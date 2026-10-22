import struct
import unittest
from camera_install.compact_pixel_reference import prepare,point


def arguments():
    curve=(struct.pack('<25i',2,0,0,255,255,*([0]*20))*3).hex()
    matrix=[0]*60
    for c in range(3):matrix[c*20+c]=65536
    return dict(mode=1,splitCount=0,selectorBlock=None,axisBlock=None,
                preCurvesHex=curve,postCurvesHex=curve,thirdCurvesHex=None,
                matrix240Hex=struct.pack('<60i',*matrix).hex())


class CompactPixelTests(unittest.TestCase):
    def test_empty_axes_preserve_mode1_round_trips_but_do_not_apply_six_axes(self):
        from unittest.mock import patch
        from camera_install.lab_math_reference import rgb_to_lab,lab_to_rgb
        import math
        a=arguments()
        a['axisBlock']=dict(kind=2,count=0,points=5,
            initializedHex=(struct.pack('<2I',2,0)+bytes(504)).hex())
        rgb=[.123456789,.345678912,.789123456]
        expected=rgb
        for _ in range(2):
            expected=[v/2**24 for v in lab_to_rgb(rgb_to_lab([math.trunc(v*2**24) for v in expected],24,2),24,2)]
        with patch('camera_install.compact_pixel_reference.axes') as apply_axes:
            self.assertEqual(point(rgb,prepare(a)),expected)
            apply_axes.assert_not_called()
        a['mode']=2
        self.assertEqual(point(rgb,prepare(a)),rgb)
        for bad in (bytes(8),struct.pack('<2I',2,0)+bytes(503)+b'\x01'):
            a['axisBlock']['initializedHex']=bad.hex()
            with self.assertRaises(ValueError):prepare(a)

    def test_axis_division_precedes_weight_multiplication_at_integer_boundary(self):
        from camera_install.default_axis_reference import transform
        rgb=[.9999998807907104,.37499988079071045,.12499994039535522]
        result=transform(rgb,[(0,10,0)]+[(0,0,0)]*5,allow_fixed_point_overshoot=True)
        self.assertEqual(result,(1.,.3564827420033184,.09907590017523393))

    def test_null_optional_stages_preserve_identity(self):
        self.assertEqual(point([.125,.25,.5],prepare(arguments())),[.125,.25,.5])

    def test_fixed_coefficients_are_not_six_decimal_truncated(self):
        a=arguments();matrix=list(struct.unpack('<60i',bytes.fromhex(a['matrix240Hex'])))
        matrix[0]=65535;a['matrix240Hex']=struct.pack('<60i',*matrix).hex()
        self.assertEqual(prepare(a)[0][0],65535/65536)
        self.assertEqual(point([.5,0,0],prepare(a))[0],.5*65535/65536)

    def test_selector_split_requires_valid_group_count(self):
        a=arguments();a['splitCount']=1
        with self.assertRaises(ValueError):prepare(a)

    def test_wider_selector_domain_requires_explicit_bounded_opt_in(self):
        a=arguments();self.assertEqual(prepare(a)[-1],.05)
        a['researchSelectorMargin']=.25;self.assertEqual(prepare(a)[-1],.25)
        for value in (.251,-.01,float('nan'),float('inf')):
            a['researchSelectorMargin']=value
            with self.assertRaises(ValueError):prepare(a)
        a['splitCount']=0;a['mode']=3
        with self.assertRaises(ValueError):prepare(a)

    def test_luminance_uses_native_ten_matrix(self):
        a=arguments();a['thirdCurvesHex']=a['preCurvesHex']
        actual=point([0,0,.125],prepare(a))
        from camera_install.color_math_reference import forward_color,inverse_color
        from camera_install.float_lab_reference import forward,inverse
        lab=forward(forward_color([0,0,.125],10),12)
        lab[0]=((lab[0]/100*255)/255)*100
        expected=inverse_color(inverse(lab,12),10)[0]
        for x,y in zip(actual,expected):self.assertAlmostEqual(x,y,places=14)


if __name__=='__main__':unittest.main()
