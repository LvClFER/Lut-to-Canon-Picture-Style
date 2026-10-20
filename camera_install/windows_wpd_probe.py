"""Windows Portable Devices transport research for the direct-camera path.

Discovery, capability queries and event payloads are read-only. The explicit
event-session probe may toggle Canon's temporary remote/event session modes,
then always attempts to turn them off. This module never issues a registration
command and uses Windows' own WPD manager rather than Canon software.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import struct
import sys
import uuid
from ctypes import wintypes
from camera_install.canon_events import extract_property_values


_MANAGER_CLSID = "0af10cec-2ecd-4b92-9581-34f6ae0637f3"
_MANAGER_IID = "a1567595-4c2f-4574-a6fa-ecef917b9a40"
_DEVICE_CLSID = "728a21c5-3d9e-48d7-9810-864848f0f404"
_DEVICE_IID = "625e2df8-6392-4cf0-9ad1-3cfa5f17775c"
_VALUES_CLSID = "0c15d503-d017-47ce-9016-7b3f978721cc"
_VALUES_IID = "6848f6f2-3155-4f86-b6f5-263eeeab3143"
_KEYS_CLSID = "de2d022d-2480-43be-97f0-d1fa2cf98f4f"
_KEYS_IID = "dada2357-e0ad-492e-98db-dd61c53ba353"
_PROPVARIANT_COLLECTION_CLSID = "08a99e2f-6d6d-4b80-af5a-baf2bcbe4cb9"
_PROPVARIANT_COLLECTION_IID = "89b2e422-4f1b-4316-bcef-a44afea83eb3"
_CLIENT_CATEGORY = "204d9f0c-2292-4080-9f42-40664e70f859"
_COMMON_CATEGORY = "f0422a9c-5dc8-4440-b5bd-5df28835658a"
_MTP_CATEGORY = "4d545058-1a2e-4106-a357-771e0819fc56"
_MTP_DEVICE_PROPS_CATEGORY = "4d545058-8900-40b3-8f1d-dc246e1e8370"
_API_OPTIONS_CATEGORY = "10e54a3e-052d-4777-a13c-de7614be2bc4"
_CLSCTX_INPROC_SERVER = 1
_RPC_E_CHANGED_MODE = 0x80010106
_GENERIC_READ = 0x80000000
_GENERIC_READ_WRITE = 0xc0000000
_FILE_READ_ACCESS = 1
_VT_UI4 = 19
_PTP_RESPONSE_OK = 0x2001
_MAX_EVENT_BYTES = 4 * 1024 * 1024


class _Guid(ctypes.Structure):
    # Windows ABI widths also apply when inspecting these records on LP64 hosts.
    _fields_ = [
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_text(cls, value: str) -> "_Guid":
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class _PropertyKey(ctypes.Structure):
    _fields_ = [("fmtid", _Guid), ("pid", ctypes.c_uint32)]

    @classmethod
    def create(cls, category: str, pid: int) -> "_PropertyKey":
        return cls(_Guid.from_text(category), pid)


def _check_hr(value: int, action: str) -> None:
    if value & 0x80000000:
        raise OSError(f"{action} failed: HRESULT 0x{value & 0xffffffff:08X}")


def _method(pointer: ctypes.c_void_p, index: int, *argtypes):
    address = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents[index]
    return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(address)


def _release(pointer: ctypes.c_void_p) -> None:
    if pointer.value:
        _method(pointer, 2)(pointer)


def _create_instance(ole32, clsid_text: str, iid_text: str) -> ctypes.c_void_p:
    instance = ctypes.c_void_p()
    clsid, iid = _Guid.from_text(clsid_text), _Guid.from_text(iid_text)
    _check_hr(
        ole32.CoCreateInstance(
            ctypes.byref(clsid), None, _CLSCTX_INPROC_SERVER,
            ctypes.byref(iid), ctypes.byref(instance),
        ),
        f"CoCreateInstance({clsid_text})",
    )
    return instance


def _set_unsigned(values: ctypes.c_void_p, key: _PropertyKey, value: int) -> None:
    setter = _method(values, 9, ctypes.POINTER(_PropertyKey), wintypes.ULONG)
    _check_hr(setter(values, ctypes.byref(key), value), "IPortableDeviceValues.SetUnsignedIntegerValue")


def _get_unsigned(values: ctypes.c_void_p, key: _PropertyKey) -> int:
    value = wintypes.ULONG()
    getter = _method(
        values, 10, ctypes.POINTER(_PropertyKey), ctypes.POINTER(wintypes.ULONG),
    )
    _check_hr(getter(values, ctypes.byref(key), ctypes.byref(value)), "IPortableDeviceValues.GetUnsignedIntegerValue")
    return int(value.value)


def _set_unsigned_large(values: ctypes.c_void_p, key: _PropertyKey, value: int) -> None:
    setter = _method(values, 13, ctypes.POINTER(_PropertyKey), ctypes.c_ulonglong)
    _check_hr(
        setter(values, ctypes.byref(key), value),
        "IPortableDeviceValues.SetUnsignedLargeIntegerValue",
    )


def _get_unsigned_large(values: ctypes.c_void_p, key: _PropertyKey) -> int:
    value = ctypes.c_ulonglong()
    getter = _method(
        values, 14, ctypes.POINTER(_PropertyKey), ctypes.POINTER(ctypes.c_ulonglong),
    )
    _check_hr(
        getter(values, ctypes.byref(key), ctypes.byref(value)),
        "IPortableDeviceValues.GetUnsignedLargeIntegerValue",
    )
    return int(value.value)


def _set_string(values: ctypes.c_void_p, key: _PropertyKey, value: str) -> None:
    setter = _method(values, 7, ctypes.POINTER(_PropertyKey), ctypes.c_wchar_p)
    _check_hr(setter(values, ctypes.byref(key), value), "IPortableDeviceValues.SetStringValue")


def _get_string(ole32, values: ctypes.c_void_p, key: _PropertyKey) -> str:
    pointer = ctypes.c_void_p()
    getter = _method(
        values, 8, ctypes.POINTER(_PropertyKey), ctypes.POINTER(ctypes.c_void_p),
    )
    _check_hr(getter(values, ctypes.byref(key), ctypes.byref(pointer)), "IPortableDeviceValues.GetStringValue")
    if not pointer.value:
        raise RuntimeError("WPD returned an empty transfer context")
    try:
        return ctypes.wstring_at(pointer)
    finally:
        ole32.CoTaskMemFree(pointer)


def _set_buffer(values: ctypes.c_void_p, key: _PropertyKey, value: bytes) -> None:
    storage = (ctypes.c_ubyte * max(1, len(value)))()
    if value:
        ctypes.memmove(storage, value, len(value))
    setter = _method(
        values, 29, ctypes.POINTER(_PropertyKey),
        ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD,
    )
    _check_hr(
        setter(values, ctypes.byref(key), storage, len(value)),
        "IPortableDeviceValues.SetBufferValue",
    )


def _get_buffer(
    ole32, values: ctypes.c_void_p, key: _PropertyKey,
    max_bytes: int = _MAX_EVENT_BYTES,
) -> bytes:
    pointer = ctypes.c_void_p()
    length = wintypes.DWORD()
    getter = _method(
        values, 30, ctypes.POINTER(_PropertyKey),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD),
    )
    _check_hr(
        getter(values, ctypes.byref(key), ctypes.byref(pointer), ctypes.byref(length)),
        "IPortableDeviceValues.GetBufferValue",
    )
    if length.value and not pointer.value:
        raise RuntimeError("WPD returned a null transfer buffer")
    try:
        if length.value > max_bytes:
            raise RuntimeError("WPD transfer buffer exceeded the requested limit")
        return ctypes.string_at(pointer, length.value) if length.value else b""
    finally:
        if pointer.value:
            ole32.CoTaskMemFree(pointer)


def _set_propvariant_collection(
    values: ctypes.c_void_p, key: _PropertyKey, collection: ctypes.c_void_p,
) -> None:
    setter = _method(
        values, 33, ctypes.POINTER(_PropertyKey), ctypes.c_void_p,
    )
    _check_hr(
        setter(values, ctypes.byref(key), collection),
        "IPortableDeviceValues.SetIPortableDevicePropVariantCollectionValue",
    )


def _new_ui4_collection(ole32, values: tuple[int, ...]) -> ctypes.c_void_p:
    collection = _create_instance(
        ole32, _PROPVARIANT_COLLECTION_CLSID, _PROPVARIANT_COLLECTION_IID,
    )
    try:
        add = _method(collection, 5, ctypes.c_void_p)
        for value in values:
            if not 0 <= value <= 0xFFFFFFFF:
                raise ValueError("MTP command parameters must be unsigned 32-bit integers")
            variant = ctypes.create_string_buffer(32)
            struct.pack_into("<H", variant, 0, _VT_UI4)
            struct.pack_into("<I", variant, 8, value)
            _check_hr(add(collection, variant), "IPortableDevicePropVariantCollection.Add")
        return collection
    except Exception:
        _release(collection)
        raise


def _set_guid(values: ctypes.c_void_p, key: _PropertyKey, value: _Guid) -> None:
    setter = _method(values, 27, ctypes.POINTER(_PropertyKey), ctypes.POINTER(_Guid))
    _check_hr(setter(values, ctypes.byref(key), ctypes.byref(value)), "IPortableDeviceValues.SetGuidValue")


def _check_result_hresult(results: ctypes.c_void_p) -> None:
    """Raise for a WPD driver's command HRESULT when the property is present."""
    code = wintypes.LONG()
    getter = _method(
        results, 20, ctypes.POINTER(_PropertyKey), ctypes.POINTER(wintypes.LONG),
    )
    result = getter(
        results, ctypes.byref(_PropertyKey.create(_COMMON_CATEGORY, 1003)),
        ctypes.byref(code),
    )
    # Some drivers omit WPD_PROPERTY_COMMON_HRESULT on successful commands.
    if result & 0x80000000:
        return
    unsigned = code.value & 0xFFFFFFFF
    if unsigned:
        raise OSError(f"WPD MTP command failed: HRESULT 0x{unsigned:08X}")


