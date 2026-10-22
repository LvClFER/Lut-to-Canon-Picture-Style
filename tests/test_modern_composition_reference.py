import unittest
from camera_install.modern_composition_reference import sample17


class ModernCompositionTests(unittest.TestCase):
    def test_constant_and_all_fraction_orders(self):
        values = [v for v in (12., 34., 56.) for _ in range(4913)]
        import itertools
        for rgb in itertools.permutations((1., 7., 15.)):
            self.assertEqual(sample17(values, rgb), [12., 34., 56.])

    def test_endpoint_correction(self):
        values = [float((r, g, b)[c] * 16) for c in range(3)
                  for r in range(17) for g in range(17) for b in range(17)]
        self.assertEqual(sample17(values, (240., 255., 256.)), [240., 256., 256.])

    def test_invalid_geometry_and_coordinates(self):
        for values, rgb in (([], (0, 0, 0)), ([0.] * 14739, (-1, 0, 0)),
                            ([0.] * 14739, (float('nan'), 0, 0))):
            with self.assertRaises(ValueError):
                sample17(values, rgb)
