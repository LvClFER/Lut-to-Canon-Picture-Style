import itertools
import unittest
from camera_install.integer_tetrahedral_reference import interpolate,profile_rgb16,table


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

    def test_profile_rgb16_identity_and_input_precision(self):
        values=[v//2 for v in table('identity')]
        for point in itertools.product((0,127,128,8191,8192,32768,65535),repeat=3):
            self.assertEqual(profile_rgb16(values,point),[v&~127 for v in point])

    def test_profile_rgb16_wraps_before_clipping(self):
        for constant,expected in ((-1,0),(256,65535),(2**23,0),(2**24,0),(2**24+1,256)):
            self.assertEqual(profile_rgb16([constant]*3000,[0,0,0]),[expected]*3)

    def test_profile_rgb16_all_orders_and_channel_order(self):
        values=[channel*10 for channel in range(3) for _ in range(1000)]
        for point in itertools.permutations((127,10000,30000)):
            self.assertEqual(profile_rgb16(values,point),[0,2560,5120])

    def test_profile_rgb16_observed_native_vectors(self):
        cases=(
            ('signed',[0,65535,0],[14052,18916,23780]),
            ('signed',[0,65535,65535],[65535,65535,0]),
            ('modular',[10000,20000,30000],[41184,47072,52960]),
            ('modular',[20000,30000,10000],[50544,56432,62320]),
            ('modular',[30000,10000,20000],[37440,43328,49216]),
            ('overflow',[10000,20000,30000],[0,0,65535]),
            ('overflow',[20000,30000,10000],[0,65535,0]),
            ('overflow',[30000,10000,20000],[0,65535,65535]),
        )
        for pattern,point,expected in cases:
            with self.subTest(pattern=pattern,point=point):
                self.assertEqual(profile_rgb16(table(pattern),point),expected)

    def test_profile_rgb16_rejects_invalid_data(self):
        for point in ((True,0,0),(-1,0,0),(65536,0,0),(1.0,0,0),(0,0)):
            with self.subTest(point=point),self.assertRaises(ValueError):
                profile_rgb16(table('identity'),point)
        for values in ([0]*2999,[0]*2999+[2**31],[0]*2999+[1.0]):
            with self.assertRaises(ValueError):profile_rgb16(values,[0,0,0])