def _new_mtp_params(
    ole32, command_id: int, opcode: int | None = None,
    args: tuple[int, ...] = (), context: str | None = None,
) -> ctypes.c_void_p:
    # Direct slot-state requests blocked the physical RP driver; acquisition is unresolved.
    if command_id == 12 and opcode == 0x9127 and args and args[0] in (0xd163, 0xd164, 0xd165):
        raise ValueError('Direct slot-state requests are disabled pending protocol attribution')
    params = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
    collection = ctypes.c_void_p()
    try:
        _set_guid(
            params, _PropertyKey.create(_COMMON_CATEGORY, 1001),
            _Guid.from_text(_MTP_CATEGORY),
        )
        _set_unsigned(params, _PropertyKey.create(_COMMON_CATEGORY, 1002), command_id)
        # MTP no-data/write commands require the read/write IOCTL, even for mode changes.
        access = 3 if command_id in (12, 14, 16) else _FILE_READ_ACCESS
        _set_unsigned(params, _PropertyKey.create(_API_OPTIONS_CATEGORY, 3), access)
        if opcode is not None:
            _set_unsigned(params, _PropertyKey.create(_MTP_CATEGORY, 1001), opcode)
            collection = _new_ui4_collection(ole32, tuple(args))
            _set_propvariant_collection(
                params, _PropertyKey.create(_MTP_CATEGORY, 1002), collection,
            )
        if context is not None:
            _set_string(params, _PropertyKey.create(_MTP_CATEGORY, 1006), context)
        return params
    except Exception:
        _release(params)
        raise
    finally:
        _release(collection)


