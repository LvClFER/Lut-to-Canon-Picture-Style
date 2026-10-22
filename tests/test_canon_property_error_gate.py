"""Synthetic DLL contract tests; no Canon DLL or fixtures required."""
import ctypes
import unittest
from canon_engine import EdsCFParse


class FakePropertyDll:
    def __init__(self, rc, size_rc=0):
        self.rc = rc
        self.size_rc = size_rc
        self.data_calls = 0

    def EdsCfpGetPropertySize(self, ref, prop, param, kind, size):
        kind._obj.value = 32
        size._obj.value = 16
        return self.size_rc

    def EdsCfpGetPropertyData(self, ref, prop, param, size, dest):
        self.data_calls += 1
        ctypes.memset(dest, 0, size)
        return self.rc


class CanonPropertyErrorGateTests(unittest.TestCase):
    def api(self, rc):
        api = EdsCFParse.__new__(EdsCFParse)
        api.dll = FakePropertyDll(rc)
        return api

    def test_zero_filled_error_buffer_is_never_returned(self):
        api = self.api(0x2d)
        with self.assertRaisesRegex(RuntimeError, 'GetPropertyData.*0000002D'):
            api.get_property(None, 0x40001070, 16)
        self.assertEqual(api.dll.data_calls, 1)

    def test_successful_zero_data_is_not_rejected_by_pixel_heuristic(self):
        api = self.api(0)
        self.assertEqual(api.get_property(None, 0x40001070, 16), bytes(16))

    def test_size_mismatch_stops_before_data_read(self):
        api = self.api(0)
        with self.assertRaisesRegex(RuntimeError, 'expected 32'):
            api.get_property(None, 0x40001070, 32)
        self.assertEqual(api.dll.data_calls, 0)

    def test_missing_property_size_error_stops_before_data_read(self):
        api = self.api(0)
        api.dll.size_rc = 0x50
        with self.assertRaisesRegex(RuntimeError, 'GetPropertySize.*00000050'):
            api.get_property(None, 0x40001010)
        self.assertEqual(api.dll.data_calls, 0)

    def test_error_rejects_nonzero_partial_data_too(self):
        api = self.api(0x2d)

        def partial_read(ref, prop, param, size, dest):
            api.dll.data_calls += 1
            ctypes.memset(dest, 0x7f, size)
            return 0x2d

        api.dll.EdsCfpGetPropertyData = partial_read
        with self.assertRaisesRegex(RuntimeError, 'GetPropertyData.*0000002D'):
            api.get_property(None, 0x40001070, 16)
        self.assertEqual(api.dll.data_calls, 1)


if __name__ == '__main__':
    unittest.main()
