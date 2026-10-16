import itertools
import unittest
from camera_install.integer_tetrahedral_reference import interpolate,table


class IntegerTetrahedralTests(unittest.TestCase):
    def test_identity_all_six_orders(self):
        values=table('identity')
        for coordinates in itertools.permutations((3*16,19*16,51*16)):
            expected=[(v>>4)*64 for v in coordinates]
            self.assertEqual(interpolate(values,coordinates),[expected[0],expected[2],expected[1]])

    def test_discard_four_low_bits(self):
        values=table('signed')
        self.assertEqual(interpolate(values,[1008,2000,3008]),interpolate(values,[1023,2015,3023]))

    def test_impulse_vertex(self):
        self.assertEqual(interpolate(table('impulse'),[4*1024,5*1024,6*1024]),[6400,19200,12800])

    def test_safe_domain(self):
        with self.assertRaises(ValueError): interpolate(table('identity'),[-1,0,0])
        for value in (9217, True, 1.0):
            with self.assertRaises(ValueError): interpolate(table('identity'),[value,0,0])

    def test_upper_endpoint_without_padding(self):
        values=table('identity')
        for coordinates in itertools.product((0,4095,8191,9216),repeat=3):
            expected=[(v>>4)*64 for v in coordinates]
            self.assertEqual(interpolate(values,coordinates),[expected[0],expected[2],expected[1]])
