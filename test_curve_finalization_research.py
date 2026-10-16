import unittest
from camera_install.curve_finalization_research import finalize_samples


class FinalizationTests(unittest.TestCase):
    def test_identity_unchanged(self):
        self.assertEqual(finalize_samples([(0, 0), (1, 1)], [0, .25, .5, .75, 1]), [0, .25, .5, .75, 1])

    def test_following_knot_cap_can_lower_a_sample(self):
        self.assertEqual(finalize_samples([(0, 0), (.5, .8), (1, .3)], [0, .5, .9, .6, .3]), [0, .5, .8, .3, .3])

    def test_invalid_coverage_refused(self):
        with self.assertRaises(ValueError):
            finalize_samples([(0, 0)], [0, 1])
