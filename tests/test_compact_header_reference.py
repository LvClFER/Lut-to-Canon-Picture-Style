import struct
import unittest
from camera_install.compact_header_reference import build_compact16752_prefix,build_older_compact_prefix,inspect_compact16752_style
from camera_install.control_section_reference import build_control_plain
from camera_install.cipher_stream_reference import decode
from camera_install.packed10_reference import pack10_integer


class CompactHeaderTests(unittest.TestCase):
    def test_observed_format_requires_markers_padding_and_reserved_bits(self):
        keys=(bytes(512),bytes(513))
        prefix=build_compact16752_prefix(self.fields(),build_control_plain({}))
        table=pack10_integer([0]*3000)
        carrier=prefix+b''.join(decode(table,keys,seed) for seed in (0xb8ed,0x33137)*2)
        normalized=carrier[:8]+carrier[40:]
        self.assertEqual(inspect_compact16752_style(normalized,keys),
            dict(styleSelector=0x84,blockCount=4,gridNodes=10,compilerRouteEstablished=False))
        # Header tags and packed reserved bits provide evidence beyond total length.
        for offset in (0,4,8,10,60,64,76,78,80,336+3):
            corrupt=bytearray(normalized);corrupt[offset]^=0x80
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                inspect_compact16752_style(bytes(corrupt),keys)
        for invalid in (None,16720,normalized[:-1],normalized+b'x'):
            with self.assertRaises(ValueError):inspect_compact16752_style(invalid,keys)

    def fields(self):
        fields={i:(4,struct.pack('<I',3)) for i in range(0x1030,0x1036)}
        fields.update({0x1002:(2,b'name\0'),0x1009:(3,b'\x84\0'),0x100c:(3,b'\x12\0')})
        return fields

    def test_compact_offsets_and_16bit_size(self):
        value=build_compact16752_prefix(self.fields(),build_control_plain({}))
        self.assertEqual(len(value),368)
        self.assertEqual(struct.unpack_from('<I',value,4)[0],16712)
        self.assertEqual(struct.unpack_from('<HH',value,40),(16712,0x84))
        self.assertEqual(value[8:40],value[44:76])
        self.assertEqual(struct.unpack_from('<II',value,92),(0xdeadbeef,0xdeadbeef))
        self.assertEqual(struct.unpack_from('<HH',value,108),(0x48,252))
        self.assertEqual(value[364:],b'\x12\0\0\0')

    def test_missing_controls_and_bad_envelope_fail(self):
        fields=self.fields();del fields[0x1031]
        with self.assertRaises(ValueError):build_compact16752_prefix(fields,build_control_plain({}))
        with self.assertRaises(ValueError):build_compact16752_prefix(self.fields(),bytes(252))

    def test_older_layout_envelopes_controls_and_sizes(self):
        control=build_control_plain({})
        for size,length,offset,marker in ((8528,336,76,0x28),(16720,336,76,0x28),(16744,360,100,0x40)):
            value=build_older_compact_prefix(self.fields(),control,size)
            self.assertEqual(len(value),length)
            self.assertEqual(struct.unpack_from('<I',value,4)[0],size-40)
            self.assertEqual(struct.unpack_from('<HH',value,40),(size-40,0x84))
            self.assertEqual(struct.unpack_from('<HH',value,offset),(marker,252))
            self.assertEqual(value[offset+4:offset+256],control)
            self.assertEqual(value[-4:],b'\x12\0\0\0')
        for size in (True,0,16752,83076,8528.0):
            with self.assertRaises(ValueError):build_older_compact_prefix(self.fields(),control,size)
