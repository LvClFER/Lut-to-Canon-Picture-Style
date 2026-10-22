import struct
import unittest
from camera_install.legacy_axis_reference import adjustments,transform


class LegacyAxisTests(unittest.TestCase):
    def block(self,values=(0,0,0)):
        first=[5,0,0,0,0,1,0,0,0,2,0,0,0,3,0,0,0,5,0,0,0]
        second=[5,0,180,50,50,1,0,0,0,2,360,100,100,3,*values,5,5,5,5]
        return struct.pack('<44i',2,2,*first,*second)

    def test_verified_global_geometry(self):
        self.assertEqual(adjustments(self.block((10,10,10))),(10,10,10))
        damaged=bytearray(self.block());struct.pack_into('<i',damaged,24*4,1)
        with self.assertRaises(ValueError):adjustments(damaged)

    def test_positive_saturation_depends_on_original_saturation(self):
        self.assertEqual(transform([.5,.5,.5],(0,10,0)),(.5,.5,.5))
        for a,b in zip(transform([.25,.75,.25],(0,10,0)),(.1875,.8125,.1875)):
            self.assertAlmostEqual(a,b,places=14)

    def test_negative_saturation_has_linear_gain(self):
        for a,b in zip(transform([.25,.75,.25],(0,-10,0)),(.275,.725,.275)):
            self.assertAlmostEqual(a,b,places=14)

    def test_gray_luminance_protected(self):
        self.assertEqual(transform([.5,.5,.5],(10,0,10)),(.5,.5,.5))

    def test_invalid_adjustment(self):
        with self.assertRaises(ValueError):transform([0,0,0],(float('nan'),0,0))

    def test_fixed_point_overshoot_is_explicit(self):
        rgb=[1+1/2**24,.25,.125]
        with self.assertRaises(ValueError):transform(rgb,(10,10,5))
        result=transform(rgb,(10,10,5),allow_fixed_point_overshoot=True)
        self.assertTrue(all(0<=v<=1 for v in result))

    def test_invalid_rgb_rejected_before_coordinate_math(self):
        for rgb in ([],[0,0],[0,0,0,0],[float('inf'),0,0],[-.1,0,0],[1.002,0,0]):
            with self.assertRaises(ValueError):transform(rgb,(0,0,0),allow_fixed_point_overshoot=True)

    def test_combined_controls_use_original_coordinate(self):
        from unittest.mock import patch
        rgb=[.8,.2,.2]
        with patch('camera_install.legacy_axis_reference.compose',return_value=rgb) as mocked:
            transform(rgb,(10,10,5))
        args=mocked.call_args.args
        self.assertEqual(args[1],10/60)
        self.assertAlmostEqual(args[2],.06)
        self.assertAlmostEqual(args[3],.03)
