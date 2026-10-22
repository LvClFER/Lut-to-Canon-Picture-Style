import struct
import unittest
from camera_install.tail_settings_reference import settings_from_records, modern_user_grid_arguments


class TailSettingsTests(unittest.TestCase):
    def test_empty_axes_keep_a_nonnull_zero_count_block_in_both_modes(self):
        records=self.records()
        empty=struct.pack('<2I',2,0)+bytes(504)
        records.update({0x1061:empty,0x1062:empty,0x1029:bytes(240),0x102b:struct.pack('<2I',1,0)})
        for mode in (1,2):
            axis=settings_from_records(records,mode)['axisBlock']
            self.assertEqual(axis['count'],0)
            self.assertEqual(bytes.fromhex(axis['initializedHex']),empty)
        for bad in (empty[:-4],empty+bytes(4),empty[:-1]+b'\x01',struct.pack('<2I',1,0)+bytes(504)):
            records[0x1061]=bad
            with self.assertRaises(ValueError):settings_from_records(records)

    def test_mode2_uses_distinct_matrix_axes_and_selector(self):
        records = self.records()
        records.update({0x1029: bytes([4]) * 240, 0x1062: records[0x1061],
                        0x102b: struct.pack('<II', 1, 0)})
        value = modern_user_grid_arguments(records, 2)
        self.assertEqual(value['matrix240Hex'], records[0x1029].hex())
        self.assertEqual(value['numericArguments'], [2, 1])
        self.assertIsNone(value['oldParameterBlock'])
        del records[0x1062]
        with self.assertRaises(ValueError):
            modern_user_grid_arguments(records, 2)

    def test_unknown_source_mode_rejected(self):
        for mode in (0, 3, True):
            with self.assertRaises(ValueError):
                settings_from_records(self.records(), mode)

    def records(self):
        axis = bytearray(512)
        struct.pack_into('<II', axis, 0, 2, 6)
        for n in range(6):
            struct.pack_into('<I', axis, 8 + n * 84, 5)
        return {0x1018: bytes([1]) * 300, 0x1065: bytes([2]) * 300,
                0x1019: bytes([3]) * 300, 0x1021: bytes(240),
                0x1061: bytes(axis), 0x1023: struct.pack('<II', 1, 0)}

    def test_distinct_curve_provenance(self):
        value = settings_from_records(self.records())
        self.assertEqual(bytes.fromhex(value['preCurvesHex']), bytes([1]) * 300)
        self.assertEqual(bytes.fromhex(value['postCurvesHex']), bytes([2]) * 300)
        self.assertEqual(bytes.fromhex(value['thirdCurvesHex']), bytes([3]) * 300)
        self.assertEqual((value['mode'], value['splitCount']), (1, 0))

    def test_missing_or_wrong_spans(self):
        for identifier in self.records():
            records = self.records()
            del records[identifier]
            with self.assertRaises(ValueError):
                settings_from_records(records)
        records = self.records()
        records[0x1023] += b'\0'
        with self.assertRaises(ValueError):
            settings_from_records(records)

    def test_nonempty_selector_bounds(self):
        records = self.records()
        records[0x1023] = struct.pack('<III', 1, 1, 4) + bytes(64)
        self.assertEqual(settings_from_records(records)['selectorBlock']['points'], 4)
        records[0x1023] = struct.pack('<III', 1, 13, 4) + bytes(64)
        with self.assertRaises(ValueError):
            settings_from_records(records)
