import struct,unittest
from camera_install.compact_cache_reference import build_compact_cache


class CompactCacheTests(unittest.TestCase):
    def test_zero_source_is_exact_for_explicit_observed_policies(self):
        record=struct.pack('<3H',12,3,33)+bytes(215622)
        for flag in (0,1):
            for coefficients in (False,True):
                self.assertEqual(build_compact_cache(record,grid_flag=flag,
                                                    coefficient_mode=coefficients),bytes(4096))

    def test_unknown_policy_and_invalid_source_are_rejected(self):
        for flag in (-1,2,True,1.0,None):
            with self.assertRaises(ValueError):
                build_compact_cache(b'',grid_flag=flag,coefficient_mode=False)
        for coefficients in (0,1,None):
            with self.assertRaises(ValueError):
                build_compact_cache(b'',grid_flag=1,coefficient_mode=coefficients)
        for source in (bytes(215628),b'',None):
            with self.assertRaises(ValueError):
                build_compact_cache(source,grid_flag=1,coefficient_mode=False)
