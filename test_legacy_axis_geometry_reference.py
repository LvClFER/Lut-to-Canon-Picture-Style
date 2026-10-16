import struct
import unittest
from camera_install.legacy_axis_geometry_reference import decode,helper,transform
from camera_install.legacy_six_axis_reference import transform as canonical


class GeometryTests(unittest.TestCase):
    def test_three_groups_use_circular_neighbors_and_exact_geometry(self):
        groups=[]
        for low,high in ((0,60),(60,120),(120,360)):
            groups.extend([5,0,(low+high)//2,50,50,1,low,0,0,
                           2,high,100,100,3,0,0,0,5,10,0,0])
        raw=struct.pack('<65i',2,3,*groups)
        for rgb in ([.2,.1,.1],[.1,.2,.1],[.1,.1,.2],[.5,.5,.5]):
            for actual,expected in zip(transform(rgb,raw),rgb):
                self.assertAlmostEqual(actual,expected,places=14)
        with self.assertRaises(ValueError):transform([.2,.1,.1],raw[:-4])
        with self.assertRaises(ValueError):transform([.2,.1,.1],raw+bytes(4))

    def test_signed_red_lower_bound_matches_wrapped_interval(self):
        words=[5,0,10,10,18,1,-10,0,0,2,30,20,36,3,0,0,0,5,10,10,0]
        signed=decode(struct.pack('<21i',*words))
        words[6]=350
        wrapped=decode(struct.pack('<21i',*words))
        for rgb in ([.2,.18,.18],[.2,.18,.19],[.2,.19,.18]):
            self.assertEqual(helper(rgb,signed,signed,signed),
                             helper(rgb,wrapped,wrapped,wrapped))
        words[6]=-361
        with self.assertRaises(ValueError):decode(struct.pack('<21i',*words))

    def block(self,rotation=0,span=30,sbounds=(0,100),lbounds=(0,100)):
        groups=[]
        for i in range(6):
            centre=(i*60+rotation)%360
            groups.extend([5,0,centre,50,50,1,(centre-span)%360,*sbounds[:1],*lbounds[:1],
                           2,(centre+span)%360,sbounds[1],lbounds[1],3,
                           *((10,-10,10) if i%2==0 else (-10,10,-10)),5,20,0,0])
        return struct.pack('<128i',2,6,*groups)

    def test_canonical_path_matches_separate_reference(self):
        values=[(10,-10,10),(-10,10,-10)]*3
        for r in range(5):
            for g in range(5):
                for b in range(5):
                    rgb=[r/4,g/4,b/4]
                    for a,v in zip(transform(rgb,self.block()),canonical(rgb,values)):
                        self.assertAlmostEqual(a,v,places=14)

    def test_saturation_bounds_bypass_low_chroma(self):
        rgb=[.55,.5,.5]
        for a,b in zip(transform(rgb,self.block(sbounds=(20,80))),rgb):
            self.assertAlmostEqual(a,b,places=14)

    def test_lightness_bounds_bypass_dark_sample(self):
        rgb=[.1,0,0]
        for a,b in zip(transform(rgb,self.block(lbounds=(20,80))),rgb):
            self.assertAlmostEqual(a,b,places=14)

    def test_reject_unknown_block_layout(self):
        with self.assertRaises(ValueError):transform([.5,.3,.2],bytes(512))
        raw=list(struct.unpack('<21i',self.block()[8:92]));raw[17]=4
        with self.assertRaises(ValueError):decode(struct.pack('<21i',*raw))

    def test_wrap_transition_preserves_native_absolute_hue_arithmetic(self):
        words=list(struct.unpack('<128i',self.block()))
        for i in range(6):words[16+21*i:19+21*i]=[0,0,0]
        words[16]=10
        rgb=[.28125,.031250059604644775,.125]
        changed=transform(rgb,struct.pack('<128i',*words))
        self.assertEqual([(v-old)+old for v,old in zip(changed,rgb)],
                         [.28125,.031250059604644775,.09484617466110981])

    def test_fixed_point_overshoot_requires_opt_in(self):
        rgb=[1+1/2**24,.25,.125]
        with self.assertRaises(ValueError):transform(rgb,self.block())
        result=transform(rgb,self.block(),allow_fixed_point_overshoot=True)
        self.assertTrue(all(0<=v<=1 for v in result))

    def test_hue_upper_boundary_is_exclusive(self):
        raw=self.block()
        groups=[decode(raw[8+84*i:92+84*i]) for i in range(6)]
        self.assertEqual(helper([.75,.5,.25],groups[0],groups[5],groups[1]),
                         [.5,.5,0.,0.])

    def test_saturation_closed_boundaries_and_outside_bypass(self):
        raw=self.block(sbounds=(25,75))
        groups=[decode(raw[8+84*i:92+84*i]) for i in range(6)]
        for rgb in ([.625,.375,.375],[.875,.125,.125]):
            result=helper(rgb,groups[0],groups[5],groups[1])
            self.assertNotEqual(result[2],0.)
        self.assertEqual(helper([.5625,.4375,.4375],groups[0],groups[5],groups[1]),
                         [0.,0.,0.,0.])

    def test_lightness_closed_boundaries(self):
        raw=self.block(lbounds=(25,75))
        groups=[decode(raw[8+84*i:92+84*i]) for i in range(6)]
        for rgb in ([.375,.125,.125],[.875,.625,.625]):
            result=helper(rgb,groups[0],groups[5],groups[1])
            self.assertNotEqual(result[3],0.)
        self.assertEqual(helper([.1875,.0625,.0625],groups[0],groups[5],groups[1]),
                         [0.,0.,0.,0.])