def _send_wpd(device: ctypes.c_void_p, params: ctypes.c_void_p) -> ctypes.c_void_p:
    results = ctypes.c_void_p()
    send = _method(
        device, 4, wintypes.DWORD, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    _check_hr(send(device, 0, params, ctypes.byref(results)), "IPortableDevice.SendCommand")
    if not results.value:
        raise RuntimeError("WPD SendCommand returned no result values")
    try:
        _check_result_hresult(results)
        return results
    except Exception:
        _release(results)
        raise


def _mtp_read(
    ole32, device: ctypes.c_void_p, opcode: int,
    args: tuple[int, ...] = (), max_bytes: int = _MAX_EVENT_BYTES,
) -> tuple[int, bytes]:
    """Run one device-to-host MTP data phase, bounded and fail-closed."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    params = ctypes.c_void_p()
    results = ctypes.c_void_p()
    context = None
    transfer_started = False
    payload = bytearray()
    response_code = None
    try:
        params = _new_mtp_params(ole32, 13, opcode=opcode, args=tuple(args))
        results = _send_wpd(device, params)
        context = _get_string(
            ole32, results, _PropertyKey.create(_MTP_CATEGORY, 1006),
        )
        transfer_started = True
        try:
            total_size = _get_unsigned_large(
                results, _PropertyKey.create(_MTP_CATEGORY, 1007),
            )
        except OSError:
            # The Windows MTP driver has historically returned this UI8 field
            # through the UI4 accessor on some versions.
            total_size = _get_unsigned(
                results, _PropertyKey.create(_MTP_CATEGORY, 1007),
            )
        try:
            optimal = _get_unsigned(
                results, _PropertyKey.create(_MTP_CATEGORY, 1013),
            )
        except OSError:
            optimal = 0
        _release(results)
        results = ctypes.c_void_p()
        _release(params)
        params = ctypes.c_void_p()

        unknown_size = total_size in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
        if not unknown_size and total_size > max_bytes:
            raise RuntimeError(
                f"MTP data phase is larger than the safety limit ({total_size} > {max_bytes})"
            )
        chunk_size = max(1, min(optimal or 1024 * 1024, 1024 * 1024, max_bytes))
        while unknown_size or len(payload) < total_size:
            remaining = max_bytes - len(payload)
            if remaining <= 0:
                raise RuntimeError("MTP data phase exceeded the safety limit")
            requested = min(chunk_size, remaining)
            if not unknown_size:
                requested = min(requested, total_size - len(payload))
            params = _new_mtp_params(ole32, 15, context=context)
            _set_unsigned(
                params, _PropertyKey.create(_MTP_CATEGORY, 1008), requested,
            )
            _set_buffer(
                params, _PropertyKey.create(_MTP_CATEGORY, 1012), bytes(requested),
            )
            results = _send_wpd(device, params)
            chunk = _get_buffer(
                ole32, results, _PropertyKey.create(_MTP_CATEGORY, 1012),
                max_bytes=requested,
            )
            try:
                actual = _get_unsigned(
                    results, _PropertyKey.create(_MTP_CATEGORY, 1009),
                )
                if actual > len(chunk):
                    raise RuntimeError("WPD reported more bytes read than it returned")
                chunk = chunk[:actual]
            except OSError:
                pass
            payload.extend(chunk)
            _release(results)
            results = ctypes.c_void_p()
            _release(params)
            params = ctypes.c_void_p()
            if len(chunk) < requested:
                if not unknown_size and len(payload) != total_size:
                    raise RuntimeError("WPD returned a short MTP data phase")
                break
            if not unknown_size and len(payload) == total_size:
                break

        params = _new_mtp_params(ole32, 17, context=context)
        results = _send_wpd(device, params)
        response_code = _get_unsigned(
            results, _PropertyKey.create(_MTP_CATEGORY, 1003),
        )
        transfer_started = False
        if response_code != _PTP_RESPONSE_OK:
            raise RuntimeError(f"Canon PTP command returned 0x{response_code:04X}")
        return response_code, bytes(payload)
    finally:
        _release(results)
        _release(params)
        if transfer_started and context:
            cleanup_params = ctypes.c_void_p()
            cleanup_results = ctypes.c_void_p()
            try:
                cleanup_params = _new_mtp_params(ole32, 17, context=context)
                cleanup_results = _send_wpd(device, cleanup_params)
            except Exception:
                pass
            finally:
                _release(cleanup_results)
                _release(cleanup_params)


def _mtp_no_data(
    ole32, device: ctypes.c_void_p, opcode: int, args: tuple[int, ...] = (),
) -> int:
    """Run one MTP operation without a data phase and require PTP success."""
    params = ctypes.c_void_p()
    results = ctypes.c_void_p()
    try:
        params = _new_mtp_params(ole32, 12, opcode=opcode, args=tuple(args))
        results = _send_wpd(device, params)
        response_code = _get_unsigned(
            results, _PropertyKey.create(_MTP_CATEGORY, 1003),
        )
        if response_code != _PTP_RESPONSE_OK:
            raise RuntimeError(f"Canon PTP command returned 0x{response_code:04X}")
        return response_code
    finally:
        _release(results)
        _release(params)


def _summarize_event_data(data: bytes) -> dict:
    """Summarize Canon event records without exposing property payloads."""
    event_codes: list[str] = []
    property_codes: list[str] = []
    offset = 0
    structurally_valid = True
    blocks = 0
    while offset < len(data):
        if len(data) - offset < 4:
            structurally_valid = False
            break
        length = struct.unpack_from("<I", data, offset)[0]
        if length == 0:
            offset += 4
            if any(data[offset:]):
                structurally_valid = False
            else:
                offset = len(data)
            break
        if length < 8 or length > len(data) - offset:
            structurally_valid = False
            break
        event_code = struct.unpack_from("<I", data, offset + 4)[0]
        if length == 8 and event_code == 0:
            offset += 8
            if any(data[offset:]):
                structurally_valid = False
            else:
                offset = len(data)
            break
        blocks += 1
        if blocks > 4096:
            structurally_valid = False
            break
        event_codes.append(f"0x{event_code:08X}")
        if event_code in (0xC189, 0xC18A) and length >= 12:
            property_code = struct.unpack_from("<I", data, offset + 8)[0]
            property_codes.append(f"0x{property_code:08X}")
        offset += length
    if offset != len(data):
        structurally_valid = False
    return {
        "byteLength": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "recordCount": blocks,
        "eventCodes": event_codes,
        "propertyCodes": property_codes,
        "structurallyValid": structurally_valid,
    }


def _extract_property_event_values(
    data: bytes, property_code: int, max_value_bytes: int = 1024 * 1024,
) -> list[bytes]:
    """Extract one requested C189 value internally; callers must not log it."""
    return extract_property_values(data, property_code, max_value_bytes)


def _supported_vendor_operations(ole32, device_id: str) -> list[str]:
    """Query the WPD driver; never send a Canon command or open for writing."""
    device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
    client = ctypes.c_void_p()
    params = ctypes.c_void_p()
    results = ctypes.c_void_p()
    collection = ctypes.c_void_p()
    opened = False
    try:
        client = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        _set_unsigned(client, _PropertyKey.create(_CLIENT_CATEGORY, 9), _GENERIC_READ)
        open_device = _method(device, 3, ctypes.c_wchar_p, ctypes.c_void_p)
        _check_hr(open_device(device, device_id, client), "IPortableDevice.Open(GENERIC_READ)")
        opened = True

        params = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        _set_guid(params, _PropertyKey.create(_COMMON_CATEGORY, 1001), _Guid.from_text(_MTP_CATEGORY))
        # WPD_COMMAND_MTP_EXT_GET_SUPPORTED_VENDOR_OPCODES: a read-only WPD
        # driver query, not a Canon PTP write or a registration transaction.
        _set_unsigned(params, _PropertyKey.create(_COMMON_CATEGORY, 1002), 11)
        _set_unsigned(params, _PropertyKey.create(_API_OPTIONS_CATEGORY, 3), _FILE_READ_ACCESS)
        send = _method(device, 4, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
        _check_hr(send(device, 0, params, ctypes.byref(results)), "WPD GetSupportedVendorOpcodes")

        get_collection = _method(
            results, 34, ctypes.POINTER(_PropertyKey), ctypes.POINTER(ctypes.c_void_p),
        )
        key = _PropertyKey.create(_MTP_CATEGORY, 1005)
        _check_hr(get_collection(results, ctypes.byref(key), ctypes.byref(collection)), "WPD vendor opcode collection")
        count = wintypes.DWORD()
        _check_hr(
            _method(collection, 3, ctypes.POINTER(wintypes.DWORD))(collection, ctypes.byref(count)),
            "WPD vendor opcode count",
        )
        if count.value > 4096:
            raise RuntimeError("WPD returned an implausible vendor opcode count")
        get_at = _method(collection, 4, wintypes.DWORD, ctypes.c_void_p)
        codes = []
        for index in range(count.value):
            # A PROPVARIANT with VT_UI4 has its value at byte 8. A 32-byte
            # buffer safely covers the native PROPVARIANT size on x86/x64.
            item = ctypes.create_string_buffer(32)
            _check_hr(get_at(collection, index, item), "WPD vendor opcode")
            if int.from_bytes(item.raw[:2], "little") != 19:  # VT_UI4
                raise RuntimeError("Unexpected WPD vendor opcode VARTYPE")
            codes.append(f"0x{int.from_bytes(item.raw[8:12], 'little'):04X}")
        return codes
    finally:
        _release(collection)
        _release(results)
        _release(params)
        _release(client)
        if opened:
            _method(device, 8)(device)  # IPortableDevice.Close
        _release(device)


def _supported_vendor_device_properties(ole32, device_id: str) -> list[str]:
    """List Canon/MTP device-property keys, without requesting any values."""
    device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
    client = ctypes.c_void_p()
    content = ctypes.c_void_p()
    properties = ctypes.c_void_p()
    keys = ctypes.c_void_p()
    opened = False
    try:
        client = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        _set_unsigned(client, _PropertyKey.create(_CLIENT_CATEGORY, 9), _GENERIC_READ)
        _check_hr(
            _method(device, 3, ctypes.c_wchar_p, ctypes.c_void_p)(device, device_id, client),
            "IPortableDevice.Open(GENERIC_READ)",
        )
        opened = True
        _check_hr(_method(device, 5, ctypes.POINTER(ctypes.c_void_p))(device, ctypes.byref(content)), "IPortableDevice.Content")
        _check_hr(_method(content, 4, ctypes.POINTER(ctypes.c_void_p))(content, ctypes.byref(properties)), "IPortableDeviceContent.Properties")
        _check_hr(
            _method(properties, 3, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p))(
                properties, "DEVICE", ctypes.byref(keys),
            ),
            "IPortableDeviceProperties.GetSupportedProperties",
        )
        count = wintypes.DWORD()
        _check_hr(
            _method(keys, 3, ctypes.POINTER(wintypes.DWORD))(keys, ctypes.byref(count)),
            "WPD device property count",
        )
        if count.value > 4096:
            raise RuntimeError("WPD returned an implausible device property count")
        vendor_category = _Guid.from_text(_MTP_DEVICE_PROPS_CATEGORY)
        get_at = _method(keys, 4, wintypes.DWORD, ctypes.POINTER(_PropertyKey))
        codes = []
        for index in range(count.value):
            key = _PropertyKey()
            _check_hr(get_at(keys, index, ctypes.byref(key)), "WPD device property key")
            if bytes(key.fmtid) == bytes(vendor_category):
                codes.append(f"0x{key.pid:04X}")
        return codes
    finally:
        _release(keys)
        _release(properties)
        _release(content)
        _release(client)
        if opened:
            _method(device, 8)(device)
        _release(device)


def _vendor_property_readability(ole32, device_id: str) -> dict[str, str]:
    """Try targeted WPD GetValues; never return a property's actual value."""
    device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
    client = ctypes.c_void_p()
    content = ctypes.c_void_p()
    properties = ctypes.c_void_p()
    keys = ctypes.c_void_p()
    opened = False
    try:
        client = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        keys = _create_instance(ole32, _KEYS_CLSID, _KEYS_IID)
        _set_unsigned(client, _PropertyKey.create(_CLIENT_CATEGORY, 9), _GENERIC_READ)
        _check_hr(
            _method(device, 3, ctypes.c_wchar_p, ctypes.c_void_p)(device, device_id, client),
            "IPortableDevice.Open(GENERIC_READ)",
        )
        opened = True
        _check_hr(_method(device, 5, ctypes.POINTER(ctypes.c_void_p))(device, ctypes.byref(content)), "IPortableDevice.Content")
        _check_hr(_method(content, 4, ctypes.POINTER(ctypes.c_void_p))(content, ctypes.byref(properties)), "IPortableDeviceContent.Properties")
        add_key = _method(keys, 5, ctypes.POINTER(_PropertyKey))
        output = {}
        for code in (0xD163, 0xD170):
            key = _PropertyKey.create(_MTP_DEVICE_PROPS_CATEGORY, code)
            _check_hr(add_key(keys, ctypes.byref(key)), "WPD property key collection Add")
            values = ctypes.c_void_p()
            variant = ctypes.create_string_buffer(32)
            try:
                result = _method(
                    properties, 5, ctypes.c_wchar_p, ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_void_p),
                )(properties, "DEVICE", keys, ctypes.byref(values))
                _check_hr(result, f"WPD GetValues(0x{code:04X})")
                if not values.value:
                    raise RuntimeError("WPD GetValues returned no results")
                get_value = _method(values, 6, ctypes.POINTER(_PropertyKey), ctypes.c_void_p)
                _check_hr(get_value(values, ctypes.byref(key), variant), "WPD GetValue")
                variant_type = int.from_bytes(variant.raw[:2], "little")
                if variant_type == 10:  # VT_ERROR
                    error = int.from_bytes(variant.raw[8:12], "little")
                    output[f"0x{code:04X}"] = f"unavailable: HRESULT 0x{error:08X}"
                else:
                    output[f"0x{code:04X}"] = f"value returned (VARTYPE {variant_type}); content suppressed"
            except Exception as exc:
                output[f"0x{code:04X}"] = str(exc)
            finally:
                if values.value:
                    ole32.PropVariantClear(variant)
                _release(values)
                _check_hr(_method(keys, 6)(keys), "WPD property key collection Clear")
        return output
    finally:
        _release(keys)
        _release(properties)
        _release(content)
        _release(client)
        if opened:
            _method(device, 8)(device)
        _release(device)


