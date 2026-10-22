import struct
import unittest
from camera_install.pf3_field_experiments import mutations, nonlinear_mutations, matrix_mutations, policy_mutations, axis_parameter_mutations,old_selector_mutations


class FieldTests(unittest.TestCase):
    def test_third_curve_channels_change_exactly_one_endpoint(self):
        from camera_install.pf3_field_experiments import third_curve_channel_mutations
        words=([2,0,0,255,255]+[0]*20)*3
        records=[{'id':'0x1065','data':struct.pack('>75I',*words)}]
        for channel,(_,prop,data) in enumerate(third_curve_channel_mutations(records)):
            actual=struct.unpack('<75I',data)
            self.assertEqual([i for i,(a,b) in enumerate(zip(words,actual)) if a!=b],[channel*25+4])
            self.assertEqual(actual[channel*25+4],230);self.assertEqual(prop,0x40001065)
        self.assertEqual(records[0]['data'],struct.pack('>75I',*words))

    def test_sharpness_sweep_preserves_source_and_skips_baseline(self):
        from camera_install.pf3_field_experiments import sharpness_scalar_mutations
        records=[{'id':'0x1034','data':struct.pack('>I',4)}]
        rows=list(sharpness_scalar_mutations(records,0x1034))
        self.assertEqual([struct.unpack('<I',row[2])[0] for row in rows],[0,1,2,3,5,6,7])
        self.assertTrue(all(row[1]==0x40001034 for row in rows))
        self.assertEqual(records[0]['data'],struct.pack('>I',4))

    def test_sharpness_sweep_refuses_other_fields_and_bad_baseline(self):
        from camera_install.pf3_field_experiments import sharpness_scalar_mutations
        with self.assertRaises(ValueError):list(sharpness_scalar_mutations([],0x1030))
        with self.assertRaises(ValueError):list(sharpness_scalar_mutations([{'id':'0x1035','data':struct.pack('>I',8)}],0x1035))
        self.assertEqual(len(list(sharpness_scalar_mutations([{'id':'0x1035','data':bytes(4)}],0x1035))),7)

    def test_old_selector_candidates_have_complete_bounded_records(self):
        from camera_install.legacy_grid_reference import selective_groups
        records=[{'id':key,'data':struct.pack('>2I',1,0)} for key in ('0x1023','0x102b')]
        variants=list(old_selector_mutations(records))
        self.assertEqual(len(variants),4)
        for _,prop,data in variants:
            self.assertIn(prop,(0x40001023,0x4000102b))
            self.assertEqual(len(data),76)
            self.assertEqual(len(selective_groups({'kind':1,'count':1,'points':4,'initializedHex':data.hex()})),1)
        self.assertEqual(records[0]['data'],struct.pack('>2I',1,0))
    def test_axis_parameter_mutations_preserve_layout(self):
        words = [2,6]+[0]*126
        records = [{'id':key,'data':struct.pack('>128i',*words)} for key in ('0x1061','0x1062')]
        variants = list(axis_parameter_mutations(records))
        self.assertEqual(len(variants),6)
        for _,_,data in variants:
            actual = struct.unpack('<128i',data)
            changed = [i for i,(a,b) in enumerate(zip(words,actual)) if a != b]
            self.assertEqual(len(changed),1)
            self.assertIn(changed[0],(16,17,18))
            self.assertEqual(actual[changed[0]],10)
    def test_policy_scratch_changes_one_word_only(self):
        records = [{'id':key,'data':struct.pack('>2I',1,0)} for key in ('0x1023','0x102b')]
        variants = list(policy_mutations(records))
        self.assertEqual(len(variants),4)
        self.assertEqual([struct.unpack('<2I',data) for _,_,data in variants],[(2,0),(1,2),(2,0),(1,2)])
        self.assertTrue(all(r['data'] == struct.pack('>2I',1,0) for r in records))

    def test_matrix_double_preserves_other_coefficients(self):
        words = [65536] + list(range(1,60))
        records = [{'id':key,'data':struct.pack('>60i',*words)} for key in ('0x1021','0x1029')]
        for name,_,data in matrix_mutations(records,True):
            self.assertTrue(name.endswith('_FIRST_DOUBLE'))
            self.assertEqual(struct.unpack('<60i',data),(131072,*words[1:]))
    def records(self):
        return [{"id": "0x1008", "data": struct.pack(">HHI", 0x10, 4, 440) + bytes(440)
                 + struct.pack(">HHI", 0xffff, 0xffff, 0)}] + [
                 {"id": key, "data": struct.pack(">75I", 2, 0, 0, 255, 255, *([0] * 70))}
                 for key in ("0x1019", "0x1018", "0x1065")]

    def test_changes_are_single_field_and_endianness_correct(self):
        records = self.records()
        results = list(mutations(records))
        self.assertEqual(len(results), 4)
        self.assertEqual(struct.unpack_from(">i", results[0][2], 28)[0], 655360)
        for _, _, payload in results[1:]:
            self.assertEqual(struct.unpack_from("<5I", payload), (2, 0, 0, 255, 230))
        self.assertEqual(struct.unpack_from(">5I", records[1]["data"]), (2, 0, 0, 255, 255))

    def test_unexpected_curve_refused(self):
        records = self.records()
        records[1]["data"] = bytes(300)
        with self.assertRaises(ValueError):
            list(mutations(records))

    def test_nonlinear_candidates_bounded_and_preserve_size(self):
        cases = list(nonlinear_mutations(self.records()))
        self.assertEqual(len(cases), 5)
        self.assertTrue(all(len(data) == 300 for _, _, data in cases))
        self.assertEqual(struct.unpack_from("<7I", cases[0][2]), (3, 0, 0, 128, 96, 255, 255))

    def test_matrix_mutation_changes_only_first_coefficient(self):
        words = [65536] + list(range(1,60))
        records = [{'id': key, 'data': struct.pack('>60i', *words)} for key in ('0x1021','0x1029')]
        variants = list(matrix_mutations(records))
        self.assertEqual(len(variants), 2)
        for _, _, data in variants:
            values = struct.unpack('<60i', data)
            self.assertEqual(values[0], 32768)
            self.assertEqual(list(values[1:]), words[1:])
        self.assertEqual(struct.unpack('>60i', records[0]['data'])[0], 65536)
