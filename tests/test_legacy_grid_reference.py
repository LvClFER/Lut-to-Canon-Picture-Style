import unittest
from camera_install.legacy_grid_reference import point,compact_point,flagged_point
from camera_install.mlib_grid_research import legacy_curve_vectors,legacy_matrix_vectors,legacy_gamut_policy_vectors,legacy_multiple_group_vectors,legacy_grid_flag_vectors
from camera_install.legacy_grid_reference import selective_groups
from camera_install.modern_grid_reference import curve_settings
import struct
from unittest.mock import patch


class LegacyGridTests(unittest.TestCase):
    def identity(self):
        coeff=[0.]*57
        for c in range(3): coeff[c*19+c]=1.
        curves={k:[[i/300 for i in range(301)]]*3 for k in ('preCurvesHex','postCurvesHex','thirdCurvesHex')}
        curves['applyLuminance']=False
        return coeff,1,curves,[]

    def test_compact_boundary_extrapolation(self):
        for b in range(10):
            result=compact_point((0,0,b),*self.identity())
            for a,v in zip(result,[0,0,min(b,8)*32]): self.assertAlmostEqual(a,v,places=12)

    def test_preceding_null_luminance_bypass(self):
        self.assertEqual(point([0,0,.0625],*self.identity()),[0.,0.,16.])

    def test_flagged_endpoints_and_integer_rounding(self):
        cases=((10,0,256.),(10,1,256.),(10,2,255.),
               (17,0,240.),(17,1,240.51612903225808),(17,2,255.75))
        for nodes,flag,expected in cases:
            actual=flagged_point((0,0,nodes-1),*self.identity(),nodes,flag)
            self.assertAlmostEqual(actual[2],expected,places=12)
        coeff,mode,curves,groups=self.identity()
        coeff[0]=.999984
        self.assertEqual(flagged_point((1,0,0),coeff,mode,curves,groups,10,0)[0],31.)

    def test_flag2_compact_retains_valid_axis_overshoot(self):
        with patch('camera_install.legacy_grid_reference.point',return_value=[1.01,0.,0.]):
            self.assertEqual(flagged_point((9,0,0),*self.identity(),10,2),[257.55,0.,0.])

    def test_flagged_geometry_rejects_unverified_inputs(self):
        for nodes,flag,indices in ((8,1,(0,0,0)),(17,3,(0,0,0)),(10,1,(10,0,0))):
            with self.assertRaises(ValueError):flagged_point(indices,*self.identity(),nodes,flag)

    def test_nine_node_boundary_constants(self):
        for flag,expected in ((0,282.),(1,280.),(2,255.)):
            self.assertAlmostEqual(flagged_point((8,0,0),*self.identity(),9,flag)[0],expected,places=12)

    def test_cubic_one_ulp_difference_survives_integer_truncation(self):
        coefficients,mode,curves,groups=self.identity()
        coefficients[18]=.03125
        curves['applyAxis']=True
        self.assertEqual(flagged_point((1,2,5),coefficients,mode,curves,groups,10,0),[33.,63.,160.])

    def test_flag_vectors_keep_original_capture_and_geometry_provenance(self):
        raw=[0]*60
        for c in range(3):raw[c*20+c]=65536
        base={'nodes':17,'headerHex':struct.pack('<4I',3,17,17,2).hex(),'expectedHex':'stock',
              'arguments':{'matrix240Hex':struct.pack('<60i',*raw).hex(),'numericArguments':[1,1]}}
        cases=legacy_grid_flag_vectors([base],True,True)
        self.assertEqual(len(cases),31)
        self.assertIs(cases[0],base)
        self.assertEqual(base['nodes'],17)
        for case in cases[1:]:
            self.assertEqual(case['nodes'],9)
            self.assertEqual(struct.unpack('<4I',bytes.fromhex(case['headerHex']))[1],9)
            self.assertIsNone(case['expectedHex'])

    def test_modern_endpoint_scale(self):
        self.assertEqual(point([0,0,.9990234375],*self.identity()),[0.,0.,255.75])

    def test_synthetic_vectors_preserve_baseline_and_mark_scope(self):
        base={'arguments':{'preCurvesHex':None,'postCurvesHex':None,
                          'thirdCurvesHex':None,'numericArguments':[1,1]},
              'nodes':17,'expectedHex':'baseline'}
        cases=legacy_curve_vectors([base])
        self.assertEqual(len(cases),13)
        self.assertIs(cases[0],base)
        self.assertIsNone(base['arguments']['preCurvesHex'])
        for case in cases[1:]:
            self.assertIsNone(case['expectedHex'])
            args={k:(v or bytes(300).hex()) for k,v in case['arguments'].items()
                  if k.endswith('CurvesHex')}
            settings=curve_settings(args)
            stage=next(k for k,v in case['arguments'].items() if k.endswith('CurvesHex') and v)
            self.assertNotEqual(settings[stage][0],[i/(len(settings[stage][0])-1)
                                                     for i in range(len(settings[stage][0]))])

    def test_matrix_vectors_preserve_reserved_words(self):
        raw=[0]*60
        for c in range(3): raw[c*20+c]=65536;raw[c*20+19]=12345
        base={'arguments':{'matrix240Hex':struct.pack('<60i',*raw).hex(),
                           'numericArguments':[1,1]},'nodes':10,'expectedHex':'stock'}
        cases=legacy_matrix_vectors([base])
        self.assertEqual(len(cases),7)
        for case in cases[1:]:
            words=struct.unpack('<60i',bytes.fromhex(case['arguments']['matrix240Hex']))
            self.assertEqual(words[19::20],(12345,)*3)
            self.assertIsNone(case['expectedHex'])

    def test_luminance_clamps_profile_intermediate_only_when_present(self):
        coefficients,mode,curves,_=self.identity()
        curves['applyAxis']=False
        with patch('camera_install.legacy_grid_reference.selective',return_value=(-.01,1.01,.5)):
            raw=point([.2,.3,.4],coefficients,mode,curves,[object()],1,None)
            self.assertEqual(raw,[-.010000000000000009,1.01,.5])
            curves['applyLuminance']=True
            with patch('camera_install.legacy_grid_reference.forward_color',return_value=[0,0,0]) as convert:
                point([.2,.3,.4],coefficients,mode,curves,[object()],1,None)
                self.assertEqual(convert.call_args.args,([0,1,.5],mode))

    def test_six_axis_dispatch_preserves_widths(self):
        coefficients,mode,curves,groups=self.identity()
        curves.update(axisKind='six',axisValues=[(10,0,0)]*6,
                      axisWidths=[0,5,10,20,30,60])
        with patch('camera_install.legacy_grid_reference.six_axes',return_value=[.1,.2,.3]) as transform:
            self.assertEqual(point([.2,.3,.4],coefficients,mode,curves,groups),[25.6,51.2,76.8])
            self.assertEqual(transform.call_args.args[1:],(curves['axisValues'],curves['axisWidths']))

    def test_pre_axis_selectors_run_before_post_curve(self):
        coefficients,mode,curves,groups=self.identity()
        curves['preGroups']=[object()];curves['applyAxis']=False
        curves['postCurvesHex']=[[i/600 for i in range(301)]]*3
        with patch('camera_install.legacy_grid_reference.selective',return_value=[.2,.4,.6]):
            for a,b in zip(point([.1,.1,.1],coefficients,mode,curves,groups),[25.6,51.2,76.8]):
                self.assertAlmostEqual(a,b,places=12)

    def test_gamut_vectors_do_not_mutate_captured_policy(self):
        raw=[0]*60
        for c in range(3):raw[c*20+c]=65536
        base={'nodes':17,'expectedHex':'stock','arguments':{'numericArguments':[1,1],
              'matrix240Hex':struct.pack('<60i',*raw).hex()}}
        for policy in (0,2):
            cases=legacy_gamut_policy_vectors([base],policy)
            self.assertEqual(len(cases),8)
            self.assertIs(cases[0],base)
            for case in cases[1:]:
                self.assertEqual(case['arguments']['numericArguments'],[1,policy])
                self.assertIsNone(case['expectedHex'])
        self.assertEqual(base['arguments']['numericArguments'],[1,1])

    def test_multiple_group_layout_and_order(self):
        base={'nodes':17,'expectedHex':'stock','arguments':{'numericArguments':[1,1]}}
        cases=legacy_multiple_group_vectors([base])
        self.assertEqual(len(cases),7)
        for case in cases[1:]:
            block=case['arguments']['additionalParameterBlock']
            self.assertEqual(len(selective_groups(block)),block['count'])
        first=cases[1]['arguments']['additionalParameterBlock']['initializedHex']
        reverse=cases[2]['arguments']['additionalParameterBlock']['initializedHex']
        self.assertNotEqual(first,reverse)
        self.assertNotIn('additionalParameterBlock',base['arguments'])
