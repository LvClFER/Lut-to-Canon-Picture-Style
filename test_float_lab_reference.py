import unittest
from camera_install.float_lab_reference import forward, inverse


class FloatLabTests(unittest.TestCase):
    def test_black_and_reference_whites(self):
        for mode, xyz in ((12,[.9505,1,1.089]),(1,[.9642,1,.8249])):
            self.assertEqual(forward([0,0,0],mode),[0,0,0])
            self.assertEqual(forward(xyz,mode),[100,0,0])
            for a,b in zip(inverse([100,0,0],mode),xyz):
                self.assertAlmostEqual(a,b,places=14)

    def test_piecewise_roundtrip(self):
        for mode in (1,12):
            for xyz in ([.001,.002,.003],[.2,.3,.4],[.8,.6,.1]):
                for a,b in zip(inverse(forward(xyz,mode),mode),xyz):
                    self.assertAlmostEqual(a,b,places=13)

    def test_invalid_inputs(self):
        for bad in ([0,0],[0,float('nan'),0],[0,float('inf'),0]):
            with self.assertRaises(ValueError): forward(bad,12)
            with self.assertRaises(ValueError): inverse(bad,12)
