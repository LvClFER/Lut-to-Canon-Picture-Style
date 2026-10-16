import struct
import unittest
from camera_install.pf3_auxiliary_research import nested_records


class NestedTests(unittest.TestCase):
    def test_complete_nested_structure(self):
        data = struct.pack(">HHIIHHI", 0x10, 4, 4, 6, 0xffff, 0xffff, 0)
        result = nested_records(data)
        self.assertTrue(result["completeTerminatedStructure"])
        self.assertEqual(result["records"][0]["unsigned32BigEndian"], [6])
        self.assertFalse(result["semanticsValidated"])

    def test_truncation_is_not_accepted(self):
        result = nested_records(struct.pack(">HHI", 0x10, 4, 440))
        self.assertFalse(result["completeTerminatedStructure"])
        self.assertEqual(result["tailSize"], 8)

    def test_trailing_bytes_not_ignored(self):
        result = nested_records(struct.pack(">HHI", 0xffff, 0xffff, 0) + b"x")
        self.assertFalse(result["completeTerminatedStructure"])
        self.assertEqual(result["tailSize"], 1)

    def test_six_groups_preserve_signed_candidates(self):
        group = [1, 1, 2, 0, 50 * 65536, 50 * 65536, (-30 * 65536) & 0xffffffff,
                 0, 0, 30 * 65536, 100 * 65536, 100 * 65536, 0, 0, 0, 20, 0, 0]
        payload = struct.pack(">110I", *([6, 6] + group * 6))
        data = struct.pack(">HHI", 0x10, 4, len(payload)) + payload + struct.pack(">HHI", 0xffff, 0xffff, 0)
        hypothesis = nested_records(data)["records"][0]["sixGroupHypothesis"]
        self.assertEqual(len(hypothesis["groups"]), 6)
        self.assertEqual(hypothesis["candidateSigned16_16Fields"][0][3], -30)
        self.assertFalse(hypothesis["fieldMeaningValidated"])
