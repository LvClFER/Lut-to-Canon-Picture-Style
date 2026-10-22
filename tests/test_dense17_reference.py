import unittest
import numpy as np
from camera_install.dense17_reference import convert17


class Dense17Tests(unittest.TestCase):
    def test_identity_endpoint_and_planar_layout(self):
        axis = np.arange(33) / 32
        source = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1)
        actual = convert17(source)
        self.assertEqual(actual.shape, (3, 17, 17, 17))
        np.testing.assert_array_equal(actual[:, 0, 0, 0], [0, 0, 0])
        np.testing.assert_array_equal(actual[:, -1, -1, -1], [255.75] * 3)
        np.testing.assert_array_equal(actual[:, 3, 7, 11], [48, 112, 176])

    def test_constants_clipped_and_bad_geometry(self):
        source = np.ones((33, 33, 33, 3)) * [2, -.5, .25]
        np.testing.assert_array_equal(convert17(source)[:, 8, 8, 8], [255.75, 0, 64])
        with self.assertRaises(ValueError):
            convert17(np.zeros((17, 17, 17, 3)))
