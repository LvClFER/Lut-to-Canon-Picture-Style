import struct
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from camera_install.modern_grid_reference import prepare, point,curve_settings,packing_passed,selector_settings,apply_selectors
from camera_install.lab_math_reference import rgb_to_lab,lab_to_rgb


class ModernGridTests(unittest.TestCase):
    def test_unused_third_channels_require_explicit_research_opt_in(self):
        identity=struct.pack('<25I',2,0,0,255,255,*([0]*20))
        changed=struct.pack('<25I',2,0,0,255,230,*([0]*20))
        arguments={'preCurvesHex':(identity*3).hex(),'postCurvesHex':(identity*3).hex(),
                   'thirdCurvesHex':(identity+changed+identity).hex()}
        with self.assertRaises(ValueError):curve_settings(arguments)
        result=curve_settings(arguments,True)
        self.assertNotEqual(result['thirdCurvesHex'][0],result['thirdCurvesHex'][1])

    def test_named_field_case_does_not_claim_or_remove_other_cases(self):
        from camera_install.modern_grid_reference import named_field_cases
        rows=[{'name':'a'},{'name':'b'}]
        self.assertEqual(named_field_cases(rows,'b'),[rows[1]])
        self.assertEqual(len(rows),2)
        with self.assertRaises(ValueError):named_field_cases(rows,'missing')
        with self.assertRaises(ValueError):named_field_cases(rows+[rows[0]],'a')

    def test_bounded_selector_captures_are_required(self):
        empty={'kind':1,'count':0,'initializedHex':struct.pack('<2i',1,0).hex()}
        self.assertEqual(selector_settings({'oldParameterBlock':None,'additionalParameterBlock':empty}),([],[]))
        with self.assertRaises(ValueError):selector_settings({'oldParameterBlock':None})
        with self.assertRaises(ValueError):selector_settings({'oldParameterBlock':None,'additionalParameterBlock':dict(empty,count=1)})

    def test_selector_alias_order_and_nodes_are_preserved(self):
        with patch('camera_install.modern_grid_reference.selective',side_effect=lambda rgb,*args,**kwargs:[rgb[0]+.01,*rgb[1:]]) as call:
            actual=apply_selectors([.2,.3,.4],[object(),object()],17)
            self.assertAlmostEqual(actual[0],.22)
            self.assertEqual(call.call_args_list[1].args[0],(.21000000000000002,.3,.4))
            self.assertEqual(call.call_args.kwargs['nodes'],17)

    def test_nonempty_selectors_remain_explicitly_experimental(self):
        identity=(struct.pack('<25i',2,0,0,255,255,*([0]*20))*3).hex()
        words=[2,6]
        for i in range(6):
            centre=i*60
            words.extend([5,0,centre,50,50,1,(centre-30)%360,0,0,2,(centre+30)%360,100,100,3,0,0,0,5,20,0,0])
        matrix=[0]*60
        for c in range(3):matrix[c*20+c]=65536
        raw=struct.pack('<19i',1,1,4,0,180,50,50,1,0,0,0,2,360,100,100,3,5,0,0)
        args={'preCurvesHex':identity,'postCurvesHex':identity,'thirdCurvesHex':identity,
              'oldParameters512Hex':None,'sixAxes512Hex':struct.pack('<128i',*words).hex(),
              'matrix240Hex':struct.pack('<60i',*matrix).hex(),'numericArguments':[1,1],
              'oldParameterBlock':None,'additionalParameterBlock':{'kind':1,'count':1,'points':4,'initializedHex':raw.hex()},
              'additionalParametersHeader8Hex':raw[:8].hex(),'additionalEmptyParametersHex':None}
        with self.assertRaises(ValueError):prepare(args)
        coefficients,mode=prepare(args,True)
        self.assertEqual(mode,1)
        self.assertEqual(coefficients,self.identity_coefficients())

    def test_unsupported_domain_is_reported_and_not_counted_as_pass(self):
        from camera_install.modern_grid_reference import main
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.json';output=Path(folder)/'check.json'
            source.write_text(json.dumps({'files':[{'source':'unsafe-vector','mlibCalls':{'captures':[{
                'functionRva':'0x11220','initializedArguments':{},'gridArguments':[{
                'nodes':17,'initializedOutputFloat64Hex':bytes(17**3*24).hex()}]}]}}]}),encoding='utf-8')
            with patch('sys.argv',['reference','--trace',str(source),'--output',str(output)]), \
                 patch('camera_install.modern_grid_reference.prepare',return_value=([0.]*57,2)), \
                 patch('camera_install.modern_grid_reference.axis_settings',return_value=([],[])), \
                 patch('camera_install.modern_grid_reference.curve_settings',return_value={}), \
                 patch('camera_install.modern_grid_reference.point',side_effect=ValueError('unverified negative index')), \
                 patch('builtins.print'):
                with self.assertRaises(SystemExit) as error:main()
            self.assertEqual(error.exception.code,1)
            report=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['checks'],[])
            self.assertEqual(report['unsupported'][0]['coordinates'],[0,0,0])
            self.assertEqual(report['unsupported'][0]['reason'],'unverified negative index')

    def identity_coefficients(self):
        # Polynomial basis starts R,G,B; each output selects its own input.
        result=[0.]*57
        for channel in range(3): result[channel*19+channel]=1.
        return result

    def test_native_full33_green_boundary(self):
        lab=rgb_to_lab([0,16777216,0],24,1)
        self.assertEqual(lab,[5749934,-5648445,5451687])
        self.assertEqual(lab_to_rgb(lab,24,2),[9565362,16777558,3762079])
        self.assertEqual(point([0,1,0],self.identity_coefficients(),1,True),[6.,32767.,3.])

    def test_neutral_black(self):
        for mode in (1,2):
            self.assertEqual(point([0,0,0],self.identity_coefficients(),mode,True),[0.,0.,0.])

    def test_reject_unverified_curves(self):
        identity=struct.pack('<75i',*(([2,0,0,255,255]+[0]*20)*3)).hex()
        bad={'preCurvesHex':(struct.pack('<I',13)+bytes(296)).hex(),'postCurvesHex':identity,'thirdCurvesHex':identity}
        with self.assertRaises(ValueError): prepare(bad)

    def test_nonlinear_curve_cache(self):
        identity=struct.pack('<75i',*(([2,0,0,255,255]+[0]*20)*3)).hex()
        nonlinear=struct.pack('<75i',*(([3,0,0,128,160,255,255]+[0]*18)*3)).hex()
        curves=curve_settings({'preCurvesHex':nonlinear,'postCurvesHex':identity,'thirdCurvesHex':identity})
        samples=curves['preCurvesHex'][0]
        self.assertEqual(len(samples),256)
        self.assertAlmostEqual(samples[128],160/255,places=14)
        self.assertTrue(all(a<=b for a,b in zip(samples,samples[1:])))

    def test_unmapped_chromatic_curve_rejected(self):
        identity=struct.pack('<25i',*([2,0,0,255,255]+[0]*20))
        changed=struct.pack('<25i',*([2,0,0,255,230]+[0]*20))
        raw=(identity*3).hex()
        with self.assertRaises(ValueError):
            curve_settings({'preCurvesHex':raw,'postCurvesHex':raw,'thirdCurvesHex':(identity+changed+identity).hex()})

    def test_empty_curve_native_fallback(self):
        identity=(struct.pack('<25i',*([2,0,0,255,255]+[0]*20))*3).hex()
        curves=curve_settings({'preCurvesHex':bytes(300).hex(),'postCurvesHex':identity,'thirdCurvesHex':identity})
        self.assertEqual(curves['preCurvesHex'],[[i/300 for i in range(301)]]*3)

    def test_native_profile_selects_one_packing_candidate(self):
        candidates=[{'independentEqualsNativeGrid':True,'nativePayloadBlocks':[]},
                    {'independentEqualsNativeGrid':True,'nativePayloadBlocks':[2]}]
        self.assertTrue(packing_passed(candidates,True))
        candidates[1]['nativePayloadBlocks']=[]
        self.assertFalse(packing_passed(candidates,True))
        self.assertTrue(packing_passed(candidates,False))
        candidates[0]['independentEqualsNativeGrid']=False
        self.assertFalse(packing_passed(candidates,False))
        self.assertFalse(packing_passed([],False))
