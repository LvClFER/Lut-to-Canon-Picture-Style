import unittest
from camera_install.legacy_six_axis_reference import sector_weights,transform
from camera_install.default_axis_reference import sector_weights as modern_weights


class PrecedingSixAxisTests(unittest.TestCase):
    def test_preserve_old_wrap_endpoint_order(self):
        hue=5.166666666666667
        self.assertEqual(sector_weights(hue)[0],0.)
        self.assertGreater(modern_weights(hue)[0],0.)
        result=transform([.75,0,.625],[(10,0,0)]+[(0,0,0)]*5)
        for a,b in zip(result,[.75,0,.6249999999999998]):self.assertAlmostEqual(a,b,places=14)

    def test_left_wrap_endpoint_blend(self):
        self.assertAlmostEqual(sector_weights(5.833333333333333)[0],.9995878961405604,places=14)

    def test_hard_width_and_conservation(self):
        self.assertEqual(sector_weights(.5,0),[0.,1.,0.,0.,0.,0.])
        for width in (0,5,10,20,30,60):
            for h in (0,.1,.5,1.1,2.8333333333333335,5.833333333333333):
                self.assertAlmostEqual(sum(sector_weights(h,width)),1.)

    def test_invalid_width(self):
        for width in (-1,float('nan')):
            with self.assertRaises(ValueError):sector_weights(0,width)

    def test_owning_sector_uses_its_width(self):
        widths=[0,5,10,20,30,60]
        for hue in (.49,.5,1.49,2.51,4.49,5.9):
            owner=int((hue+.5)//1)%6
            self.assertEqual(sector_weights(hue,widths),sector_weights(hue,widths[owner]))
        with self.assertRaises(ValueError):sector_weights(0,[20]*5)
