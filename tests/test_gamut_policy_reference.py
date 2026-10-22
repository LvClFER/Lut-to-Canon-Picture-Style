import unittest
from camera_install.gamut_policy_reference import correct


class GamutPolicyTests(unittest.TestCase):
    def matrix(self,gain=1.25):
        values=[0.]*57
        values[0]=gain;values[20]=values[40]=1.
        return values

    def test_in_gamut_bypass(self):
        self.assertEqual(correct([.2,.4,.8],self.matrix()),[.25,.4,.8])

    def test_native_binary_search_branch(self):
        expected=[.9996814373240988,.20025485014072147,.5]
        self.assertEqual(correct([1,0,.5],self.matrix()),expected)

    def test_nonintersecting_ray_is_bounded(self):
        values=self.matrix(1);values[40]=2.
        with self.assertRaises(ValueError):correct([.75,1,.75],values)

    def test_unsafe_source_rejected(self):
        with self.assertRaises(ValueError):correct([float('nan'),0,0],self.matrix())
        with self.assertRaises(ValueError):correct([-1,0,0],self.matrix())
