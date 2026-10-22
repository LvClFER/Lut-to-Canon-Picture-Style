import ctypes
import struct
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, Mock
from camera_install.wpd_command_sender import CommandSender, DataPhaseSender, CapabilitySender, _response_parameters
from camera_install.wpd_data_phase_reference import CommandPropertyMapAdapter, COMMON, MTP


class CommandSenderTests(unittest.TestCase):
    def test_only_missing_optional_response_parameters_are_empty(self):
        for status, accepted in ((0x80070490, True), (0x80070005, False),
                                 (0x80070057, False), (0, False)):
            with self.subTest(status=hex(status)), \
                 patch('camera_install.wpd_command_sender.api._method',
                       return_value=lambda *args: status), \
                 patch('camera_install.wpd_command_sender.api._release'):
                if accepted:
                    self.assertEqual(_response_parameters(Mock(), ctypes.c_void_p(3)), ())
                    with self.assertRaises(OSError):
                        CapabilitySender(Mock(), ctypes.c_void_p(1))._decode(
                            ctypes.c_void_p(3), {}, {})
                else:
                    with self.assertRaises((OSError, RuntimeError)):
                        _response_parameters(Mock(), ctypes.c_void_p(3))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows system COM only')
    def test_real_local_com_marshalling_without_device_access(self):
        # Qt owns the main thread's COM apartment during combined UI tests.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(self._local_com_marshalling).result(timeout=10)

    def _local_com_marshalling(self):
        from camera_install.wpd_connection import _system_com
        from camera_install import windows_wpd_probe as api
        com = _system_com()
        api._check_hr(com.CoInitializeEx(None, 0), 'Initialize local COM')
        params = ctypes.c_void_p()
        try:
            params = api._new_mtp_params(com, 12, opcode=0x9114, args=(1, 0xffffffff))
            self.assertEqual(api._get_unsigned(params, api._PropertyKey.create(COMMON, 1002)), 12)
            self.assertEqual(api._get_unsigned(params, api._PropertyKey.create(MTP, 1001)), 0x9114)
            self.assertEqual(api._get_unsigned(params, api._PropertyKey.create(api._API_OPTIONS_CATEGORY, 3)), 3)
            from camera_install.wpd_command_sender import _unsigned_collection
            self.assertEqual(_unsigned_collection(com, params, 1002, 5), (1, 0xffffffff))
            self.assertEqual(_response_parameters(com, params), ())
            api._set_unsigned(params, api._PropertyKey.create(MTP, 1004), 1)
            with self.assertRaises(OSError):
                _response_parameters(com, params)
            for command, access in ((11, 1), (12, 3), (13, 1), (14, 3),
                                    (15, 1), (16, 3), (17, 1)):
                api._release(params)
                params = ctypes.c_void_p()
                params = api._new_mtp_params(com, command)
                self.assertEqual(api._get_unsigned(params,
                    api._PropertyKey.create(api._API_OPTIONS_CATEGORY, 3)), access)
        finally:
            api._release(params)
            com.CoUninitialize()

    def test_vendor_capability_query_is_distinct_from_no_data_ptp(self):
        sender = CapabilitySender(Mock(), ctypes.c_void_p(1))
        request = {(COMMON, 1001): MTP, (COMMON, 1002): 11}
        self.assertEqual(sender._validate(request), (11, None, (), None))
        with patch('camera_install.wpd_command_sender._unsigned_collection', return_value=(0x9114,)) as collection:
            result = sender._decode(ctypes.c_void_p(3), request, {(COMMON, 1003): 0})
            self.assertEqual(result[(MTP, 1005)], (0x9114,))
            self.assertEqual(collection.call_args.args[2:], (1005, 4096))
        with patch('camera_install.wpd_command_sender._unsigned_collection', return_value=(0x10000,)):
            with self.assertRaises(RuntimeError):
                sender._decode(ctypes.c_void_p(3), request, {})

    def run_fake(self, *, command_hr=0, send_hr=0, missing_hr=False, null_result=False):
        released = []
        def method(pointer, index, *types):
            if index == 4:
                def send(device, flags, params, result):
                    result._obj.value = 0 if null_result else 3
                    return send_hr
                return send
            if index == 20:
                def error(results, key, value):
                    value._obj.value = command_hr
                    return 0x80004005 if missing_hr else 0
                return error
            raise AssertionError(index)
        with patch('camera_install.wpd_command_sender.api._new_mtp_params',
                   return_value=ctypes.c_void_p(2)) as new, \
             patch('camera_install.wpd_command_sender.api._method', side_effect=method), \
             patch('camera_install.wpd_command_sender.api._release',
                   side_effect=lambda ptr: released.append(ptr.value)), \
             patch('camera_install.wpd_command_sender.api._get_unsigned', return_value=0x2001), \
             patch('camera_install.wpd_command_sender._response_parameters', return_value=(9,)):
            sender = CommandSender(Mock(), ctypes.c_void_p(1))
            adapter = CommandPropertyMapAdapter(sender)
            try:
                result = adapter.execute(0x9114, (1,))
            except Exception:
                self.assertEqual(released, [None if null_result else 3, 2])
                raise
            self.assertEqual(released, [3, 2])
            self.assertEqual(new.call_args.kwargs, {'opcode': 0x9114, 'args': (1,), 'context': None})
            return result

    def test_marshalling_links_to_adapter_without_real_com(self):
        self.assertEqual(self.run_fake().parameters, (9,))

    def test_hresult_missing_or_failed_and_null_results_close_owned_values(self):
        for kwargs in ({'missing_hr': True}, {'command_hr': 0x80070005},
                       {'send_hr': 0x80004005}, {'null_result': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises((OSError, RuntimeError)):
                self.run_fake(**kwargs)

    def test_preflight_does_not_create_com_objects(self):
        sender = CommandSender(Mock(), ctypes.c_void_p(1))
        valid = {(COMMON, 1001): MTP, (COMMON, 1002): 12,
                 (MTP, 1001): 0x9114, (MTP, 1002): (1,)}
        with patch('camera_install.wpd_command_sender.api._new_mtp_params') as new:
            for request in ({}, dict(valid, extra=0),
                            {**valid, (MTP, 1002): (True,)},
                            {**valid, (COMMON, 1002): 14}):
                with self.assertRaises(ValueError):
                    sender(request)
            sender._thread = -1
            with self.assertRaises(RuntimeError):
                sender(valid)
            new.assert_not_called()

    def test_data_phase_marshalling_uses_ui8_and_explicit_write_access(self):
        sender = DataPhaseSender(Mock(), ctypes.c_void_p(1), allow_write=True)
        request = {(COMMON, 1001): MTP, (COMMON, 1002): 14,
                   (MTP, 1001): 0x9192, (MTP, 1002): (1, 16720), (MTP, 1007): 16720}
        with patch('camera_install.wpd_command_sender.api._new_mtp_params',
                   return_value=ctypes.c_void_p(2)), \
             patch('camera_install.wpd_command_sender.api._set_unsigned_large') as ui8:
            params = sender._make_params(request, sender._validate(request))
            self.assertEqual(params.value, 2)
            self.assertEqual(ui8.call_args.args[1].pid, 1007)
            self.assertEqual(ui8.call_args.args[2], 16720)
        with self.assertRaises(ValueError):
            DataPhaseSender(Mock(), ctypes.c_void_p(1))._validate(request)

    def test_receive_decode_preserves_actual_count_and_missing_size_context(self):
        sender = DataPhaseSender(Mock(), ctypes.c_void_p(1))
        base = {(COMMON, 1001): MTP, (COMMON, 1002): 15,
                (MTP, 1006): 'ctx', (MTP, 1008): 8, (MTP, 1012): bytes(8)}
        with patch('camera_install.wpd_command_sender.api._get_buffer', return_value=b'abc'+bytes(5)), \
             patch('camera_install.wpd_command_sender.api._get_unsigned', return_value=3):
            result = sender._decode(ctypes.c_void_p(3), base, {})
            self.assertEqual(result[(MTP, 1009)], 3)
            self.assertEqual(len(result[(MTP, 1012)]), 8)
        with patch('camera_install.wpd_command_sender.api._get_string', return_value='ctx'), \
             patch('camera_install.wpd_command_sender.api._get_unsigned_large', side_effect=OSError()), \
             patch('camera_install.wpd_command_sender.api._get_unsigned', side_effect=OSError()):
            result = sender._decode(ctypes.c_void_p(3), {(COMMON, 1002): 13}, {})
            self.assertEqual(result, {(MTP, 1006): 'ctx'})

    def test_data_preflight_rejects_bad_counts_contexts_and_extra_keys(self):
        sender = DataPhaseSender(Mock(), ctypes.c_void_p(1), allow_write=True)
        request = {(COMMON, 1001): MTP, (COMMON, 1002): 16,
                   (MTP, 1006): 'ctx', (MTP, 1010): 3, (MTP, 1012): b'abc'}
        self.assertEqual(sender._validate(request), (16, None, (), 'ctx'))
        for wrong in ({**request, (MTP, 1010): 4},
                      {**request, (MTP, 1006): 'ctx\0'},
                      {**request, (MTP, 1012): bytearray(b'abc')},
                      {**request, (MTP, 1999): 0}):
            with self.assertRaises(ValueError):
                sender._validate(wrong)

    def test_response_collection_marshalling_and_cleanup(self):
        for count, vt, expected in ((2, 19, (0, 0xffffffff)),
                                    (1, 8, None), (6, 19, None)):
            ole32 = Mock()
            ole32.PropVariantClear.return_value = 0
            def method(pointer, index, *types):
                if index == 34:
                    def get(results, key, output):
                        output._obj.value = 5
                        return 0
                    return get
                if index == 3:
                    def size(collection, output):
                        output._obj.value = count
                        return 0
                    return size
                if index == 4:
                    def at(collection, i, variant):
                        struct.pack_into('<H', variant, 0, vt)
                        struct.pack_into('<I', variant, 8, 0xffffffff if i else 0)
                        return 0
                    return at
                raise AssertionError(index)
            with patch('camera_install.wpd_command_sender.api._method', side_effect=method), \
                 patch('camera_install.wpd_command_sender.api._release') as release:
                if expected is None:
                    with self.assertRaises(RuntimeError):
                        _response_parameters(ole32, ctypes.c_void_p(3))
                else:
                    self.assertEqual(_response_parameters(ole32, ctypes.c_void_p(3)), expected)
                release.assert_called_once()
                self.assertEqual(release.call_args.args[0].value, 5)
                self.assertEqual(ole32.PropVariantClear.call_count, 0 if count > 5 else count)
