"""Windows WPD command12 sender for an explicitly supplied open COM device.

Construction does not initialize COM, enumerate or open any device. Caller
owns COM apartment and device lifetime/permissions. No Canon DLL dependency.
This experimental sender is not enabled in the editor's registration path.
"""
import ctypes
import struct
import threading
from ctypes import wintypes
from . import windows_wpd_probe as api
from .wpd_data_phase_reference import COMMON, MTP


def _unsigned_collection(ole32, results, pid, maximum):
    collection = ctypes.c_void_p()
    key = api._PropertyKey.create(MTP, pid)
    try:
        api._check_hr(api._method(results, 34, ctypes.POINTER(api._PropertyKey),
            ctypes.POINTER(ctypes.c_void_p))(results, ctypes.byref(key),
            ctypes.byref(collection)), 'Get response parameters')
        if not collection.value:
            raise RuntimeError('Null response parameter collection')
        count = wintypes.DWORD()
        api._check_hr(api._method(collection, 3, ctypes.POINTER(wintypes.DWORD))(
            collection, ctypes.byref(count)), 'Get response parameter count')
        if count.value > maximum:
            raise RuntimeError('Oversized response parameter collection')
        values = []
        for index in range(count.value):
            variant = ctypes.create_string_buffer(32)
            try:
                api._check_hr(api._method(collection, 4, wintypes.DWORD, ctypes.c_void_p)(
                    collection, index, variant), 'Get response parameter')
                if struct.unpack_from('<H', variant)[0] != 19:
                    raise RuntimeError('Response parameter is not VT_UI4')
                values.append(struct.unpack_from('<I', variant, 8)[0])
            finally:
                api._check_hr(ole32.PropVariantClear(variant), 'Clear response variant')
        return tuple(values)
    finally:
        api._release(collection)


def _response_parameters(ole32, results):
    return _unsigned_collection(ole32, results, 1004, 5)


class CommandSender:
    """Marshal only the observed no-data map, never a registration data phase."""
    def __init__(self, ole32, device):
        if not isinstance(device, ctypes.c_void_p) or not device.value:
            raise ValueError('Require explicitly supplied open COM device pointer')
        self._ole32 = ole32
        self._device = device
        self._thread = threading.get_ident()

    def _validate(self, request):
        expected = {(COMMON, 1001), (COMMON, 1002), (MTP, 1001), (MTP, 1002)}
        if (set(request) != expected or request[(COMMON, 1001)] != MTP
                or type(request[(COMMON, 1002)]) is not int
                or request[(COMMON, 1002)] != 12):
            raise ValueError('Only exact WPD command12 maps are supported')
        opcode, arguments = request[(MTP, 1001)], request[(MTP, 1002)]
        if (type(opcode) is not int or not 0 <= opcode <= 0xffff
                or type(arguments) is not tuple or len(arguments) > 5
                or any(type(v) is not int or not 0 <= v <= 0xffffffff for v in arguments)):
            raise ValueError('Invalid command opcode/parameters')
        return 12, opcode, arguments, None

    def _make_params(self, request, validated):
        command, opcode, arguments, context = validated
        return api._new_mtp_params(self._ole32, command, opcode=opcode,
                                   args=arguments, context=context)

    def _decode(self, results, request, result):
        result[(MTP, 1003)] = api._get_unsigned(results, api._PropertyKey.create(MTP, 1003))
        result[(MTP, 1004)] = _response_parameters(self._ole32, results)
        return result

    def __call__(self, request):
        if threading.get_ident() != self._thread:
            raise RuntimeError('WPD COM sender must remain on its owning thread')
        if not self._device.value:
            raise RuntimeError('WPD device connection is closed')
        validated = self._validate(request)
        params, results = ctypes.c_void_p(), ctypes.c_void_p()
        try:
            params = self._make_params(request, validated)
            # Do not use diagnostic _send_wpd: it allows omitted HRESULTs.
            send = api._method(self._device, 4, wintypes.DWORD, ctypes.c_void_p,
                               ctypes.POINTER(ctypes.c_void_p))
            api._check_hr(send(self._device, 0, params, ctypes.byref(results)),
                          'IPortableDevice.SendCommand')
            if not results.value:
                raise RuntimeError('WPD SendCommand returned null results')
            error = wintypes.LONG()
            key = api._PropertyKey.create(COMMON, 1003)
            api._check_hr(api._method(results, 20, ctypes.POINTER(api._PropertyKey),
                ctypes.POINTER(wintypes.LONG))(results, ctypes.byref(key),
                ctypes.byref(error)), 'Get required command HRESULT')
            result = {(COMMON, 1003): error.value & 0xffffffff}
            if error.value & 0x80000000:
                return result
            return self._decode(results, request, result)
        finally:
            try:
                api._release(results)
            finally:
                api._release(params)