def _canon_event_summary(ole32, device_id: str) -> dict:
    """Poll Canon GetEvent once through WPD; this is a device-to-host read."""
    device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
    client = ctypes.c_void_p()
    opened = False
    try:
        client = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        _set_unsigned(client, _PropertyKey.create(_CLIENT_CATEGORY, 9), _GENERIC_READ)
        _check_hr(
            _method(device, 3, ctypes.c_wchar_p, ctypes.c_void_p)(
                device, device_id, client,
            ),
            "IPortableDevice.Open(GENERIC_READ)",
        )
        opened = True
        response_code, data = _mtp_read(ole32, device, 0x9116)
        summary = _summarize_event_data(data)
        summary["responseCode"] = f"0x{response_code:04X}"
        return summary
    finally:
        _release(client)
        if opened:
            _method(device, 8)(device)
        _release(device)


def _canon_event_session_summary(ole32, device_id: str) -> dict:
    """Temporarily enable Canon event mode, poll once, then disable it."""
    device = _create_instance(ole32, _DEVICE_CLSID, _DEVICE_IID)
    client = ctypes.c_void_p()
    opened = False
    remote_enabled = False
    events_enabled = False
    cleanup: dict[str, str] = {}
    try:
        client = _create_instance(ole32, _VALUES_CLSID, _VALUES_IID)
        _set_unsigned(client, _PropertyKey.create(_CLIENT_CATEGORY, 9), _GENERIC_READ_WRITE)
        _check_hr(
            _method(device, 3, ctypes.c_wchar_p, ctypes.c_void_p)(
                device, device_id, client,
            ),
            "IPortableDevice.Open(GENERIC_READ | GENERIC_WRITE)",
        )
        opened = True
        _mtp_no_data(ole32, device, 0x9114, (1,))
        remote_enabled = True
        _mtp_no_data(ole32, device, 0x9115, (1,))
        events_enabled = True
        response_code, data = _mtp_read(ole32, device, 0x9116)
        summary = _summarize_event_data(data)
        summary["responseCode"] = f"0x{response_code:04X}"
        summary["temporarySessionCommands"] = ["0x9114", "0x9115", "0x9116"]
        summary["cleanup"] = cleanup
        return summary
    finally:
        if events_enabled:
            try:
                cleanup["eventMode"] = f"0x{_mtp_no_data(ole32, device, 0x9115, (0,)):04X}"
            except Exception as exc:
                cleanup["eventModeError"] = str(exc)
        if remote_enabled:
            try:
                cleanup["remoteMode"] = f"0x{_mtp_no_data(ole32, device, 0x9114, (0,)):04X}"
            except Exception as exc:
                cleanup["remoteModeError"] = str(exc)
        _release(client)
        if opened:
            _method(device, 8)(device)
        _release(device)


