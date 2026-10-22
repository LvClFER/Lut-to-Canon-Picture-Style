import unittest
import struct
from camera_install.alternate_payload_reference import LAYOUT, verify_blocks,expanded_header


class AlternatePayloadTests(unittest.TestCase):
    def test_observed_header_expansion(self):
        old=bytearray((i%256 for i in range(344)))
        struct.pack_into('<H',old,24,0x4140)
        struct.pack_into('<I',old,84,0xfc0040)
        new=expanded_header(bytes(old))
        self.assertEqual(len(new),360)
        self.assertEqual(new[:24],old[:24])
        self.assertEqual(new[24:32],struct.pack('<2I',1,1))
        self.assertEqual(new[92:100],struct.pack('<2I',1,1))
        self.assertEqual(new[104:],old[88:])
        for damaged in (b'',bytes(344),bytes(old[:-1]),bytes(old[:24])+b'xx'+bytes(old[26:])):
            with self.assertRaises(ValueError): expanded_header(damaged)
    def test_older_geometry_and_unknown_header(self):
        decoded,captures,gates=self.fixture()
        shifted={(offset-16,seed):value for (offset,seed),value in decoded.items()}
        self.assertEqual(len(verify_blocks(shifted,captures,gates,344)),3)
        for header in (True,343,345,360.0):
            with self.assertRaises(ValueError): verify_blocks(shifted,captures,gates,header)
    def fixture(self):
        values=[bytes([i])*4096 for i in (1,2,3,2)]
        decoded=dict(zip(LAYOUT,values))
        captures=[{'functionRva':function,'nativePackedHex':value.hex()}
                  for function,value in (('0x49e00',values[0]),('0x4b760',values[1]),('0x4b760',values[2]))]
        gates=[{'index':1,'enabled':True},{'index':2,'enabled':False}]
        return decoded,captures,gates

    def test_mixed_gate_and_duplicate_reference(self):
        rows=verify_blocks(*self.fixture())
        self.assertEqual(len(rows),3)
        self.assertEqual(len(rows[1]['locations']),2)

    def test_missing_corrupt_and_wrong_seed(self):
        decoded,captures,gates=self.fixture()
        for changed in ({},dict(decoded)):
            if changed:
                changed[LAYOUT[0]]=b'bad'
            with self.assertRaises(ValueError): verify_blocks(changed,captures,gates)
        changed=dict(decoded); changed[(360,0)]=changed.pop(LAYOUT[0])
        with self.assertRaises(ValueError): verify_blocks(changed,captures,gates)
        with self.assertRaises(ValueError): verify_blocks(decoded,captures[1:],gates)

    def test_gate_type_index_and_disagreement(self):
        decoded,captures,gates=self.fixture()
        for changed in ([],[gates[0],gates[0]],
                        [{'index':True,'enabled':True},gates[1]],
                        [{'index':1,'enabled':1},gates[1]],
                        [{'index':1,'enabled':False},gates[1]]):
            with self.assertRaises(ValueError): verify_blocks(decoded,captures,changed)

    def test_ambiguous_integer_reference_rejected(self):
        decoded,captures,gates=self.fixture()
        captures.append({'functionRva':'0x49e00','nativePackedHex':captures[1]['nativePackedHex']})
        with self.assertRaises(ValueError): verify_blocks(decoded,captures,gates)
