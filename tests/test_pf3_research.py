import struct
import unittest

from camera_install.pf3_research import parse_records, byte_representations, describe, checksum_observations


class Pf3ResearchTests(unittest.TestCase):
    def test_big_endian_record_offsets_and_tail(self):
        raw = struct.pack(">HHI", 0x1002, 2, 4) + b"test" + b"CRC"
        records, tail = parse_records(raw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "0x1002")
        self.assertEqual(records[0]["fileDataOffset"], 20)
        self.assertEqual(records[0]["data"], b"test")
        self.assertEqual(tail, b"CRC")

    def test_truncated_record_remains_unexplained(self):
        raw = struct.pack(">HHI", 0x1070, 4, 100) + b"short"
        records, tail = parse_records(raw)
        self.assertEqual(records, [])
        self.assertEqual(tail, raw)

    def test_invalid_identifier_does_not_become_a_record(self):
        raw = struct.pack(">HHI", 0x0011, 1, 0)
        self.assertEqual(parse_records(raw), ([], raw))

    def test_endian_candidates(self):
        candidates = dict(byte_representations(bytes.fromhex("00010002")))
        self.assertEqual(candidates["swap16"], bytes.fromhex("01000200"))
        self.assertEqual(candidates["swap32"], bytes.fromhex("02000100"))

    def test_dense_grid_description(self):
        raw = struct.pack("<3H", 12, 3, 33) + bytes(33 ** 3 * 6)
        self.assertTrue(describe(raw)["denseGrid"]["within12Bit"])

    def test_checksum_and_terminator_records(self):
        prefix = struct.pack(">HHI", 0x1002, 2, 4) + b"test"
        checksum = struct.pack(">HHII", 0xFFFE, 4, 4, sum(prefix))
        terminator = struct.pack(">HHI", 0xFFFF, 0xFFFF, 0)
        records, tail = parse_records(prefix + checksum + terminator)
        self.assertEqual(len(records), 3)
        self.assertEqual(tail, b"")
        self.assertEqual(checksum_observations(prefix + checksum + terminator, records)["matchingCandidates"],
                         ["sum_bytes_before_checksum_record"])

    def test_does_not_parse_after_terminator(self):
        terminator = struct.pack(">HHI", 0xFFFF, 0xFFFF, 0)
        extra = struct.pack(">HHI", 0x1002, 2, 0)
        records, tail = parse_records(terminator + extra)
        self.assertEqual(len(records), 1)
        self.assertEqual(tail, extra)

    def test_checksum_absence_is_an_observation_not_parse_failure(self):
        prefix = struct.pack('>HHI', 0x1002, 2, 3) + b'abc'
        terminator = struct.pack('>HHI', 0xffff, 0xffff, 0)
        plain = prefix + terminator
        records, tail = parse_records(plain)
        self.assertEqual(tail, b'')
        self.assertEqual(records[-1]['id'], '0xffff')
        self.assertEqual(checksum_observations(plain, records), {'present': False})

    def test_state_one_checksum_bias_is_not_plain_byte_sum(self):
        prefix = struct.pack('>HHI', 0x1002, 2, 3) + b'abc'
        stored = sum(prefix) + 0x22e1
        plain = prefix + struct.pack('>HHII', 0xfffe, 4, 4, stored)
        records, _ = parse_records(plain)
        observed = checksum_observations(plain, records)
        self.assertEqual(observed['storedBigEndian'] -
                         observed['candidateValues']['sum_bytes_before_checksum_record'], 0x22e1)
        self.assertNotIn('sum_bytes_before_checksum_record', observed['matchingCandidates'])

    def test_empty_tail_does_not_imply_terminator(self):
        plain = struct.pack('>HHI', 0x1002, 2, 3) + b'abc'
        records, tail = parse_records(plain)
        self.assertEqual(tail, b'')
        self.assertNotEqual(records[-1]['id'], '0xffff')

    def test_every_truncated_checksum_is_preserved_as_tail(self):
        prefix = struct.pack('>HHI', 0x1002, 2, 3) + b'abc'
        checksum = struct.pack('>HHII', 0xfffe, 4, 4, sum(prefix))
        for length in range(1, len(checksum)):
            with self.subTest(length=length):
                records, tail = parse_records(prefix + checksum[:length])
                self.assertEqual(len(records), 1)
                self.assertEqual(tail, checksum[:length])

    def test_high_bit_alias_requires_explicit_research_mode(self):
        plain = struct.pack('>HHI', 0x9002, 2, 3) + b'abc'
        self.assertEqual(parse_records(plain), ([], plain))
        records, tail = parse_records(plain, allow_high_bit_records=True)
        self.assertEqual(records[0]['id'], '0x9002')
        self.assertEqual(tail, b'')

    def test_distinct_metadata_banks_keep_ids_data_and_order(self):
        for identifiers in ((0x1002, 0x9002), (0x9002, 0x1002)):
            with self.subTest(identifiers=identifiers):
                payloads = (b'first-bank', b'second-bank')
                plain = b''.join(struct.pack('>HHI', identifier, 2, len(data)) + data
                                 for identifier, data in zip(identifiers, payloads))
                records, tail = parse_records(plain, allow_high_bit_records=True)
                self.assertEqual(tail, b'')
                self.assertEqual([r['id'] for r in records], [hex(i) for i in identifiers])
                self.assertEqual([r['data'] for r in records], list(payloads))
                self.assertEqual(records[1]['decodedHeaderOffset'], 8 + len(payloads[0]))

    def test_repeated_exact_id_is_preserved_not_silently_overwritten(self):
        plain = b''.join(struct.pack('>HHI', 0x1002, 2, len(data)) + data
                         for data in (b'old', b'new'))
        records, tail = parse_records(plain)
        self.assertEqual(tail, b'')
        self.assertEqual([r['id'] for r in records], ['0x1002', '0x1002'])
        self.assertEqual([r['data'] for r in records], [b'old', b'new'])

    def test_checksum_covers_both_banks_without_id_normalization(self):
        prefix = (struct.pack('>HHI', 0x1002, 2, 1) + b'A' +
                  struct.pack('>HHI', 0x9002, 2, 1) + b'B')
        plain = prefix + struct.pack('>HHII', 0xfffe, 4, 4, sum(prefix))
        records, tail = parse_records(plain, allow_high_bit_records=True)
        self.assertEqual(tail, b'')
        self.assertEqual(checksum_observations(plain, records)['matchingCandidates'],
                         ['sum_bytes_before_checksum_record'])
        changed = bytearray(plain)
        changed[9] = 0x10  # Normalize the high ID to 0x1002 without updating checksum.
        changed_records, _ = parse_records(bytes(changed), allow_high_bit_records=True)
        self.assertNotIn('sum_bytes_before_checksum_record',
                         checksum_observations(bytes(changed), changed_records)['matchingCandidates'])


if __name__ == "__main__":
    unittest.main()
