import struct
import unittest
from camera_install.canon_events import extract_property_values, decode_observed_rp_d163, decode_event_batch


class CanonEventTests(unittest.TestCase):
    def test_observed_state_layout_preserves_control(self):
        control = bytes(range(32))
        result = decode_observed_rp_d163(struct.pack("<III", 44, 1, 65)+control)
        self.assertEqual(result.selector, 65)
        self.assertEqual(result.control, control)
        self.assertNotIn("control=", repr(result))

    def test_state_layout_rejects_write_value_and_unknown_prefix(self):
        for data in (struct.pack("<II", 1, 65)+bytes(32),
                     struct.pack("<III", 40, 1, 65)+bytes(32),
                     struct.pack("<III", 44, 2, 65)+bytes(32)):
            with self.assertRaises(ValueError):
                decode_observed_rp_d163(data)

    def test_multiple_values_and_other_properties(self):
        def record(code, value):
            return struct.pack("<III", 12+len(value), 0xC189, code)+value
        data = record(0xD163, b"one")+record(0xD170, b"other")+record(0xD163, b"two")
        self.assertEqual(extract_property_values(data, 0xD163), [b"one", b"two"])

    def test_terminator_cannot_hide_nonzero_tail(self):
        with self.assertRaises(ValueError):
            extract_property_values(struct.pack("<II", 8, 0)+b"x", 0xD163)

    def test_value_bound(self):
        with self.assertRaises(ValueError):
            extract_property_values(struct.pack("<III", 15, 0xC189, 0xD163)+b"abc", 0xD163, 2)

    def test_truncated_property(self):
        with self.assertRaises(ValueError):
            extract_property_values(struct.pack("<II", 8, 0xC189), 0xD163)

    def test_rejects_nonbuffers_and_invalid_integer_fields(self):
        for data in (44, True, "state", None):
            with self.assertRaises(ValueError):
                decode_observed_rp_d163(data)
            with self.assertRaises(ValueError):
                extract_property_values(data, 0xD163)
        for code in (True, 1.0, "1", -1, 2**32):
            with self.assertRaises(ValueError):
                extract_property_values(b"", code)
        for maximum in (True, 1.0, 0, -1, 16*1024*1024+1):
            with self.assertRaises(ValueError):
                extract_property_values(b"", 0xD163, maximum)

    def test_mutable_input_is_snapshotted(self):
        data = bytearray(struct.pack("<III", 44, 1, 65)+bytes(range(32)))
        state = decode_observed_rp_d163(memoryview(data))
        data[:] = bytes(len(data))
        self.assertEqual(state.control, bytes(range(32)))
        record = bytearray(struct.pack("<III", 15, 0xC189, 0xD163)+b"abc")
        values = extract_property_values(memoryview(record), 0xD163)
        record[-3:] = b"xyz"
        self.assertEqual(values, [b"abc"])

    def test_all_truncations_of_record_fail(self):
        record = struct.pack("<III", 16, 0xC189, 0xD163)+b"abcd"
        for length in range(1, len(record)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                extract_property_values(record[:length], 0xD163)

    def test_continuation_marker_is_distinct_from_normal_end(self):
        record = struct.pack("<III", 15, 0xC189, 0xD163)+b"abc"
        for marker in (0, 0xffffffff):
            batch = decode_event_batch(record+struct.pack("<II", 8, marker))
            self.assertEqual(batch.continuation, marker == 0xffffffff)
            self.assertEqual(batch.properties[0].property_code, 0xD163)
            self.assertEqual(batch.properties[0].value, b"abc")
            self.assertNotIn("abc", repr(batch))
        self.assertTrue(decode_event_batch(struct.pack("<II", 8, 0xffffffff)).continuation)
        self.assertFalse(decode_event_batch(b"").continuation)

    def test_continuation_cannot_hide_nonzero_tail_or_unknown_layout(self):
        for data in (struct.pack("<II", 8, 0xffffffff)+b"x",
                     struct.pack("<II", 12, 0xffffffff)+bytes(4),
                     struct.pack("<II", 4, 0xffffffff)):
            with self.assertRaises(ValueError):
                decode_event_batch(data)

    def test_batch_bound_and_existing_selected_property_bound(self):
        record = struct.pack("<III", 15, 0xC189, 0xD170)+b"abc"
        with self.assertRaises(ValueError):
            decode_event_batch(record, 2)
        self.assertEqual(extract_property_values(record, 0xD163, 2), [])
