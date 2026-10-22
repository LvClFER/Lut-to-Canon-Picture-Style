import unittest
from camera_install.polynomial_color_reference import basis, transform, disk_coefficients, EXPONENTS
import struct


class PolynomialTests(unittest.TestCase):
    def test_unique_terms(self):
        self.assertEqual(len(set(EXPONENTS)), 19)
        self.assertTrue(all(1 <= sum(term) <= 3 for term in EXPONENTS))

    def test_basis(self):
        values = basis([.2,.4,.8])
        self.assertEqual(values[:3], [.2,.4,.8])
        self.assertAlmostEqual(values[13], .2*.4*.8)

    def test_identity_coefficients(self):
        coefficients = [0.] * 57
        for row in range(3): coefficients[row*19+row] = 1
        self.assertEqual(transform([.2,.4,.8], coefficients), [.2,.4,.8])

    def test_native_multiplication_order_is_exact(self):
        r,g,b=32/255,64/255,160/255
        values=basis([r,g,b])
        self.assertEqual(values[18],b*b*b)
        self.assertEqual(values[14],r*b*b)
        self.assertNotEqual(values[18],b**3)
        self.assertNotEqual(values[14],r*(b*b))

    def test_invalid_data(self):
        with self.assertRaises(ValueError): basis([1,2])
        with self.assertRaises(ValueError): transform([1,2,3], [0]*56)
        with self.assertRaises(ValueError): basis([float('nan'),1,2])

    def test_disk_coefficients_ignore_each_padding_word(self):
        words = [0] * 60
        for row in range(3):
            words[row*20+row] = 65536
            words[row*20+19] = 12345
        coefficients = disk_coefficients(struct.pack('>60i', *words))
        self.assertEqual(transform([.2,.4,.8], coefficients), [.2,.4,.8])
