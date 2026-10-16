import unittest
import numpy as np
from camera_install.curve_bspline_research import quadratic_samples


class SplineTests(unittest.TestCase):
    def test_identity(self):
        np.testing.assert_allclose(quadratic_samples([[0, 0], [.5, .5], [1, 1]], 256), np.arange(256) / 255, atol=1e-15)

    def test_interpolates_control_points(self):
        samples = quadratic_samples([[0, 0], [.5, .25], [1, 1]], 257)
        self.assertEqual(samples[128], .25)
        self.assertEqual(samples[-1], 1.)

    def test_duplicate_x_refused(self):
        with self.assertRaises(ValueError):
            quadratic_samples([[0, 0], [0, .5], [1, 1]], 256)
