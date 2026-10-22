import unittest
from camera_install.cached_curve_reference import evaluate


class CachedCurveTests(unittest.TestCase):
    def test_fractional_position(self):
        self.assertEqual(evaluate([0,.5,1], .25), .25)

    def test_upper_boundary(self):
        self.assertEqual(evaluate([0,.5,.8], 1), .8)
        self.assertEqual(evaluate([0,.5,.8], 1.1), .8)

    def test_nonmonotonic_cache(self):
        self.assertEqual(evaluate([0,1,0], .75), .5)

    def test_rejects_unsafe_domain(self):
        with self.assertRaises(ValueError): evaluate([0,1], -.01)
        with self.assertRaises(ValueError): evaluate([0,1], float('nan'))
        with self.assertRaises(ValueError): evaluate([0], .5)

    def test_negative_subsample_requires_explicit_opt_in(self):
        # Both indices are zero, but native interpolation still multiplies
        # and adds; preserve that rounding rather than returning values[0].
        self.assertEqual(evaluate([.2,.5,1],-.25,allow_negative_subsample=True),.20000000000000004)
        with self.assertRaises(ValueError):evaluate([.2,.5,1],-.5,allow_negative_subsample=True)
