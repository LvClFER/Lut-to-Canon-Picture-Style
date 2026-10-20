import struct
import unittest
from camera_install.cipher_stream_reference import decode
from camera_install.pf3_source_reference import read_source_fields, write_source_fields


class SourceReaderTests(unittest.TestCase):
    keys = (bytes(512), bytes(513))  # Synthetic, not Canon keys.

    def test_reference_bank_keeps_its_own_ids_values_and_record_order(self):
        fields = {0x1002: (2, b'Active'), 0x9002: (2, b'Reference'),
                  0x1032: (4, struct.pack('<i', 2)), 0x9032: (4, bytes(4))}
        raw = write_source_fields(fields, self.keys)
        loaded = read_source_fields(raw, self.keys)
        self.assertEqual(tuple(loaded), tuple(fields))
        self.assertEqual(loaded, fields)
        self.assertEqual(write_source_fields(loaded, self.keys), raw)
        changed = dict(loaded)
        changed[0x1032] = (4, struct.pack('<i', -1))
        reopened = read_source_fields(write_source_fields(changed, self.keys), self.keys)
        self.assertEqual(reopened[0x9032], fields[0x9032])
        self.assertEqual(reopened[0x9002], fields[0x9002])

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

    def test_writer_reproduces_original_bytes_and_preserves_order_and_types(self):
        body = struct.pack('>HHIH', 0x1009, 3, 2, 0x84)
        body += struct.pack('>HHII', 0x1031, 4, 4, 0xfffffffc)
        body += struct.pack('>HHI', 0x1008, 0xffff, 3) + b'abc'
        raw = self.wrap(body)
        fields = read_source_fields(raw, self.keys)
        self.assertEqual(write_source_fields(fields, self.keys), raw)
        edited = dict(fields)
        edited[0x1031] = (4, struct.pack('<i', 3))
        self.assertEqual(read_source_fields(write_source_fields(edited, self.keys), self.keys), edited)

    def test_writer_rejects_invalid_field_boundaries(self):
        for fields in ({}, {0xfffe: (4, bytes(4))}, {0x1000: (3, b'x')},
                       {0x1000: (4, bytearray(4))}, {0x1000: (1, b'x')},
                       {0x1000: [2, b'x']}):
            with self.assertRaises(ValueError):
                write_source_fields(fields, self.keys)
