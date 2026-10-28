"""Explicit Windows WPD connection; no enumeration or Canon software dependency.

Construction is inert. Entering opens the supplied device and needs separate
user authorization before real camera use. Not enabled in the editor UI.
"""
import ctypes
import sys
import threading
from ctypes import wintypes
from . import windows_wpd_probe as api
from .wpd_command_sender import CommandSender, DataPhaseSender, CapabilitySender


def _system_com():
    if sys.platform != 'win32':
        raise RuntimeError('WPD connection requires Windows')
    ole32 = ctypes.WinDLL('ole32')
    ole32.CoInitializeEx.argtypes = (ctypes.c_void_p, wintypes.DWORD)
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = ()
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = (ctypes.POINTER(api._Guid), ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(api._Guid), ctypes.POINTER(ctypes.c_void_p))
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    ole32.CoTaskMemFree.restype = None
    ole32.PropVariantClear.argtypes = (ctypes.c_void_p,)
    ole32.PropVariantClear.restype = ctypes.c_long
    return ole32


class WpdConnection:
    def __init__(self, device_id, *, allow_write=False, allow_control=False, com_factory=_system_com):
        if (type(device_id) is not str or not device_id or len(device_id) > 32768
                or '\0' in device_id or type(allow_write) is not bool
                or type(allow_control) is not bool):
            raise ValueError('Require explicit bounded device ID/write policy')
        self._id, self._write, self._factory = device_id, allow_write, com_factory
        self._control = allow_control
        self._device = ctypes.c_void_p()
        self._client = ctypes.c_void_p()
        self._com = None
        self._initialized = self._open_attempted = self._used = False
        self._thread = None
        self.commands = self.data = None
        self.capabilities = None

    def _cleanup(self):
        errors = []
        client = self._client
        self._client = ctypes.c_void_p()
        if client.value:
            try:
                api._release(client)
            except Exception as error:
                errors.append(error)
        # Invalidate all senders sharing this pointer before releasing COM.
        device = ctypes.c_void_p(self._device.value)
        self._device.value = None
        if device.value:
            try:
                if self._open_attempted:
                    api._check_hr(api._method(device, 8)(device), 'IPortableDevice.Close')
            except Exception as error:
                errors.append(error)
            finally:
                try:
                    api._release(device)
                except Exception as error:
                    errors.append(error)
        if self._initialized:
            self._initialized = False
            try:
                self._com.CoUninitialize()
            except Exception as error:
                errors.append(error)
        return errors

    def __enter__(self):
        if self._used:
            raise RuntimeError('WPD connection is single-use')
        self._used = True
        self._thread = threading.get_ident()
        try:
            self._com = self._factory()
            initialized = self._com.CoInitializeEx(None, 0)
            # Do not borrow an unknown apartment after RPC_E_CHANGED_MODE.
            api._check_hr(initialized, 'CoInitializeEx')
            if initialized not in (0, 1):
                raise RuntimeError('Unexpected COM initialization success code')
            self._initialized = True
            self._device = api._create_instance(self._com, api._DEVICE_CLSID, api._DEVICE_IID)
            self._client = api._create_instance(self._com, api._VALUES_CLSID, api._VALUES_IID)
            client = self._client
            if not self._device.value or not client.value:
                raise RuntimeError('COM creation returned null interface')
            api._set_string(client, api._PropertyKey.create(api._CLIENT_CATEGORY, 2), 'Style Studio')
            for pid, value in ((3, 1), (4, 0), (5, 0),
                               (9, api._GENERIC_READ_WRITE if self._write or self._control else api._GENERIC_READ)):
                api._set_unsigned(client, api._PropertyKey.create(api._CLIENT_CATEGORY, pid), value)
            self._open_attempted = True
            api._check_hr(api._method(self._device, 3, ctypes.c_wchar_p, ctypes.c_void_p)(
                self._device, self._id, client), 'IPortableDevice.Open')
            self._client = ctypes.c_void_p()
            api._release(client)
            self.commands = CommandSender(self._com, self._device)
            self.data = DataPhaseSender(self._com, self._device, allow_write=self._write)
            self.capabilities = CapabilitySender(self._com, self._device)
            return self
        except BaseException as original:
            errors = self._cleanup()
            original.connection_cleanup_completed=not errors
            if errors:
                original.add_note(f'WPD connection cleanup also failed: {len(errors)} stage(s)')
            raise

    def __exit__(self, kind, error, traceback):
        if threading.get_ident() != self._thread:
            raise RuntimeError('WPD connection must close on its owning thread')
        errors = self._cleanup()
        if error is not None:error.connection_cleanup_completed=not errors
        if errors:
            if error is not None:
                error.add_note(f'WPD connection cleanup also failed: {len(errors)} stage(s)')
            else:
                raise RuntimeError('WPD connection cleanup incomplete') from errors[0]
        return False
