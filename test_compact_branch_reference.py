import unittest
from camera_install.compact_branch_reference import uses_pixel_builder, verify_builder_links, verify_float_builder_links
from camera_install.compact_branch_reference import coefficient_policy, COEFFICIENT_POLICY_IDS
from camera_install.compact_branch_reference import rejects_fine_detail_branch
from camera_install.compact_branch_reference import convert_alternate_grid,compact_builder_path,derived_compact_grid_flag
from camera_install.compact_branch_reference import compact_first_pair_plan,compact_pixel_scale,compact16752_plan
from camera_install.integer_tetrahedral_reference import table as synthetic_table
from camera_install.compact_branch_reference import older_compact_plan


class CompactBranchTests(unittest.TestCase):
    def test_older_topology_does_not_invent_second_pair_processing(self):
        import struct
        descriptor=bytearray(14796)
        struct.pack_into('<H',descriptor,0x1ee+3*0x9a0+2,1)
        args=(bytes(descriptor),0x84,0x80000382,0)
        self.assertEqual(older_compact_plan(*args,3)['blockPaths'],('cache','cache'))
        self.assertEqual(older_compact_plan(*args,4)['blockPaths'],('pixel','cache','cache','cache'))
        self.assertEqual(older_compact_plan(*args,5,base_callback_noop=True)['totalSize'],16744)
        with self.assertRaises(ValueError):older_compact_plan(*args,5)
        for family in (True,2,6):
            with self.assertRaises(ValueError):older_compact_plan(*args,family)

    def test_complete_plan_requires_serializer_and_callback_evidence(self):
        import struct
        descriptor=bytearray(14796)
        for index in (1,2):struct.pack_into('<H',descriptor,0x1ee+3*0x9a0+index*2,1)
        args=(bytes(descriptor),0x84,0x80000382,0)
        hybrid=compact16752_plan(*args,6,base_callback_noop=True)
        self.assertEqual(hybrid['blockPaths'],('pixel','pixel','cache','cache'))
        self.assertEqual(hybrid['pixelScale'],255)
        self.assertEqual(compact16752_plan(*args,7)['blockPaths'],('pixel',)*4)
        for family in (True,0,5,8,11):
            with self.assertRaises(ValueError):compact16752_plan(*args,family)
        with self.assertRaises(ValueError):compact16752_plan(*args,6)
        with self.assertRaises(ValueError):compact16752_plan(*args,6,base_callback_noop=1)

    def test_complete_plan_keeps_unimplemented_integer_path_visible(self):
        import struct
        descriptor=bytearray(14796)
        struct.pack_into('<H',descriptor,0x1ee+3*0x5d8+2,1)
        args=(bytes(descriptor),0x84,0x80000289,0)
        self.assertEqual(compact16752_plan(*args,6,base_callback_noop=True)['blockPaths'],
                         ('integer-interpolation','cache','cache','cache'))
        self.assertEqual(compact16752_plan(*args,7)['blockPaths'],
                         ('integer-interpolation','cache','integer-interpolation','cache'))
        # A non-one capability word is not permission to process pixels.
        struct.pack_into('<H',descriptor,0x1ee+3*0x5d8+2,2)
        self.assertEqual(compact16752_plan(bytes(descriptor),0x84,0x80000289,0,7)['blockPaths'],('cache',)*4)

    def test_pixel_scale_is_separate_from_coefficients_and_family(self):
        for selector in (0x80000382,0x80000401):self.assertEqual(compact_pixel_scale(selector),255)
        for selector in (0,0x412,0x80000381,0x80000383,0x80000400,0x80000402,0xffffffff):self.assertEqual(compact_pixel_scale(selector),256)
        for selector in (True,-1,0x100000000,1.0):
            with self.assertRaises(ValueError):compact_pixel_scale(selector)

    def test_first_pair_uses_selected_reader_and_explicit_object_flag(self):
        import struct
        descriptor=bytearray(14796)
        # Neutral ordinal3: enable only first modern gate.
        struct.pack_into('<H',descriptor,0x1ee+3*0x9a0+2,1)
        plan=compact_first_pair_plan(bytes(descriptor),0x84,0x80000382,0)
        self.assertEqual(plan,dict(descriptorPrefixBytes=14796,gateWords=(1,0),paths=('pixel','cache')))
        self.assertEqual(compact_first_pair_plan(bytes(descriptor),0x84,0x80000382,1)['paths'],('integer-interpolation','cache'))
        self.assertEqual(compact_first_pair_plan(bytes(descriptor),0x84,0x80000289,0)['paths'],('cache','cache'))
        struct.pack_into('<H',descriptor,0x1ee+3*0x5d8+4,1)
        self.assertEqual(compact_first_pair_plan(bytes(descriptor),0x84,0x80000289,0)['paths'],('cache','integer-interpolation'))
        for args in ((None,0x84,0,0),(bytes(7492),0x84,0,0),(bytes(descriptor),True,0,0),(bytes(descriptor),0x84,0,True)):
            with self.assertRaises(ValueError):compact_first_pair_plan(*args)

    def test_derived_flag_normalizes_internal1001_before_lookup(self):
        zeros={0,39,170,172,201,203,205}
        for selector in range(207):
            self.assertEqual(derived_compact_grid_flag(0x80000169+selector),0 if selector in zeros else 1)
        for value in (0,39,170,205,0x80000168,0xffffffff):
            self.assertEqual(derived_compact_grid_flag(value),1)
        self.assertEqual(derived_compact_grid_flag(0x80000169),0)
        for value in (-1,0x100000000,True,1.0):
            with self.assertRaises(ValueError):derived_compact_grid_flag(value)

    def test_descriptor_gate_precedes_numerical_branch(self):
        for policy in (False,True):
            for flag in (0,1,255):
                self.assertEqual(compact_builder_path(False,policy,flag),'internal-table-copy')
                self.assertEqual(compact_builder_path(True,policy,flag),
                                 'pixel' if not policy and flag==0 else 'integer-interpolation')
        for args in ((0,False,0),(True,0,0),(False,False,256)):
            with self.assertRaises(ValueError):compact_builder_path(*args)

    def test_fine_detail_specific_rejection(self):
        for camera_id in COEFFICIENT_POLICY_IDS:
            self.assertTrue(rejects_fine_detail_branch(camera_id,0x88))
            for selector in (0,0x81,0x82,0x83,0x84,0x85,0xffff):
                self.assertFalse(rejects_fine_detail_branch(camera_id,selector))
        for camera_id in (0,0xffffffff,0x80000433,0x80000487):
            self.assertFalse(rejects_fine_detail_branch(camera_id,0x88))
        for args in ((True,0x88),(0,True),(0,-1),(0,0x10000)):
            with self.assertRaises(ValueError): rejects_fine_detail_branch(*args)
    def test_alternate_quantization_thresholds(self):
        # A constant table cannot expose rounding or plane-coordinate errors.
        table=synthetic_table('identity')
        for value, truncated, rounded in (
                (0,0,0), (.499999,0,0), (.5,0,2),
                (1.499999,2,2), (1.5,2,4),
                (287.499999,574,574), (287.5,574,576),
                (288,576,576), (10000,576,576)):
            values=[value]*1000+[.5]*1000+[287.5]*1000
            self.assertEqual(convert_alternate_grid(values,table,True),
                             [truncated]*1000+[0]*1000+[574]*1000)
            self.assertEqual(convert_alternate_grid(values,table,False),
                             [rounded]*1000+[2]*1000+[576]*1000)

    def test_alternate_planes_and_domain(self):
        table=[10]*1000+[20]*1000+[-30]*1000
        self.assertEqual(convert_alternate_grid([1.25]*3000,table,False),table)
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                convert_alternate_grid([value]*3000,table,False)
        for mode in (False,True):
            for value in (287.5,288,10000):
                self.assertEqual(convert_alternate_grid([value]*3000,table,mode),table)
    def test_policy(self):
        self.assertEqual(len(COEFFICIENT_POLICY_IDS), 41)
        self.assertTrue(all(coefficient_policy(i) for i in COEFFICIENT_POLICY_IDS))
        for value in (0, 0xFFFFFFFF, 0x80000433, 0x80000487, 0x412,
                      0x80000214, 0x80000235, 0x80000394, 0xC0000251):
            self.assertFalse(coefficient_policy(value))
        for value in (-1, 0x100000000, True, '0x412'):
            with self.assertRaises(ValueError):
                coefficient_policy(value)

    def test_float_links(self):
        value = '00' * 24000
        grid = {'argument': 'stack7', 'nodes': 10, 'bytes': 24000,
                'initializedOutputFloat64Hex': value}
        source = {'functionRva': '0x14bd0', 'result': 1, 'gridArguments': [grid]}
        target = {'functionRva': '0x475c0', 'inputPlanarFloat64Hex': value}
        rows = verify_float_builder_links([source, source, target])
        self.assertEqual(rows[0]['sourceCandidates'], [0, 1])
        for data in ([], [target], [dict(source, result=0), target],
                     [dict(source, gridArguments=[dict(grid, argument='stack0')]), target]):
            with self.assertRaises(ValueError):
                verify_float_builder_links(data)

    def test_gate(self):
        for mode in (False, True):
            for flag in range(256):
                self.assertEqual(uses_pixel_builder(mode, flag), not mode and flag == 0)
        for args in ((0, 0), (False, True), (False, -1), (False, 256)):
            with self.assertRaises(ValueError):
                uses_pixel_builder(*args)

    def test_links(self):
        value = '00' * 12000
        builder = {'functionRva': '0x475c0', 'callerRva': '0x4c900',
                   'outputPlanarInt32Hex': value}
        packer = {'functionRva': '0x49e00', 'callerRva': '0x4c92d',
                  'inputPlanarInt32Hex': value}
        self.assertEqual(len(verify_builder_links([builder, packer])), 1)
        for captures in ([], [builder], [dict(builder, callerRva='0x0'), packer],
                         [dict(builder, outputPlanarInt32Hex='00'), packer]):
            with self.assertRaises(ValueError):
                verify_builder_links(captures)
