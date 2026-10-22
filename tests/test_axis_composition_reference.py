import unittest
from camera_install.axis_composition_reference import compose


class AxisCompositionTests(unittest.TestCase):
    def test_identity(self):
        import colorsys
        for rgb in ([0,0,0],[1,1,1],[.4,.1,.1],[.8,.5,.5],[.2,.8,.4]):
            result = compose(rgb,colorsys.rgb_to_hls(*rgb)[0]*6,0,0)
            for a,b in zip(result,rgb): self.assertAlmostEqual(a,b,places=14)

    def test_hue(self):
        result = compose([.8,.2,.2],1/6,0,0)
        for a,b in zip(result,[.8,.3,.2]): self.assertAlmostEqual(a,b,places=14)

    def test_positive_saturation_gain_and_input_dependency(self):
        for rgb,weight,expected in (([.8,.2,.2],.06,[.89,.11,.11]),([.4,.1,.1],.02,[.415,.085,.085])):
            for a,b in zip(compose(rgb,0,weight,0),expected): self.assertAlmostEqual(a,b,places=14)

    def test_gamut_compression(self):
        result = compose([1,0,0],0,0,.1)
        self.assertAlmostEqual(result[0],1,places=14)
        self.assertAlmostEqual(result[1],.08442887702247637,places=14)

    def test_negative_saturation(self):
        result = compose([.8,.2,.2],0,-1,0)
        self.assertEqual(result,(.5,.5,.5))

    def test_invalid_domain(self):
        for rgb in ([float('nan'),0,0],[-1,0,0],[0,0,2]):
            with self.assertRaises(ValueError): compose(rgb,0,0,0)

    def test_native_fixed_point_overshoot(self):
        from camera_install.default_axis_reference import transform
        rgb=[.57014000415802,1.0000203847885132,.2242373824119568]
        expected=[.5701377750037573,1,.22424976216233294]
        with self.assertRaises(ValueError): transform(rgb,[(0,0,0)]*6)
        result=transform(rgb,[(0,0,0)]*6,allow_fixed_point_overshoot=True)
        for a,b in zip(result,expected): self.assertAlmostEqual(a,b,places=14)
