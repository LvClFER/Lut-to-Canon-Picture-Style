import struct
import unittest
import numpy as np
from camera_install.legacy_dense9_reference import dense9_flag0


class LegacyDenseNineTests(unittest.TestCase):
    def test_zero_and_constant_white(self):
        for sample, expected in ((0, 0),):
            record = struct.pack('<3H',12,3,33)+struct.pack('<H',sample)*107811
            grid = dense9_flag0(record)
            self.assertEqual(grid.shape,(3,9,9,9))
            self.assertTrue(np.all(grid == expected))

    def test_white_retains_native_integer_truncation(self):
        # Own-host 1b670/196a0 comparison confirms these 254-valued samples;
        # do not force a mathematically ideal constant-white result of255.
        record=struct.pack('<3H',12,3,33)+struct.pack('<H',4095)*107811
        values,counts=np.unique(dense9_flag0(record),return_counts=True)
        self.assertEqual(values.tolist(),[254.,255.])
        self.assertEqual(counts.tolist(),[270,1917])

    def test_source_geometry_is_not_guessed(self):
        for record in (b'', None, bytes(215628),
                       struct.pack('<3H',12,3,33)+struct.pack('<H',4096)*107811):
            with self.assertRaises(ValueError):
                dense9_flag0(record)
