import unittest
import numpy as np
from camera_install.compact_grid_reference import compact_flag0, compact_flag1, compact_flag2, synthetic, trilinear


class CompactGridTests(unittest.TestCase):
    def test_integer_boundary_uses_distinct_constants(self):
        result = compact_flag0(synthetic('scrambled'))
        self.assertEqual(result[0,0,0,8],69)
        self.assertEqual(result[0,0,0,9],69)
        self.assertEqual(result[0,0,0,1],138)
        self.assertEqual(result[0,0,1,8],152)

    def test_integer_identity(self):
        np.testing.assert_array_equal(compact_flag0(synthetic('identity'))[0,:,0,0],
                                      [0,32,64,96,128,160,192,224,256,256])
    def test_identity_coordinates_and_planar_storage(self):
        result = compact_flag2(synthetic('identity'))
        self.assertEqual(result.shape, (3,10,10,10))
        np.testing.assert_allclose(result[0,:,0,0], [0,32,64,96,128,160,192,224,255,255], atol=1e-12)

    def test_constant(self):
        result = compact_flag2(synthetic('constant'))
        np.testing.assert_allclose(result[:,3,5,7], [51,102,204], atol=1e-12)

    def test_multilinear_product(self):
        actual = trilinear(synthetic('product'), np.array([[.13,.42,.83]]))
        np.testing.assert_allclose(actual, [[.13*.42,.42*.83,.83*.13]], atol=1e-14)

    def test_invalid_shape(self):
        with self.assertRaises(ValueError): trilinear(np.zeros((2,2,2,3)), [[0,0,0]])

    def test_nonfinite(self):
        with self.assertRaises(ValueError): trilinear(synthetic('identity'), [[float('nan'),0,0]])

    def test_diagonal_boundary_not_axiswise_extension(self):
        result = compact_flag1(synthetic('product'))
        self.assertAlmostEqual(result[0,8,8,0], 256.8784313725491, places=10)
        self.assertAlmostEqual(result[0,9,9,0], result[0,8,8,0], places=12)

    def test_boundary_identity(self):
        result = compact_flag1(synthetic('identity'))
        np.testing.assert_allclose(result[0,:,0,0], [0,32,64,96,128,160,192,224,256,256], atol=1e-12)
