import unittest
from camera_install.legacy_sector_reference import weights,compose,transform,decode_group,target_selector
import struct


class LegacySectorTests(unittest.TestCase):
    def points(self):
        return {0:(290/60,.06,.2),1:(250/60,0,0),2:(330/60,.4,.6),3:(-.1,-.01,0)}

    def test_captured_active_case(self):
        hsl=[5,1/15,.0625]
        w=weights(hsl,self.points())
        for a,b in zip(w,[.7499999999999997,.9803921568627451,.3125]):
            self.assertAlmostEqual(a,b,places=14)
        expected=[4.977022058823529,.06436887254901962,.0625]
        for a,b in zip(compose(hsl,self.points()[3],w),expected):
            self.assertAlmostEqual(a,b,places=14)

    def test_outside_region_unchanged(self):
        self.assertEqual(transform([0,1,0],self.points()),(0,1,0))

    def test_unmapped_gamut_rejected(self):
        with self.assertRaises(ValueError): compose([0,.1,.05],[0,1,0],[1,1,1])

    def test_native_delta_limits_exclude_hue(self):
        raw=struct.pack('<19i',1,1,4,0,180,50,50,1,0,0,0,2,360,100,100,3,180,80,-80)
        self.assertEqual(decode_group(raw)[3],(3.,.5,-.5))

    def test_delta_limits_follow_selector_not_global_constant(self):
        raw=struct.pack('<19i',1,1,4,0,180,30,40,1,120,20,10,2,240,80,90,3,180,80,-80)
        group=decode_group(raw)
        for a,b in zip(group[3],(1.,.5,-.3)): self.assertAlmostEqual(a,b)

    def test_fifth_point_overrides_delta_and_unsupported_nodes_bypass(self):
        words=[1,1,5,0,180,50,50,1,0,0,0,2,360,100,100,3,0,0,0,4,200,60,60]
        group=decode_group(struct.pack('<23i',*words))
        changed=target_selector([.25,.75,.25],group,33)
        for a,b in zip(changed[3],(1/3,.1,.1)): self.assertAlmostEqual(a,b)
        self.assertIs(target_selector([.25,.75,.25],group,25),group)

    def test_target_quantization_repositions_centre_without_changing_width(self):
        words=[1,1,5,0,193,43,47,1,100,10,15,2,300,90,85,3,0,0,0,4,213,53,57]
        group=decode_group(struct.pack('<23i',*words))
        changed=target_selector([.25,.75,.25],group,10)
        self.assertNotEqual(changed[0],group[0])
        for c in range(3):
            self.assertAlmostEqual(changed[0][c]-changed[1][c],group[0][c]-group[1][c])
            self.assertAlmostEqual(changed[2][c]-changed[0][c],group[2][c]-group[0][c])

    def test_observed_strong_boundary_intersections(self):
        cases=[([.5,0,.5],[2.25,.5,.75]),
               ([.5,.5,.5],[2.1666666666666665,2/3,2/3]),
               ([.5,.5,-.5],[2.1666666666666665,2/3,.33333333333333337])]
        for delta,expected in cases:
            result=compose([2,.5,.5],delta,[2/3,1,1],allow_strong_gamut=True)
            for a,b in zip(result,expected):self.assertAlmostEqual(a,b,places=14)
