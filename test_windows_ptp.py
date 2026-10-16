from __future__ import annotations

import struct
import sys
import ctypes
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from camera_install import windows_wpd_probe as wpd

from camera_install.ptp_capture import (
    build_canon_property_packet, build_rp_d163_packet,
    build_rp_d170_packet, validate_rp_slot1_capture,
)
from camera_install.windows_wpd_probe import (
    _Guid, _PropertyKey, _check_hr, _create_instance, _method, _release,
    _get_buffer, _get_string, _get_unsigned_large, _new_ui4_collection,
    _extract_property_event_values,
    _set_buffer, _set_guid, _set_string, _set_unsigned, _set_unsigned_large,
    _summarize_device, _summarize_event_data, _VALUES_CLSID, _VALUES_IID,
    _DEVICE_CLSID, _DEVICE_IID, _KEYS_CLSID, _KEYS_IID,
    _API_OPTIONS_CATEGORY, _FILE_READ_ACCESS,
)


class WindowsPtpResearchTests(unittest.TestCase):
    def mock_session(self):
        stack = self.enterContext(ExitStack())
        stack.enter_context(patch.object(wpd, "_create_instance", return_value=ctypes.c_void_p(1)))
        stack.enter_context(patch.object(wpd, "_set_unsigned"))
        stack.enter_context(patch.object(wpd, "_release"))
        method = stack.enter_context(patch.object(wpd, "_method"))
        method.return_value.return_value = 0
        read = stack.enter_context(patch.object(wpd, "_mtp_read", return_value=(0x2001, struct.pack("<II", 8, 0))))
        commands = stack.enter_context(patch.object(wpd, "_mtp_no_data", return_value=0x2001))
        return read, commands

    def test_plain_event_poll_does_not_toggle_session(self):
        read, commands = self.mock_session()
        result = wpd._canon_event_summary(None, "mock-device")
        self.assertTrue(result["structurallyValid"])
        self.assertEqual(result["responseCode"], "0x2001")
        self.assertNotIn("cleanup", result)
        commands.assert_not_called()
        self.assertEqual(read.call_args.args[2], 0x9116)

    def test_event_session_reports_cleanup_failure(self):
        _read, commands = self.mock_session()
        commands.side_effect = [0x2001, 0x2001, OSError("event disable failed"), 0x2001]
        result = wpd._canon_event_session_summary(None, "mock-device")
        self.assertEqual(result["cleanup"]["eventModeError"], "event disable failed")
        self.assertEqual(result["cleanup"]["remoteMode"], "0x2001")
        self.assertEqual(
            [(call.args[2], call.args[3]) for call in commands.call_args_list],
            [(0x9114, (1,)), (0x9115, (1,)), (0x9115, (0,)), (0x9114, (0,))],
        )

    def test_failed_event_read_still_disables_both_modes(self):
        read, commands = self.mock_session()
        read.side_effect = OSError("camera disconnected")
        with self.assertRaisesRegex(OSError, "camera disconnected"):
            wpd._canon_event_session_summary(None, "mock-device")
        self.assertEqual(
            [(call.args[2], call.args[3]) for call in commands.call_args_list][-2:],
            [(0x9115, (0,)), (0x9114, (0,))],
        )

    def test_oversized_transfer_buffer_rejected_before_copy(self):
        ole32 = Mock()
        def getter(_values, _key, pointer, length):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = 123
            ctypes.cast(length, ctypes.POINTER(ctypes.c_ulong))[0] = 9
            return 0
        with patch.object(wpd, "_method", return_value=getter), patch.object(ctypes, "string_at") as copy:
            with self.assertRaisesRegex(RuntimeError, "exceeded"):
                wpd._get_buffer(ole32, ctypes.c_void_p(1), _PropertyKey.create(wpd._MTP_CATEGORY, 1012), max_bytes=8)
            copy.assert_not_called()
        ole32.CoTaskMemFree.assert_called_once()

    @staticmethod
    def fixture():
        carrier = bytes((n * 7) & 255 for n in range(16752))
        selector = b"\x41\x00\x00\x00"
        control = bytes((n * 3) & 255 for n in range(32))
        style = bytearray(17126)
        state = bytearray(450)
        struct.pack_into("<4I", style, 288, 16728, 16728, 0xD170, 16720)
        style[304:17020] = carrier[:4] + carrier[40:]
        struct.pack_into("<5I", state, 288, 52, 52, 0xD163, 44, 1)
        state[308:312] = selector
        state[312:344] = control
        return carrier, selector, control, bytes(style), bytes(state)

    def test_exact_rp_mapping(self):
        result = validate_rp_slot1_capture(*self.fixture())
        self.assertTrue(result["exactMatch"])
        self.assertEqual(result["styleProperty"], "0xD170")
        self.assertNotIn("control115", result)  # No captured state bytes in reports.

    def test_exact_rp_inner_ptp_packets(self):
        carrier, selector, control, style, state = self.fixture()
        self.assertEqual(build_rp_d170_packet(carrier), style[292:17020])
        self.assertEqual(build_rp_d163_packet(selector, control), state[292:344])
        packet = build_canon_property_packet(0xD170, b"abc")
        self.assertEqual(struct.unpack_from("<III", packet), (15, 0xD170, 7))
        self.assertEqual(packet[12:], b"abc")

    def test_style_mutation_fails_closed(self):
        parts = list(self.fixture())
        altered = bytearray(parts[3])
        altered[17000] ^= 1
        parts[3] = bytes(altered)
        with self.assertRaisesRegex(ValueError, "D170"):
            validate_rp_slot1_capture(*parts)

    def test_state_mutation_fails_closed(self):
        parts = list(self.fixture())
        altered = bytearray(parts[4])
        altered[330] ^= 1
        parts[4] = bytes(altered)
        with self.assertRaisesRegex(ValueError, "D163"):
            validate_rp_slot1_capture(*parts)

    def test_r8_size_is_not_assumed_rp(self):
        parts = list(self.fixture())
        parts[0] = bytes(83076)
        with self.assertRaisesRegex(ValueError, "Unsupported capture sizes"):
            validate_rp_slot1_capture(*parts)

    def test_device_id_is_not_reported(self):
        item = _summarize_device("USB\\VID_04A9\\private-serial", "EOS RP", "camera", "Canon")
        self.assertTrue(item["canonCandidate"])
        self.assertNotIn("private-serial", repr(item))

    def test_vendor_opcode_query_requests_read_only_ioctl(self):
        key = _PropertyKey.create(_API_OPTIONS_CATEGORY, 3)
        self.assertEqual(key.pid, 3)
        self.assertEqual(_FILE_READ_ACCESS, 1)
        self.assertEqual(bytes(key.fmtid), bytes(_Guid.from_text("10e54a3e-052d-4777-a13c-de7614be2bc4")))

    def test_canon_event_summary_parses_records_without_payloads(self):
        data = (
            struct.pack("<III", 12, 0xC189, 0xD170)
            + struct.pack("<II", 8, 0xC181)
        )
        result = _summarize_event_data(data)
        self.assertTrue(result["structurallyValid"])
        self.assertEqual(result["recordCount"], 2)
        self.assertEqual(result["eventCodes"], ["0x0000C189", "0x0000C181"])
        self.assertEqual(result["propertyCodes"], ["0x0000D170"])
        self.assertNotIn(data.hex(), repr(result))

    def test_canon_event_summary_rejects_truncated_record(self):
        result = _summarize_event_data(struct.pack("<II", 12, 0xC189))
        self.assertFalse(result["structurallyValid"])
        self.assertEqual(result["recordCount"], 0)

    def test_canon_event_property_extraction_and_terminator(self):
        private_value = b"private-live-state"
        data = (
            struct.pack("<III", 12 + len(private_value), 0xC189, 0xD163)
            + private_value
            + struct.pack("<II", 8, 0)
        )
        summary = _summarize_event_data(data)
        self.assertTrue(summary["structurallyValid"])
        self.assertEqual(summary["recordCount"], 1)
        self.assertNotIn(private_value.hex(), repr(summary))
        self.assertEqual(
            _extract_property_event_values(data, 0xD163), [private_value],
        )
        self.assertEqual(_extract_property_event_values(data, 0xD170), [])

    @unittest.skipUnless(sys.platform == "win32", "Windows COM only")
    def test_wpd_values_com_roundtrip_without_camera(self):
        ole32 = ctypes.WinDLL("ole32")
        ole32.CoInitializeEx.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
        ole32.CoInitializeEx.restype = ctypes.c_long
        ole32.CoCreateInstance.argtypes = (
            ctypes.POINTER(_Guid), ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p),
        )
        ole32.CoCreateInstance.restype = ctypes.c_long
        ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
        _check_hr(ole32.CoInitializeEx(None, 0), "CoInitializeEx")
        values = ctypes.c_void_p()
        device = ctypes.c_void_p()
        keys = ctypes.c_void_p()
        collection = ctypes.c_void_p()
        try:
            device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
            values = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
            keys = _create_instance(ole32, _KEYS_CLSID, _KEYS_IID)
            key_int = _PropertyKey.create("f0422a9c-5dc8-4440-b5bd-5df28835658a", 1002)
            _set_unsigned(values, key_int, 11)
            read_int = ctypes.c_ulong()
            _check_hr(
                _method(values, 10, ctypes.POINTER(_PropertyKey), ctypes.POINTER(ctypes.c_ulong))(
                    values, ctypes.byref(key_int), ctypes.byref(read_int),
                ),
                "GetUnsignedIntegerValue",
            )
            self.assertEqual(read_int.value, 11)
            key_guid = _PropertyKey.create("f0422a9c-5dc8-4440-b5bd-5df28835658a", 1001)
            original = _Guid.from_text("4d545058-1a2e-4106-a357-771e0819fc56")
            _set_guid(values, key_guid, original)
            read_guid = _Guid()
            _check_hr(
                _method(values, 28, ctypes.POINTER(_PropertyKey), ctypes.POINTER(_Guid))(
                    values, ctypes.byref(key_guid), ctypes.byref(read_guid),
                ),
                "GetGuidValue",
            )
            self.assertEqual(bytes(read_guid), bytes(original))
            key_large = _PropertyKey.create("f0422a9c-5dc8-4440-b5bd-5df28835658a", 1010)
            _set_unsigned_large(values, key_large, 0x100000002)
            self.assertEqual(_get_unsigned_large(values, key_large), 0x100000002)
            key_string = _PropertyKey.create("f0422a9c-5dc8-4440-b5bd-5df28835658a", 1011)
            _set_string(values, key_string, "safe-context")
            self.assertEqual(_get_string(ole32, values, key_string), "safe-context")
            key_buffer = _PropertyKey.create("f0422a9c-5dc8-4440-b5bd-5df28835658a", 1012)
            _set_buffer(values, key_buffer, b"\x00\x01\x02\xff")
            self.assertEqual(_get_buffer(ole32, values, key_buffer), b"\x00\x01\x02\xff")
            collection = _new_ui4_collection(ole32, (0x9116, 0xD170))
            collection_count = ctypes.c_ulong()
            _check_hr(
                _method(collection, 3, ctypes.POINTER(ctypes.c_ulong))(
                    collection, ctypes.byref(collection_count),
                ),
                "IPortableDevicePropVariantCollection.GetCount",
            )
            self.assertEqual(collection_count.value, 2)
            _check_hr(
                _method(keys, 5, ctypes.POINTER(_PropertyKey))(keys, ctypes.byref(key_int)),
                "IPortableDeviceKeyCollection.Add",
            )
            key_count = ctypes.c_ulong()
            _check_hr(
                _method(keys, 3, ctypes.POINTER(ctypes.c_ulong))(keys, ctypes.byref(key_count)),
                "IPortableDeviceKeyCollection.GetCount",
            )
            self.assertEqual(key_count.value, 1)
            _check_hr(_method(keys, 6)(keys), "IPortableDeviceKeyCollection.Clear")
        finally:
            _release(collection)
            _release(keys)
            _release(values)
            _release(device)
            ole32.CoUninitialize()


if __name__ == "__main__":
    unittest.main()