def _canon_registration_state_summary(ole32, device_id: str) -> dict:
    """Disabled: direct9127(D163) blocked the physical RP driver on2026-10-16."""
    raise RuntimeError('Direct registration-state requests are disabled; use the startup event diagnostic')


def _device_text(manager: ctypes.c_void_p, method_index: int, device_id: str) -> str:
    getter = _method(
        manager, method_index, ctypes.c_wchar_p, ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
    )
    needed = wintypes.DWORD(0)
    getter(manager, device_id, None, ctypes.byref(needed))
    if not needed.value or needed.value > 32768:
        return ""
    output = ctypes.create_unicode_buffer(needed.value)
    result = getter(manager, device_id, ctypes.cast(output, ctypes.c_void_p), ctypes.byref(needed))
    return output.value if not (result & 0x80000000) else ""


def _summarize_device(device_id: str, friendly_name: str, description: str, manufacturer: str) -> dict:
    fingerprint = hashlib.sha256(device_id.encode("utf-16-le")).hexdigest()[:16]
    is_canon = "canon" in " ".join((device_id, friendly_name, description, manufacturer)).lower()
    return {
        "idFingerprint": fingerprint,
        "friendlyName": friendly_name,
        "description": description,
        "manufacturer": manufacturer,
        "canonCandidate": is_canon,
    }


