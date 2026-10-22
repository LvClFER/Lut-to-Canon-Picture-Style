import unittest
from camera_install.compact_pixel_research import vectors,preflight
from unittest.mock import patch
from tests.test_compact_pixel_reference import arguments


class CompactPixelResearchTests(unittest.TestCase):
    def test_unsupported_input_is_not_forwarded_to_native_probe(self):
        case=dict(name='bounded',arguments=arguments(),inputs=[[0,0,0],[.5,.5,.5]])
        with patch('camera_install.compact_pixel_research.point',side_effect=[ValueError('unsafe cached index'),[.5,.5,.5]]):
            safe,references,unsupported=preflight([case])
        self.assertEqual(safe[0]['inputs'],[[.5,.5,.5]])
        self.assertEqual(case['inputs'],[[0,0,0],[.5,.5,.5]])
        self.assertNotIn(('bounded',(0,0,0)),references)
        self.assertTrue(unsupported[0]['nativeCallSkipped'])
        self.assertEqual(unsupported[0]['reason'],'unsafe cached index')

    def test_replay_cases_are_bounded_and_duplicates_removed(self):
        a=arguments();a['thirdCurvesHex']=a['preCurvesHex']
        capture=dict(functionRva='0x1cab0',initializedArguments=a,
                     samples=[dict(input=[0,.5,1])])
        cases=vectors([capture,capture])
        self.assertEqual(len(cases),38)
        self.assertEqual(len({c['name'] for c in cases}),38)
        self.assertTrue(all(len(c['inputs'])<=192 for c in cases))
        self.assertEqual(next(c for c in cases if c['name']=='groups2_split1_mode1')['arguments']['splitCount'],1)
        maximum=next(c for c in cases if c['name']=='groups12_split6_mode1')['arguments']
        self.assertEqual(maximum['selectorBlock']['bytes'],824)
        self.assertEqual(maximum['splitCount'],6)

    def test_empty_capture_list_is_not_success(self):
        with self.assertRaises(ValueError):vectors([])


if __name__=='__main__':unittest.main()
