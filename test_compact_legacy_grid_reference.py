import struct,unittest
from camera_install.compact_legacy_grid_reference import compact_legacy_arguments
from camera_install.compact_carrier_reference import build_observed_compact16752_integer
from camera_install.compact_carrier_reference import build_observed_compact_integer
from camera_install.compact_branch_reference import compact_store_plan


class CompactLegacyArgumentTests(unittest.TestCase):
    def test_explicit_compact_store_plan_and_callback_preconditions(self):
        raw=bytearray(7492)
        struct.pack_into('<H',raw,0x1ee+2,1)
        for family,total in ((3,8528),(4,16720),(5,16744),(6,16752)):
            plan=compact_store_plan(bytes(raw),0x81,0x80000176,0,family,base_callback_noop=True)
            self.assertEqual(plan['totalSize'],total)
            self.assertEqual(plan['blockPaths'],('cache','cache') if family==3 else ('integer','cache','cache','cache'))
        for family in (5,6):
            with self.assertRaises(ValueError):compact_store_plan(bytes(raw),0x81,0x80000176,0,family)
        for descriptor,style,selector,family in ((bytes(14796),0x81,0x80000176,4),
                (bytes(raw),0x88,0x80000176,4),(bytes(raw),0x81,412,4),
                (bytes(raw),0x81,0x80000176,1)):
            with self.assertRaises(ValueError):compact_store_plan(descriptor,style,selector,0,family)

    def test_older_compositor_rejects_wrong_geometry_or_direct_pair_paths(self):
        for total,paths in ((True,('cache','cache')),(16728,('cache',)*4),
                (8528,('integer','cache')),(8528,('cache',)*4),
                (16720,None),(16744,['cache']*4)):
            with self.assertRaises(ValueError):
                build_observed_compact_integer({},bytes(7492),None,
                    block_paths=paths,internal_selector=0x80000176,total_size=total)

    def test_integer_compositor_rejects_unestablished_routes_before_records(self):
        for descriptor,paths,selector in (
                (bytes(14796),('integer','cache','cache','cache'),0x80000289),
                (bytes(7492),('integer','cache','cache','cache'),412),
                (bytes(7492),('integer','cache','integer','cache'),0x80000289),
                (bytes(7492),('pixel','cache','cache','cache'),0x80000289)):
            with self.assertRaises(ValueError):
                build_observed_compact16752_integer({},descriptor,None,
                    block_paths=paths,internal_selector=selector)

    def test_native_kind_remains_separate_and_signed_values_expand(self):
        raw=bytearray(7492);offset=0x2d0+0x104
        struct.pack_into('<HH',raw,offset,0,1)
        for p in range(16):struct.pack_into('<H' if p%4==0 else '<h',raw,offset+4+p*2,p//4 if p%4==0 else -p)
        args,native=compact_legacy_arguments(bytes(raw),0x81,1)
        self.assertEqual(struct.unpack_from('<II',native),(0,1))
        self.assertEqual(struct.unpack_from('<II',bytes.fromhex(args['additionalParameterBlock']['initializedHex'])),(1,1))
        self.assertEqual(struct.unpack_from('<5i',native,8),(4,0,-1,-2,-3))
        self.assertIsNone(args['oldParameterBlock'])

    def test_geometry_kind_style_and_index_are_strict(self):
        raw=bytes(7492)
        for data,style,index in ((bytes(14796),0x81,1),(bytearray(raw),0x81,1),(raw,0x88,1),(raw,0x81,True),(raw,0x81,0)):
            with self.assertRaises(ValueError):compact_legacy_arguments(data,style,index)
        for kind,count in ((1,0),(2,3),(0,9)):
            changed=bytearray(raw);struct.pack_into('<HH',changed,0x2d0+0x104,kind,count)
            with self.assertRaises(ValueError):compact_legacy_arguments(bytes(changed),0x81,1)
