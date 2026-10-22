import hashlib
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

import canon_engine as engine
import canon_runtime as runtime
import build_standalone
import package_public_alpha as package
from project_state import ProjectDocument,load_project
from camera_install.pf3_source_reference import write_source_fields


class BundledBasicPf3Tests(unittest.TestCase):
    def test_empty_editor_resolves_all_bases_without_selecting_a_reference(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from canon_style_studio import CanonStyleStudioQt
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(os.environ,{'CANON_STYLE_STUDIO_PORTABLE_ROOT':temporary}), \
                patch('canon_style_studio.discover_pse',return_value=None), \
                patch('canon_style_studio.find_dll',return_value=None), \
                patch('canon_engine.EdsCFParse',side_effect=AssertionError('Canon forbidden')):
            window=CanonStyleStudioQt()
            try:
                for style in engine.PICTURE_STYLE_IDS:
                    window.base_combo.setCurrentText(style)
                    self.assertEqual(window.resolve_current_base()['path'],runtime.basic_pf3_resource(style))
            finally:
                window.engine_pool.waitForDone(15000)
                window.dirty=False;window.close();app.processEvents()

    def test_first_use_generates_and_reopens_all_bases_without_input_or_canon(self):
        originals={style:hashlib.sha256(runtime.basic_pf3_resource(style).read_bytes()).hexdigest()
                   for style in engine.PICTURE_STYLE_IDS}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch('canon_engine.runtime_cache_dir',return_value=root/'empty-cache'), \
                    patch('canon_engine.EdsCFParse',side_effect=AssertionError('Canon forbidden')), \
                    patch('canon_engine.discover_pse',side_effect=AssertionError('Canon discovery forbidden')):
                for style in engine.PICTURE_STYLE_IDS:
                    with self.subTest(style=style):
                        base=engine.resolve_independent_base_pf3(style)
                        self.assertEqual(base['path'],runtime.basic_pf3_resource(style))
                        controls=dict(contrast=2,saturation=-1,color_tone=1)
                        output=root/(style+'.canonstyleproject')
                        project=ProjectDocument(name=style,edit=dict(basePictureStyle=style,
                            base_name=style,base_path=str(base['path']),luts=[],**controls))
                        engine.export_style_project(None,base['path'],output,[],controls,style,project)
                        reopened=load_project(output,extraction_root=root/(style+' reopened'))
                        details=engine.inspect_pf3(None,reopened.renderedPf3)
                        self.assertEqual(details['basic']['contrast'],2)
                        _keys,fields=engine._independent_pf3_input(reopened.renderedPf3)
                        self.assertEqual(fields[0x1009][1],struct.pack('<H',engine.PICTURE_STYLE_IDS[style]))
                        self.assertEqual(originals[style],hashlib.sha256(base['path'].read_bytes()).hexdigest())
                self.assertFalse((root/'empty-cache'/'generated_pf3_bases').exists())

    def test_older_nonidentity_pf3_can_use_bundled_reference_in_empty_cache(self):
        keys,fields=engine._independent_pf3_input(runtime.basic_pf3_resource('Neutral'))
        fields=dict(fields)
        fields[0x1021]=(4,bytes(240))
        table=bytearray(fields[0x1070][1]);table[6:]=bytes(len(table)-6)
        fields[0x1070]=fields[0x1071]=(3,bytes(table))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'old.pf3'
            source.write_bytes(write_source_fields(fields,keys))
            with patch('canon_engine.runtime_cache_dir',return_value=root/'empty'), \
                    patch('canon_engine.EdsCFParse',side_effect=AssertionError('Canon forbidden')):
                _recovered,actual=engine._independent_pf3_input(source)
                self.assertEqual(actual,fields)

    def test_packagers_allow_only_exact_authorized_basic_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);basics=root/'basic_pf3';basics.mkdir()
            target=basics/'neutral.pf3'
            shutil.copy2(runtime.basic_pf3_resource('Neutral'),target)
            self.assertEqual(build_standalone.audit(root),[])
            self.assertEqual(package.audit_tree(root),[])
            target.write_bytes(target.read_bytes()[:-1]+b'X')
            self.assertTrue(build_standalone.audit(root))
            self.assertTrue(package.audit_tree(root))
            with patch.object(runtime,'__file__',str(root/'canon_runtime.py')):
                with self.assertRaisesRegex(ValueError,'damaged'):runtime.basic_pf3_resource('Neutral')
            target.unlink()
            (basics/'extra.pf3').write_bytes(b'unapproved')
            self.assertTrue(build_standalone.audit(root))
            self.assertTrue(package.audit_tree(root))


if __name__=='__main__':unittest.main()
