import struct
import unittest
from camera_install.ptp_wire import Container, Decoder


class PtpWireTests(unittest.TestCase):
    def test_every_fragment_boundary(self):
        item = Container(2, 0x1001, 7, b"synthetic payload")
        wire = item.encode()
        for boundary in range(len(wire)+1):
            decoder = Decoder()
            self.assertEqual(decoder.feed(wire[:boundary])+decoder.feed(wire[boundary:]), [item])
            decoder.finish()

    def test_coalesced_command_response(self):
        items = [Container(1, 0x1001, 4), Container(3, 0x2001, 4)]
        self.assertEqual(Decoder().feed(b"".join(x.encode() for x in items)), items)

    def test_invalid_geometry(self):
        for item in (Container(9, 1, 1), Container(1, 1, 1, b"x"), Container(4, 1, 1, bytes(16))):
            with self.assertRaises(ValueError):
                item.encode()

    def test_malformed_length_and_truncation(self):
        with self.assertRaises(ValueError):
            Decoder().feed(struct.pack("<IHHI", 11, 2, 1, 1))
        decoder = Decoder()
        decoder.feed(Container(2, 1, 1, b"abc").encode()[:-1])
        with self.assertRaises(ValueError):
            decoder.finish()
