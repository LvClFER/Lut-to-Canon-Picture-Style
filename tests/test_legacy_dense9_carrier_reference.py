import struct,unittest
from camera_install.legacy_dense9_carrier_reference import build_legacy_dense9_carrier


class LegacyDenseCarrierTests(unittest.TestCase):
    def setUp(self):
        self.keys=(bytes(512),bytes(513))
        self.metadata=struct.pack('<I',1460)+bytes(1456)
        table=struct.pack('<3H',12,3,33)+bytes(215622)
        self.fields={0x1002:(2,b'Own synthetic test\0'),0x1009:(3,struct.pack('<H',0x84)),
                     0x1018:(4,bytes(300)),0x1029:(4,bytes(240)),
                     0x1070:(3,table),0x1071:(3,table)}

    def test_two_explicit_geometries(self):
        for size,offset in ((8164,76),(8168,332)):
            result=build_legacy_dense9_carrier(self.fields,self.keys,self.metadata,total_size=size)
            self.assertEqual(len(result),size)
            self.assertEqual(struct.unpack_from('<II',result),(1,size-40))
            self.assertEqual(result[offset:offset+1460],self.metadata)
            self.assertEqual(result[8:40],result[44:76])
            if size==8168:self.assertEqual(struct.unpack_from('<I',result,76)[0],0xfc0028)

    def test_unknown_or_incomplete_inputs_rejected(self):
        for size in (16744,8165,True,None):
            with self.assertRaises(ValueError):
                build_legacy_dense9_carrier(self.fields,self.keys,self.metadata,total_size=size)
        for missing in (0x1018,0x1029,0x1070,0x1071):
            fields={k:v for k,v in self.fields.items() if k!=missing}
            with self.assertRaises(ValueError):
                build_legacy_dense9_carrier(fields,self.keys,self.metadata,total_size=8164)
        with self.assertRaises(ValueError):
            build_legacy_dense9_carrier(self.fields,self.keys,bytes(1460),total_size=8164)
