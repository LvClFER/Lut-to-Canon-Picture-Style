import unittest
from camera_install.cipher_stream_reference import decode


class CipherStreamTests(unittest.TestCase):
    def test_synthetic_roundtrip_and_chunk_alignment(self):
        keys = (bytes(i % 256 for i in range(512)),
                bytes((i * 19) % 256 for i in range(513)))
        source = bytes(i % 251 for i in range(8192))
        for seed in (0, 0x22e1, 0xb8ed, 0x33137):
            encoded = decode(source, keys, seed)
            self.assertEqual(decode(encoded, keys, seed), source)
            self.assertEqual(encoded, decode(source[:1025], keys, seed) +
                             decode(source[1025:], keys, seed + 1025))

    def test_known_synthetic_equation_and_lengths(self):
        self.assertEqual(decode(bytes(3), (bytes(512), bytes(513)), 0), b'777')
        for keys in ((bytes(511), bytes(513)), (bytes(512), bytes(512))):
            with self.assertRaises(ValueError):
                decode(b'', keys)
