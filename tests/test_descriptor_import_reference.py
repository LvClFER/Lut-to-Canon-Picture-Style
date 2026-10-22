import unittest
import copy
import hashlib
import struct
from camera_install.descriptor_import_reference import (
    normalize_modern, normalize_compact, importer_kind, normalize_observed_raw,
    verify_import_report, modern_parameter_matrix, match_modern_matrix_calls,
    modern_axis_parameters, modern_four_point_parameters, match_modern_descriptor_calls,
    validated_style_ordinal, parameterless_matrix_reference, modern_grid_arguments)
from camera_install.compiler_regression import decode


class DescriptorImportReferenceTests(unittest.TestCase):
    def test_grid_arguments_are_descriptor_derived(self):
        data = bytearray(14796)
        struct.pack_into('<HH', data, 0x2d0 + 3 * 0x9a0 + 0x104, 1, 0)
        struct.pack_into('<HH', data, 0x3f8 + 3 * 0x9a0 + 0x1e4, 2, 0)
        arguments = modern_grid_arguments(data, 0x84, 1)
        self.assertEqual(arguments['matrix240Hex'], modern_parameter_matrix(data, 3, 1).hex())
        self.assertEqual(arguments['numericArguments'], [1, 1])
        self.assertIsNone(arguments['oldParameterBlock'])
        self.assertEqual(arguments['additionalParameterBlock']['initializedHex'], struct.pack('<2I', 1, 0).hex())
        self.assertEqual(arguments['axisParameterBlock']['bytes'], 8)

    def test_grid_arguments_reject_unobserved_selectors(self):
        for style, index, mode, policy in ((0x86, 1, 1, 1), (0x84, 3, 1, 1),
                                           (0x84, 1, 3, 1), (0x84, 1, 1, 3),
                                           (0x84, 1, True, 1)):
            with self.assertRaises(ValueError):
                modern_grid_arguments(bytes(14796), style, index, mode, policy)

    def test_parameterless_matrix_is_fixed_not_exact_unity(self):
        words=struct.unpack('<60I',parameterless_matrix_reference())
        self.assertEqual([i for i,w in enumerate(words) if w], [0,21,42])
        self.assertEqual({w for w in words if w},{65535})
    def test_six_observed_style_ordinals_no_unknown_fallback(self):
        self.assertEqual([validated_style_ordinal(s) for s in (0x81,0x82,0x83,0x84,0x85,0x88)],list(range(6)))
        for value in (0,0x86,0x87,0x89,True):
            with self.assertRaises(ValueError):
                validated_style_ordinal(value)
    def test_combined_consumer_distinguishes_four_point_indices(self):
        data = bytearray(14796)
        for index in (1,2):
            struct.pack_into('<HH',data,0x2d0+3*0x9a0+index*0x104,1,index)
            struct.pack_into('<HH',data,0x3f8+3*0x9a0+index*0x1e4,2,0)
        args=dict(matrix240Hex=modern_parameter_matrix(data,3,2).hex(),
                  numericArguments=[2,1],oldParameterBlock=None,
                  axisParameterBlock=dict(initializedHex=modern_axis_parameters(data,3,2).hex()),
                  additionalParameterBlock=dict(initializedHex=modern_four_point_parameters(data,3,2).hex()))
        capture=dict(functionRva='0x14bd0',result=1,initializedArguments=args)
        self.assertEqual(match_modern_descriptor_calls(data,3,[capture])[0]['possibleDescriptorIndices'],[2])
        for field,value in (('additionalParameterBlock',None),('oldParameterBlock',{}),('numericArguments',[])):
            changed=copy.deepcopy(capture)
            changed['initializedArguments'][field]=value
            with self.assertRaises(ValueError):
                match_modern_descriptor_calls(data,3,[changed])
    def test_four_point_expansion_signedness_and_index_count(self):
        data = bytearray(14796)
        for index, count in ((1,5),(2,6)):
            offset = 0x2d0 + 3 * 0x9a0 + index * 0x104
            struct.pack_into('<HH',data,offset,1,count)
            for group in range(count):
                for point in range(4):
                    struct.pack_into('<Hhhh',data,offset+4+group*32+point*8,
                                     point,-32768,-1,32767)
            expanded=modern_four_point_parameters(data,3,index)
            self.assertEqual(len(expanded),8+count*68)
            self.assertEqual(struct.unpack_from('<7I',expanded),(1,count,4,0,0xffff8000,0xffffffff,32767))
        struct.pack_into('<H',data,0x2d2+3*0x9a0+0x104,9)
        with self.assertRaises(ValueError):
            modern_four_point_parameters(data,3,1)
    def test_axis_expansion_signed_values_and_count(self):
        data = bytearray(14796)
        offset = 0x3f8 + 3 * 0x9a0 + 0x1e4
        struct.pack_into('<HH',data,offset,2,1)
        for point in range(5):
            struct.pack_into('<Hhhh',data,offset+4+point*8,60000,-32768,-1,32767)
        expanded = modern_axis_parameters(data,3,1)
        words = struct.unpack('<23I',expanded)
        self.assertEqual(words[:3],(2,1,5))
        self.assertEqual(words[3:7],(60000,0xffff8000,0xffffffff,32767))
        self.assertEqual(len(expanded),92)
        struct.pack_into('<H',data,offset+2,13)
        with self.assertRaises(ValueError):
            modern_axis_parameters(data,3,1)

    def test_consumer_matrix_match_preserves_ambiguity(self):
        data = bytes(14796)
        capture = dict(functionRva='0x14bd0',result=1,
                       initializedArguments=dict(matrix240Hex=bytes(240).hex(),numericArguments=[2,1]))
        result = match_modern_matrix_calls(data,3,[capture])
        self.assertEqual(result[0]['possibleDescriptorIndices'],[1,2])
        changed = copy.deepcopy(capture)
        changed['initializedArguments']['matrix240Hex'] = (b'\x01' + bytes(239)).hex()
        with self.assertRaises(ValueError):
            match_modern_matrix_calls(data,3,[changed])
        with self.assertRaises(ValueError):
            match_modern_matrix_calls(data,3,[])
    def test_static_matrix_selection_and_bounds(self):
        data = bytes(i % 251 for i in range(14796))
        for ordinal in range(6):
            for index in (1, 2):
                start = 0x104 + ordinal * 0x9a0 + index * 0xf0
                self.assertEqual(modern_parameter_matrix(data, ordinal, index), data[start:start + 240])
        for ordinal, index in ((6, 1), (-1, 1), (3, 0), (3, 3), (True, 1)):
            with self.assertRaises(ValueError):
                modern_parameter_matrix(data, ordinal, index)
    def synthetic_report(self):
        keys = (bytes(512), bytes(513))
        raw = (0x2000000f).to_bytes(4, 'little') + bytes(15072)
        normalized, _ = normalize_observed_raw(raw, keys)
        report = dict(cameraAccess=False,compilerPatched=False,sourceFilesModified=False,
                      changedInputs=[],inputHashes={'descriptor':hashlib.sha256(raw).hexdigest()},
                      rows=[dict(model='synthetic',cameraId=0,
                          modernDescriptorSources=[dict(stage='inputs',length=14796,dataHex=raw[:14796].hex())],
                          descriptorImports=[dict(stage='inputs',callerRva='0x52093',length=14796,dataHex=normalized.hex())],
                          descriptorCopies=[dict(length=7492,dataHex=normalized[:7492].hex())])])
        return report, raw, keys

    def test_report_verifies_truncated_reader_without_compatibility_claim(self):
        report, raw, keys = self.synthetic_report()
        proof = verify_import_report(report, raw, keys)
        self.assertTrue(proof['rows'][0]['exact'])
        self.assertFalse(proof['physicalValidation'])
        self.assertEqual(proof['opaqueTailLength'], 280)

    def test_report_rejects_missing_observer_and_contradictions(self):
        report, raw, keys = self.synthetic_report()
        for field, value in (('descriptorImports', []), ('modernDescriptorSources', []),
                             ('descriptorCopies', [dict(length=7492,dataHex=bytes(7492).hex())])):
            changed = copy.deepcopy(report)
            changed['rows'][0][field] = value
            with self.assertRaises(ValueError):
                verify_import_report(changed, raw, keys)
        for field, value in (('cameraAccess', True), ('changedInputs', ['descriptor']),
                             ('inputHashes', {}), ('rows', [])):
            changed = copy.deepcopy(report)
            changed[field] = value
            with self.assertRaises(ValueError):
                verify_import_report(changed, raw, keys)

    def test_native_version_selection_boundaries(self):
        for version in (0x20000001, 0x20000003, 0x20000007, 0x2000000a):
            self.assertEqual(importer_kind(version), 'compact')
        for version in (0x20000008, 0x20000009, 0x2000000b, 0x2000000f):
            self.assertEqual(importer_kind(version), 'modern')
        for version in (0, 0x20000000, 0x20000002, -1, True, 2**32):
            with self.assertRaises(ValueError):
                importer_kind(version)

    def test_strict_raw_geometries_and_opaque_tail(self):
        keys = (bytes(512), bytes(513))
        for version, size, fn in ((0x2000000a, 7492, normalize_compact),
                                  (0x2000000f, 14796, normalize_modern)):
            prefix = version.to_bytes(4, 'little') + bytes(size - 4)
            tail = bytes(range(140)) * 2
            normalized, retained = normalize_observed_raw(prefix + tail, keys)
            self.assertEqual(normalized, fn(prefix, keys))
            self.assertEqual(retained, tail)
            with self.assertRaises(ValueError):
                normalize_observed_raw(prefix, keys)

    def test_regions_and_opaque_preservation(self):
        source = bytes((i * 17 + 3) % 256 for i in range(14796))
        keys = (bytes(range(256)) * 2, bytes(range(256)) * 2 + b'\x42')
        expected = bytearray(source)
        for ordinal in range(6):
            for index, seed in enumerate((0x3fcb, 0xc7)):
                for relative in (0x10, 0x1f4):
                    start = ordinal * 0x9a0 + relative + index * 240
                    expected[start:start + 240] = decode(source[start:start + 240], keys, seed)
        self.assertEqual(normalize_modern(source, keys), bytes(expected))
        self.assertEqual(normalize_modern(normalize_modern(source, keys), keys), source)

    def test_wrong_geometry_rejected(self):
        for length in (0, 7492, 15076, 14795):
            with self.assertRaises(ValueError):
                normalize_modern(bytes(length), (bytes(512), bytes(513)))

    def test_compact_regions_and_final_style_boundary(self):
        source = bytes((i * 11 + 7) % 256 for i in range(7492))
        keys = (bytes(range(256)) * 2, bytes(range(256)) * 2 + b'\x19')
        expected = bytearray(source)
        for ordinal in range(5):
            for index, seed in enumerate((0x3fcb, 0xc7)):
                for relative in (0x10, 0x1f4):
                    start = ordinal * 0x5d8 + relative + index * 240
                    expected[start:start + 240] = decode(source[start:start + 240], keys, seed)
        self.assertEqual(normalize_compact(source, keys), bytes(expected))
        self.assertEqual(normalize_compact(source, keys)[-12:], source[-12:])
        with self.assertRaises(ValueError):
            normalize_compact(bytes(14796), keys)
