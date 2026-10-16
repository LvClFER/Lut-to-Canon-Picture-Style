import struct
import tempfile
import unittest
from pathlib import Path
from camera_install.pf3_schema_research import extract, parse_schema


class SchemaResearchTests(unittest.TestCase):
    def fixture(self):
        return b''.join(struct.pack('<3I', 0x1000+i, 4, 4) for i in range(50))

    def test_observed_count_and_no_semantic_claim(self):
        rows = parse_schema(self.fixture())
        self.assertEqual(len(rows), 50)
        self.assertTrue(all(row['semanticMeaning'] == 'not-established-by-schema' for row in rows))

    def test_reject_truncated_duplicate_and_misaligned(self):
        original = self.fixture()
        for invalid in (original[:-1], original[:12]+original[:12]+original[24:],
                        struct.pack('<3I', 0x1000, 3, 3)+original[12:]):
            with self.assertRaises(ValueError):
                parse_schema(invalid)

    def test_reject_unknown_dll_before_reading_fixed_rva(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'unknown.dll'
            path.write_bytes(b'not the validated DLL')
            with self.assertRaises(ValueError):
                extract(path)

    def test_size_policies_distinguish_strings_from_numeric_records(self):
        data = struct.pack('<3I', 0x1000, 2, 32)+struct.pack('<3I', 0x1001, 3, 1460)+struct.pack('<3I', 0x1002, 4, 0)+self.fixture()[36:]
        rows = parse_schema(data)
        self.assertEqual([row['inputSizePolicy'] for row in rows[:3]], ['bounded','exact','variable'])
