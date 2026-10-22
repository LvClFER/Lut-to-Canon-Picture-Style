import unittest
import struct
import hashlib
from unittest.mock import patch
from camera_install.basic_control_research import changed_ranges, packed_outputs, verify_editor_exports
from camera_install.pf3_field_experiments import contrast_mutations, basic_scalar_mutations, auxiliary_flag_mutations, StockCompilerError


class BasicControlResearchTests(unittest.TestCase):
    def test_failed_compiler_preserves_observations_without_giant_error_text(self):
        report={'rcGet':80,'mlibCalls':{'captures':[{'privateBuffer':'x'*10000}]}}
        error=StockCompilerError(report)
        self.assertIs(error.native_report,report)
        self.assertIn('80',str(error))
        self.assertLess(len(str(error)),250)

    def test_auxiliary_flags_are_bounded_and_keep_correct_endian_width(self):
        records=[{'id':f'0x{identifier:04x}','data':value.to_bytes(width,'big')}
                 for identifier,width,value in ((0x100c,2,1),(0x1011,4,0),(0x1012,4,0),(0x1080,4,0))]
        rows=list(auxiliary_flag_mutations(records))
        self.assertEqual(rows[0][2], bytes(2))
        self.assertTrue(all(data == b'\x01\x00\x00\x00' for _,_,data in rows[1:]))
        records[1]['data']=b'\x00\x00\x00\x02'
        with self.assertRaises(ValueError):list(auxiliary_flag_mutations(records))

    def test_explicit_scalar_sweep_does_not_assume_names(self):
        rows = list(basic_scalar_mutations([{'id':'0x1031','data':bytes(4)}],0x1031))
        self.assertTrue(all(prop == 0x40001031 for _,prop,_ in rows))
        self.assertEqual(rows[0][0], 'SCALAR_1031_MINUS4')
        with self.assertRaises(ValueError):
            list(basic_scalar_mutations([],0x115))

    def test_editor_native_verification_rejects_swapped_controls_and_color_changes(self):
        source = b'fixture'
        row = {'cameraId':1042,'source':'BASE_NEUTRAL_RP_EDITOR_EXPORT.pf3',
               'sourceSha256':hashlib.sha256(source).hexdigest(),'rcGet':0}
        baseline = {'cameraId':1042,'source':'BASE_NEUTRAL_RP.pf3'}
        before = bytes(16752)
        after = bytearray(before)
        struct.pack_into('<8i',after,76,-2,5,2,-1,0,0,2,3)
        with patch('pathlib.Path.read_bytes',return_value=source):
            for expected, candidate in ((1,after),(0,bytes(before))):
                with patch('camera_install.basic_control_research.read_payload',side_effect=[before,candidate]):
                    result=verify_editor_exports({'files':[row]},{'files':[baseline]})
                    self.assertEqual(result['passed'],expected)
            after[368]=1
            with patch('camera_install.basic_control_research.read_payload',side_effect=[before,after]):
                self.assertEqual(verify_editor_exports({'files':[row]},{'files':[baseline]})['passed'],0)

    def test_contrast_sweep_is_bounded_and_preserves_signed_values(self):
        rows = list(contrast_mutations([{'id':'0x1030','data':bytes(4)}]))
        self.assertEqual([struct.unpack('<i',data)[0] for _,_,data in rows], [-4,-3,-2,-1,1,2,3,4])
        self.assertTrue(all(prop == 0x40001030 for _,prop,_ in rows))
        with self.assertRaises(ValueError):
            list(contrast_mutations([{'id':'0x1030','data':b'\x01\x00\x00\x00'}]))

    def test_ranges_do_not_hide_unchanged_bytes(self):
        self.assertEqual(changed_ranges(b'abcdef', b'AbCdEF'), [[0,1],[2,3],[4,6]])
        self.assertEqual(changed_ranges(b'abc', b'abc'), [])
        with self.assertRaises(ValueError):
            changed_ranges(b'a', b'ab')

    def test_missing_packer_is_not_an_equality_proof(self):
        self.assertEqual(packed_outputs({}), [])
        first = {'mlibCalls': {'captures': [{'functionRva': '0x49e00', 'nativePackedHex': '0102'}]}}
        second = {'mlibCalls': {'captures': [{'functionRva': '0x49e00', 'nativePackedHex': '0103'}]}}
        self.assertNotEqual(packed_outputs(first), packed_outputs(second))


if __name__ == '__main__':
    unittest.main()
