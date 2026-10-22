import struct
import unittest
from camera_install.registration_encode_reference import encode_state, encode_style, frame_property, MAX_TRANSFER_BYTES
from camera_install.ptp_capture import build_canon_property_packet


class RegistrationEncodingTests(unittest.TestCase):
    def test_capacity_does_not_silently_truncate(self):
        value=struct.pack('<I',4)
        for capacity in (0,11,True,12.5):
            with self.assertRaises(ValueError): frame_property(0xd163,value,capacity=capacity)
        self.assertEqual(frame_property(0xd163,value,capacity=12),frame_property(0xd163,value,capacity=20))

    def test_total_packet_bound_includes_header(self):
        size=MAX_TRANSFER_BYTES-8
        value=struct.pack('<I',size)+bytes(size-4)
        self.assertEqual(len(frame_property(0xd170,value)),MAX_TRANSFER_BYTES)
        with self.assertRaises(ValueError): frame_property(0xd170,value+b'x')

    def test_invalid_types_and_snapshot(self):
        for code in (True,1.5,'1'):
            with self.assertRaises(ValueError): frame_property(code,struct.pack('<I',4))
        for data in (1000000000,'abc',None):
            with self.assertRaises(ValueError): encode_style(data)
        with self.assertRaises(ValueError): encode_state(bytes(40),extended=1)
        mutable=bytearray(struct.pack('<II',1,4)+b'abcd')
        encoded=encode_style(memoryview(mutable))
        mutable[-1]=0
        self.assertEqual(encoded,struct.pack('<II',12,1)+b'abcd')

    def test_state_framing_matches_capture_reference(self):
        normalized=struct.pack('<10I',*range(10))
        self.assertEqual(frame_property(0xd163,encode_state(normalized,extended=True)),
                         build_canon_property_packet(0xd163,normalized))

    def test_style_framing_keeps_serialized_length(self):
        normalized=struct.pack('<II',1,4)+b'abcd'
        self.assertEqual(frame_property(0xd170,encode_style(normalized)),
                         struct.pack('<IIII',20,0xd170,12,1)+b'abcd')

    def test_frame_rejects_invalid_length(self):
        for data in (b'',bytes(4),struct.pack('<I',12)+bytes(4)):
            with self.assertRaises(ValueError):
                frame_property(0xd163,data)
        with self.assertRaises(ValueError):
            frame_property(-1,struct.pack('<I',4))

    def test_extended_distinct_words(self):
        actual = encode_state(struct.pack('<10I', *range(10)), extended=True)
        self.assertEqual(struct.unpack('<11I', actual), (44, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9))

    def test_legacy_distinct_words(self):
        actual = encode_state(struct.pack('<7I', *range(7)), extended=False)
        self.assertEqual(struct.unpack('<8I', actual), (32, 0, 1, 2, 3, 4, 5, 6))

    def test_style_preserves_payload_and_validity(self):
        for validity in (0, 1, 2, 0xffffffff):
            for payload in (b'', b'abcd', bytes(range(64))):
                self.assertEqual(encode_style(struct.pack('<II', validity, len(payload))+payload),
                                 struct.pack('<II', len(payload)+8, validity)+payload)

    def test_rejects_mismatched_structures(self):
        for extended in (False, True):
            for data in (b'', bytes(32), bytes(44)):
                with self.assertRaises(ValueError):
                    encode_state(data, extended=extended)
        for data in (b'', struct.pack('<II', 1, 8), bytes(9)):
            with self.assertRaises(ValueError):
                encode_style(data)
