import struct
import unittest
from camera_install.grid_source_validation import validate


class GridSourceTests(unittest.TestCase):
    def test_known_permutation_and_scale(self):
        table = struct.pack('>6H', 12, 3, 33, 100, 200, 300)
        item = {'functionRva': '0x196a0', 'sourceGrid': {'candidateLayouts': [
            {'offset': 20, 'samples': [{'index': 0, 'rgb': [100/4095, 300/4095, 200/4095]}]}]}}
        result = validate({'files': [{'model': 'fixture', 'mlibCalls': {'captures': [item]}}]},
                          {'0x1070': table})
        self.assertTrue(result['checks'][0]['passed'])
        self.assertEqual(result['checks'][0]['diskChannelOrder'], (0, 2, 1))

    def test_rejects_wrong_header(self):
        item = {'functionRva': '0x196a0', 'sourceGrid': {'candidateLayouts': []}}
        with self.assertRaises(ValueError):
            validate({'files': [{'model': 'fixture', 'mlibCalls': {'captures': [item]}}]},
                     {'0x1070': struct.pack('>3H', 8, 3, 33)})

    def test_complete_table(self):
        words = [index % 4096 for index in range(107811)]
        table = struct.pack('>3H', 12, 3, 33) + struct.pack('>107811H', *words)
        item = {'functionRva': '0x196a0', 'sourceGrid': {'candidateLayouts': []},
                'sourceDenseFloat64Hex': struct.pack('<107811d', *[word/4095 for word in words]).hex()}
        result = validate({'files': [{'model': 'fixture', 'mlibCalls': {'captures': [item]}}]},
                          {'0x1070': table})
        self.assertTrue(result['checks'][0]['passed'])
        self.assertEqual(result['checks'][0]['valueCount'], 107811)

    def test_rejects_truncated_complete_table(self):
        item = {'functionRva': '0x196a0', 'sourceGrid': {'candidateLayouts': []},
                'sourceDenseFloat64Hex': '00'}
        with self.assertRaises(ValueError):
            validate({'files': [{'model': 'fixture', 'mlibCalls': {'captures': [item]}}]},
                     {'0x1070': struct.pack('>3H', 12, 3, 33)})
