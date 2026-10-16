import struct
import unittest
from camera_install.cipher_stream_reference import decode
from camera_install.pf3_source_reference import read_source_fields


class SourceReaderTests(unittest.TestCase):
    keys = (bytes(512), bytes(513))  # Synthetic, not Canon keys.

    def wrap(self, body, *, checksum=True):
        if checksum:
            body += struct.pack('>HHII', 0xfffe, 4, 4, sum(body) & 0xffffffff)
        body += struct.pack('>HHI', 0xffff, 0xffff, 0)
        return bytes.fromhex('0000300050535000') + struct.pack('>I', len(body)) + decode(body, self.keys, 12)

    def test_host_records_are_immutable_and_typed(self):
        body = struct.pack('>HHIH', 0x1009, 3, 2, 0x84)
        body += struct.pack('>HHII', 0x1030, 4, 4, 7)
        body += struct.pack('>HHI', 0x1002, 2, 3) + b'ABC'
        fields = read_source_fields(self.wrap(body), self.keys)
        self.assertEqual(fields[0x1009], (3, b'\x84\x00'))
        self.assertEqual(fields[0x1030], (4, b'\x07\x00\x00\x00'))
        self.assertEqual(fields[0x1002], (2, b'ABC'))
        with self.assertRaises(TypeError):
            fields[0x1002] = (2, b'X')

    def test_malformed_sources_fail_before_exposing_fields(self):
        record = struct.pack('>HHIH', 0x1009, 3, 2, 0x84)
        valid = self.wrap(record)
        for raw in (valid[:-1], valid + b'x', bytes(8) + valid[8:],
                    self.wrap(record, checksum=False), self.wrap(record * 2),
                    self.wrap(struct.pack('>HHI', 0x1009, 3, 1) + b'x'),
                    valid[:25] + bytes([valid[25] ^ 1]) + valid[26:]):
            with self.assertRaises(ValueError):
                read_source_fields(raw, self.keys)
