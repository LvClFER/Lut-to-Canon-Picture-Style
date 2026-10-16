import unittest
from camera_install.lab_math_reference import rgb_to_lab, lab_to_rgb


class LabMathTests(unittest.TestCase):
    def test_black_white(self):
        for bits in (8,12,16,24):
            for mode in (1,2):
                self.assertEqual(rgb_to_lab([0,0,0],bits,mode),[0,0,0])
                self.assertEqual(lab_to_rgb([0,0,0],bits,mode),[0,0,0])
                self.assertEqual(lab_to_rgb(rgb_to_lab([2**bits-1]*3,bits,mode),bits,mode),[2**bits-1]*3)

    def test_captured_primary(self):
        self.assertEqual(rgb_to_lab([255,0,0],8,1),[3488670,5249782,4405512])
        self.assertEqual(lab_to_rgb([3488670,5249782,4405512],8,1),[255,0,0])

    def test_domain(self):
        for rgb,bits in (([-1,0,0],8),([256,0,0],8),([0,0,0],10),([0.,0,0],8)):
            with self.assertRaises(ValueError): rgb_to_lab(rgb,bits,1)