def enumerate_portable_devices(
    inspect_operations: bool = False,
    inspect_readability: bool = False,
    inspect_events: bool = False,
    inspect_event_session: bool = False,
    inspect_registration_state: bool = False,
    _on_device=None,
) -> list[dict]:
    """List WPD devices; do not expose serial-bearing PnP identifiers."""
    if _on_device is not None and not callable(_on_device):
        raise TypeError('Internal device callback must be callable')
    if sys.platform != "win32":
        raise RuntimeError("Windows Portable Devices is available only on Windows")
    ole32 = ctypes.WinDLL("ole32")
    ole32.CoInitializeEx.argtypes = (ctypes.c_void_p, wintypes.DWORD)
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = (
        ctypes.POINTER(_Guid), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p),
    )
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    ole32.PropVariantClear.argtypes = (ctypes.c_void_p,)
    ole32.PropVariantClear.restype = ctypes.c_long
    initialized = ole32.CoInitializeEx(None, 0)
    if initialized != 0 and (initialized & 0xffffffff) != _RPC_E_CHANGED_MODE:
        _check_hr(initialized, "CoInitializeEx")
    must_uninitialize = initialized in (0, 1)
    manager = ctypes.c_void_p()
    try:
        manager = _create_instance(ole32, _MANAGER_CLSID, _MANAGER_IID)
        get_devices = _method(manager, 3, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD))
        count = wintypes.DWORD(0)
        _check_hr(get_devices(manager, None, ctypes.byref(count)), "GetDevices(count)")
        if not count.value:
            return []
        if count.value > 1024:
            raise RuntimeError("WPD returned an implausible device count")
        pointers = (ctypes.c_void_p * count.value)()
        devices = []
        try:
            _check_hr(get_devices(manager, ctypes.cast(pointers, ctypes.c_void_p), ctypes.byref(count)), "GetDevices(list)")
            for raw_pointer in pointers[:count.value]:
                if not raw_pointer:
                    continue
                device_id = ctypes.wstring_at(raw_pointer)
                device = _summarize_device(
                    device_id,
                    _device_text(manager, 5, device_id),
                    _device_text(manager, 6, device_id),
                    _device_text(manager, 7, device_id),
                )
                # Internal selection only; raw IDs never enter discovery reports.
                if _on_device is not None:
                    _on_device(device_id, dict(device))
                if (
                    inspect_operations or inspect_readability or inspect_events
                    or inspect_event_session or inspect_registration_state
                ) and device["canonCandidate"]:
                    if inspect_operations:
                        try:
                            device["supportedVendorOperations"] = _supported_vendor_operations(ole32, device_id)
                        except Exception as exc:
                            device["inspectionError"] = str(exc)
                        try:
                            device["vendorDevicePropertyCodes"] = _supported_vendor_device_properties(ole32, device_id)
                        except Exception as exc:
                            device["propertyInspectionError"] = str(exc)
                    if inspect_readability:
                        try:
                            device["vendorPropertyReadability"] = _vendor_property_readability(ole32, device_id)
                        except Exception as exc:
                            device["readabilityInspectionError"] = str(exc)
                    if inspect_events:
                        try:
                            device["canonEventPoll"] = _canon_event_summary(ole32, device_id)
                        except Exception as exc:
                            device["eventInspectionError"] = str(exc)
                    if inspect_event_session:
                        try:
                            device["canonEventSessionPoll"] = _canon_event_session_summary(
                                ole32, device_id,
                            )
                        except Exception as exc:
                            device["eventSessionInspectionError"] = str(exc)
                    if inspect_registration_state:
                        try:
                            device["canonRegistrationState"] = _canon_registration_state_summary(
                                ole32, device_id,
                            )
                        except Exception as exc:
                            device["registrationStateInspectionError"] = str(exc)
                devices.append(device)
        finally:
            for raw_pointer in pointers:
                if raw_pointer:
                    ole32.CoTaskMemFree(raw_pointer)
        return devices
    finally:
        _release(manager)
        if must_uninitialize:
            ole32.CoUninitialize()


