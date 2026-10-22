import hashlib
import struct
import tempfile
from pathlib import Path
import unittest
from camera_install.dense_acceptance_research import compare_dense,compare_final_tables,final_color_regions


class DenseAcceptanceTests(unittest.TestCase):
    def test_complete_source_match_and_single_value_mismatch(self):
        words=(12,3,33)+(0,)*107811
        data=bytearray(107811*8)
        self.assertTrue(compare_dense(words,data.hex())['passed'])
        struct.pack_into('<d',data,123*8,.25)
        result=compare_dense(words,data.hex())
        self.assertFalse(result['passed'])
        self.assertEqual(result['maxError'],.25)

    def test_reject_partial_capture(self):
        with self.assertRaises(ValueError):
            compare_dense((12,3,33)+(0,)*107811,'00')

    def test_header_only_change_does_not_validate_color(self):
        with tempfile.TemporaryDirectory() as folder:
            def report(name,data):
                path=Path(folder)/name
                path.write_bytes(data)
                return dict(cameraAccess=False,compilerPatched=False,sourceSha256=name,
                    dllSha256='test-dll',descriptorSha256='test-descriptor',researchAgentSha256='test-agent',
                    rows=[dict(model='virtual',cameraId=1,seedByte=0,privatePayload=str(path),
                               payloadSha256=hashlib.sha256(data).hexdigest())])
            a=report('a',bytes(16752))
            data=bytearray(16752); data[44]=1
            b=report('b',data)
            keys=(bytes(512),bytes(513))
            result=compare_final_tables(a,b,keys)
            self.assertFalse(result['rows'][0]['colorTablesDiffer'])
            data[368]=1
            c=report('c',data)
            self.assertTrue(compare_final_tables(a,c,keys)['rows'][0]['colorTablesDiffer'])
            c['descriptorSha256']='different-descriptor'
            with self.assertRaises(ValueError): compare_final_tables(a,c,keys)

    def test_nonfinite_capture_cannot_pass_as_zero_error(self):
        data=bytearray(107811*8)
        struct.pack_into('<d',data,123*8,float('nan'))
        with self.assertRaises(ValueError):
            compare_dense((12,3,33)+(0,)*107811,data.hex())

    def test_all_observed_regions_exclude_header_and_cover_tail(self):
        for size in (8528,16720,16744,16752,78980,83076,431616):
            regions=final_color_regions(bytes(size))
            self.assertGreater(regions[0][0],0)
            self.assertEqual(regions[-1][0]+len(regions[-1][1]),size)
            for (offset,data),(following,_) in zip(regions,regions[1:]):
                self.assertEqual(offset+len(data),following)
        with self.assertRaises(ValueError): final_color_regions(bytes(8164))
