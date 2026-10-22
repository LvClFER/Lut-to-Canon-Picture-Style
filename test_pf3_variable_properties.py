import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import canon_engine as engine
from camera_install.pf3_source_reference import read_source_fields, write_source_fields


class VariablePropertyTests(unittest.TestCase):
    def test_independent_export_preserves_variable_blobs_and_source_size(self):
        fields=engine._generated_pf3_fields('Standard')
        blob=bytes(range(256))*5+bytes(156)
        fields[0x1023]=(fields[0x1023][0],blob)
        keys=(bytes(512),bytes(513))
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'base.pf3';output=Path(temporary)/'output.pf3'
            source.write_bytes(write_source_fields(fields,keys))
            with patch.object(engine,'_independent_pf3_input',return_value=(keys,fields)):
                self.assertEqual(engine.read_base_properties(None,source)[0x40001023],blob)
                controls=dict(contrast=0,saturation=0,color_tone=0)
                engine.export_pf3(None,source,output,[],controls,'Variable blob')
            self.assertEqual(output.stat().st_size,source.stat().st_size)
            self.assertEqual(read_source_fields(output.read_bytes(),keys)[0x1023][1],blob)

    def test_native_reader_enforces_parsed_fields_but_not_opaque_blobs(self):
        api=Mock();api.get_property.return_value=b'opaque'
        with patch.object(engine,'EdsCFParse',return_value=api):
            engine.read_base_properties('mock.dll','mock.pf3')
        expected={call.args[1]:call.args[2] for call in api.get_property.call_args_list}
        self.assertIsNone(expected[0x40001023]);self.assertEqual(expected[0x115],32)
        self.assertEqual(expected[0x40001070],215628)

    def test_explicit_size_requests_still_reject_incompatible_blobs(self):
        fields=engine._generated_pf3_fields('Standard');fields[0x1023]=(3,bytes(1436))
        with self.assertRaises(ValueError):
            engine._independent_editor_properties(fields,[(0x40001023,8)])


if __name__=='__main__':unittest.main()