def probe(
    include_all: bool = False,
    inspect_operations: bool = False,
    inspect_readability: bool = False,
    inspect_events: bool = False,
    inspect_event_session: bool = False,
    inspect_registration_state: bool = False,
) -> dict:
    devices = enumerate_portable_devices(
        inspect_operations=inspect_operations,
        inspect_readability=inspect_readability,
        inspect_events=inspect_events,
        inspect_event_session=inspect_event_session,
        inspect_registration_state=inspect_registration_state,
    )
    candidates = devices if include_all else [item for item in devices if item["canonCandidate"]]
    if inspect_registration_state:
        mode = "canon-registration-state-read"
    elif inspect_event_session:
        mode = "canon-temporary-event-session"
    elif inspect_events:
        mode = "canon-event-read"
    elif inspect_readability:
        mode = "targeted-property-read"
    elif inspect_operations:
        mode = "vendor-opcode-query"
    else:
        mode = "discovery"
    return {
        "format": "CanonStyleStudio.WindowsWpdDiscovery",
        "readOnly": not (inspect_event_session or inspect_registration_state),
        "canonSoftwareRequired": False,
        "cameraSessionAttempted": (
            inspect_operations or inspect_readability or inspect_events
            or inspect_event_session or inspect_registration_state
        ) and bool(candidates),
        "registrationCommandsSent": False,
        "persistentCameraSettingsWritten": False,
        "temporarySessionModeCommandsSent": (
            inspect_event_session or inspect_registration_state
        ) and bool(candidates),
        "mode": mode,
        "devices": candidates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Research Canon WPD transport without Canon software or registration writes"
    )
    parser.add_argument("--all", action="store_true", help="include non-Canon portable devices")
    parser.add_argument("--inspect", action="store_true", help="open a read-only WPD session and query supported vendor opcodes")
    parser.add_argument("--readability", action="store_true", help="try targeted read-only queries for Canon property codes without showing their values")
    parser.add_argument("--events", action="store_true", help="poll Canon GetEvent once and report only structural metadata")
    parser.add_argument(
        "--event-session", action="store_true",
        help="temporarily enable Canon remote/event mode, poll once, and disable it again",
    )
    parser.add_argument(
        "--registration-state", action="store_true",
        help="request D163/D170 live values but report only sizes and hashes; never write them",
    )
    args = parser.parse_args(argv)
    try:
        result = probe(
            include_all=args.all,
            inspect_operations=args.inspect,
            inspect_readability=args.readability,
            inspect_events=args.events,
            inspect_event_session=args.event_session,
            inspect_registration_state=args.registration_state,
        )
    except Exception as exc:
        result = {
            "format": "CanonStyleStudio.WindowsWpdDiscovery",
            "readOnly": not (args.event_session or args.registration_state),
            "registrationCommandsSent": False,
            "error": str(exc),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
