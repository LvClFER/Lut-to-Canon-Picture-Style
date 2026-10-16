import unittest

from camera_install.cipher_known_plaintext_reference import recover_equivalent_tables, recover_sparse_tables, recover_masked_tables
from camera_install.cipher_stream_reference import decode


class KnownPlaintextCipherTests(unittest.TestCase):
    def test_partial_bytes_combine_without_assuming_unknown_bits(self):
        positions = tuple(i * 513 for i in range(512)) + tuple(i * 512 for i in range(1, 513))
        rows = []
        for p in positions:
            cipher = decode(b'\xa5', self.keys, p)[0]
            # Unknown bits intentionally wrong; masks must exclude them.
            rows.extend(((p, 0xa0, cipher, 0xf0), (p, 0x05, cipher, 0x0f)))
        recovered = recover_masked_tables(tuple(rows))
        held_out = bytes(range(256)) * 1026
        self.assertEqual(decode(held_out, recovered, 731), decode(held_out, self.keys, 731))
        self.assertEqual(recovered[0][0], 0)
        with self.assertRaisesRegex(ValueError, 'every bit'):
            recover_masked_tables(tuple(rows[::2]))

    def test_masked_evidence_rejects_invalid_and_disconnected_conflicts(self):
        for row in ((0, 0, 0, 0), (0, 0, 0, True), (0, 0, 0, 256),
                    (True, 0, 0, 255), (0, 0, 0), (0, -1, 0, 255)):
            with self.assertRaises(ValueError):
                recover_masked_tables((row,))
        # Contradictions outside the component containing node0 still matter.
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            recover_masked_tables(((100, 0, 0, 1), (100, 1, 0, 1)))

    def setUp(self):
        self.keys = (bytes((i * 73 + 11) % 256 for i in range(512)),
                     bytes((i * i + 31 * i + 17) % 256 for i in range(513)))

    def test_reconstructs_stream_not_original_tables(self):
        plain = bytes((i * 19) % 256 for i in range(2048))
        for seed in (0, 12, 511, 512, 513, 0xb8ed, 0x33137):
            with self.subTest(seed=seed):
                recovered = recover_equivalent_tables(plain, decode(plain, self.keys, seed), seed=seed)
                self.assertEqual(recovered[0][0], 0)
                self.assertNotEqual(recovered, self.keys)
                # Held-out full combined cycle, unrelated plaintext and seed.
                held_out = bytes(range(256)) * 1026
                self.assertEqual(decode(held_out, recovered, 987), decode(held_out, self.keys, 987))

    def test_redundant_inconsistent_evidence_rejected(self):
        plain = bytes(2048)
        cipher = bytearray(decode(plain, self.keys, 12))
        cipher[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            recover_equivalent_tables(plain, bytes(cipher), seed=12)

    def test_evidence_boundaries(self):
        for plain, cipher, seed in ((b'', b'', 0), (bytes(1024), bytes(1025), 0),
                                    (bytes(1024), bytes(1024), -1),
                                    (bytes(1024), bytes(1024), True),
                                    (bytes(1024), bytes(1024), 0xffffffff)):
            with self.assertRaises(ValueError):
                recover_equivalent_tables(plain, cipher, seed=seed)
        with self.assertRaises(TypeError):
            recover_equivalent_tables(bytearray(1024), bytes(1024), seed=0)

    def test_disjoint_evidence_blocks_recover_held_out_stream(self):
        # All 1025 nodes connected by CRT-selected spanning-tree edges.
        # No contiguous known-plaintext run is required by this solver.
        positions = tuple(i * 513 for i in range(512)) + tuple(i * 512 for i in range(1, 513))
        observations = tuple((p, 0, self.keys[0][p % 512] ^
                              self.keys[1][p % 513] ^ 0x37) for p in positions)
        recovered = recover_sparse_tables(observations)
        held_out = bytes(range(256)) * 1026
        self.assertEqual(decode(held_out, recovered, 123), decode(held_out, self.keys, 123))

    def test_sparse_rejects_incomplete_malformed_and_conflicting_evidence(self):
        for evidence in ((), ((0, 0, 0),), ((True, 0, 0),), ((0, -1, 0),),
                         ((0, 0, 256),), ((0, 0),), [(0, 0, 0)]):
            with self.assertRaises(ValueError):
                recover_sparse_tables(evidence)
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            recover_sparse_tables(((0, 0, 0), (0, 0, 1)))


if __name__ == '__main__':
    unittest.main()