class DataPhaseSender(CommandSender):
    """Observed WPD13..17 marshalling; writing is opt-in, not authorization.

    Caller must obtain actual camera-operation authorization separately. This
    class does not open devices or establish fresh registration state.
    """
    def __init__(self, ole32, device, *, allow_write=False):
        if type(allow_write) is not bool:
            raise ValueError('Require explicit boolean write policy')
        super().__init__(ole32, device)
        self._allow_write = allow_write

    def _validate(self, request):
        command = request.get((COMMON, 1002))
        required = {13: {1001, 1002}, 14: {1001, 1002, 1007},
                    15: {1006, 1008, 1012}, 16: {1006, 1010, 1012}, 17: {1006}}
        if type(command) is not int or command not in required:
            raise ValueError('Require explicit WPD data-phase command13..17')
        expected = {(COMMON, 1001), (COMMON, 1002)} | {(MTP, p) for p in required[command]}
        if set(request) != expected or request[(COMMON, 1001)] != MTP:
            raise ValueError('Unexpected WPD data-phase properties')
        if command in (14, 16) and not self._allow_write:
            raise ValueError('WPD writes are disabled for this sender')
        if command in (13, 14):
            opcode, arguments = request[(MTP, 1001)], request[(MTP, 1002)]
            if (type(opcode) is not int or not 0 <= opcode <= 0xffff
                    or type(arguments) is not tuple or len(arguments) > 5
                    or any(type(v) is not int or not 0 <= v <= 0xffffffff for v in arguments)):
                raise ValueError('Invalid data-phase opcode/parameters')
            if command == 14:
                size = request[(MTP, 1007)]
                if type(size) is not int or not 0 < size <= 1048576:
                    raise ValueError('Invalid bounded write size')
            return command, opcode, arguments, None
        context = request[(MTP, 1006)]
        if type(context) is not str or not context or len(context) > 4096 or '\0' in context:
            raise ValueError('Invalid transfer context')
        if command in (15, 16):
            count = request[(MTP, 1008 if command == 15 else 1010)]
            data = request[(MTP, 1012)]
            if (type(count) is not int or not 0 < count <= 1048576
                    or type(data) is not bytes or len(data) != count):
                raise ValueError('Invalid transfer buffer/count')
        return command, None, (), context

    def _make_params(self, request, validated):
        params = super()._make_params(request, validated)
        command = validated[0]
        try:
            if command in (14, 16):
                api._set_unsigned(params, api._PropertyKey.create(api._API_OPTIONS_CATEGORY, 3), 3)
            if command == 14:
                api._set_unsigned_large(params, api._PropertyKey.create(MTP, 1007), request[(MTP, 1007)])
            if command in (15, 16):
                pid = 1008 if command == 15 else 1010
                api._set_unsigned(params, api._PropertyKey.create(MTP, pid), request[(MTP, pid)])
                api._set_buffer(params, api._PropertyKey.create(MTP, 1012), request[(MTP, 1012)])
            return params
        except Exception:
            api._release(params)
            raise

    def _decode(self, results, request, result):
        command = request[(COMMON, 1002)]
        key = lambda pid: api._PropertyKey.create(MTP, pid)
        if command in (13, 14):
            result[(MTP, 1006)] = api._get_string(self._ole32, results, key(1006))
            if command == 13:
                # Retain context even if size is absent: adapter will complete
                # the opened phase once before reporting the missing field.
                try:
                    result[(MTP, 1007)] = api._get_unsigned_large(results, key(1007))
                except OSError:
                    pass
                try:
                    result[(MTP, 1013)] = api._get_unsigned(results, key(1013))
                except OSError:
                    pass
            return result
        if command == 15:
            result[(MTP, 1012)] = api._get_buffer(self._ole32, results, key(1012),
                                               max_bytes=request[(MTP, 1008)])
            result[(MTP, 1009)] = api._get_unsigned(results, key(1009))
            return result
        if command == 16:
            result[(MTP, 1011)] = api._get_unsigned(results, key(1011))
            return result
        return super()._decode(results, request, result)


class CapabilitySender(CommandSender):
    """WPD command11 capability query only, no camera registration command."""
    def _validate(self, request):
        if (set(request) != {(COMMON, 1001), (COMMON, 1002)}
                or request[(COMMON, 1001)] != MTP
                or type(request[(COMMON, 1002)]) is not int
                or request[(COMMON, 1002)] != 11):
            raise ValueError('Require exact WPD vendor-opcode query')
        return 11, None, (), None

    def _decode(self, results, request, result):
        codes = _unsigned_collection(self._ole32, results, 1005, 4096)
        if any(code > 0xffff for code in codes):
            raise RuntimeError('Vendor opcode exceeds uint16')
        result[(MTP, 1005)] = codes
        return result
