import os
import struct
import shutil
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import canon_engine as engine
from camera_install.pf3_source_reference import read_source_fields, write_source_fields


class IndependentEditorTests(unittest.TestCase):
    def test_self_bootstrap_needs_neither_cache_access_nor_neighbor_search(self):
        with patch('canon_engine.runtime_cache_dir', side_effect=PermissionError('cache unavailable')) as cache, \
             patch.object(Path, 'glob', side_effect=AssertionError('unrelated directory search')) as search:
            recovered, fields = engine._independent_pf3_input(self.reference)
        self.assertEqual(fields[0x1070], (3, engine.identity_canon_table()))
        self.assertEqual(read_source_fields(self.reference.read_bytes(), recovered), fields)
        cache.assert_not_called()
        search.assert_not_called()
        self.native.assert_not_called()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = self.root / 'cache'
        self.bases = self.cache / 'generated_pf3_bases'
        self.bases.mkdir(parents=True)
        self.keys = (bytes(range(256)) * 2, bytes(range(256)) * 2 + b'X')
        # A synthetic calibration containing only a known mathematical identity.
        self.reference = self.bases / 'reference.pf3'
        self.reference.write_bytes(write_source_fields({0x1070: (3, engine.identity_canon_table())}, self.keys))
        self.addCleanup(patch.stopall)
        patch('canon_engine.basic_pf3_resource',return_value=None).start()
        patch('canon_engine.runtime_cache_dir', return_value=self.cache).start()
        self.native = patch('canon_engine.EdsCFParse', side_effect=AssertionError('Canon runtime forbidden')).start()

    def test_generates_all_bases_from_properties_using_only_one_cipher_reference(self):
        for style in engine.PICTURE_STYLE_IDS:
            with self.subTest(style=style):
                path = engine.ensure_runtime_base_pf3(None, style)
                fields = read_source_fields(path.read_bytes(), self.keys)
                self.assertEqual(len(path.read_bytes()), 434511)
                self.assertEqual(fields[0x1009], (3, struct.pack('<H', engine.PICTURE_STYLE_IDS[style])))
                self.assertEqual(engine.read_base_properties(None, path), engine.generated_pf3_properties(style, style))
                self.assertEqual(engine.resolve_independent_base_pf3(style)['path'], path)
        self.native.assert_not_called()

    def test_owned_nonidentity_style_generates_fresh_bases_without_a_prior_cache(self):
        fields=engine._generated_pf3_fields('Neutral')
        words=struct.unpack('<107814H',fields[0x1070][1])
        table=struct.pack('<107814H',*words[:3],*(4095-v for v in words[3:]))
        fields[0x1070]=fields[0x1071]=(3,table)
        owned=self.root/'owned.pf3';owned.write_bytes(write_source_fields(fields,self.keys))
        original=owned.read_bytes()
        with patch('canon_engine.runtime_cache_dir',return_value=self.root/'fresh-cache'):
            self.assertIsNone(engine.resolve_independent_base_pf3('Portrait'))
            for style in engine.PICTURE_STYLE_IDS:
                result=engine.resolve_independent_base_pf3(style,cipher_reference=owned)
                created=read_source_fields(result['path'].read_bytes(),self.keys)
                self.assertEqual(created,engine._generated_pf3_fields(style))
                self.assertNotEqual(created[0x1070],fields[0x1070])
        self.assertEqual(owned.read_bytes(),original)
        self.native.assert_not_called()

    def test_independent_resolution_regenerates_stale_zero_matrix_cache(self):
        fields=engine._generated_pf3_fields('Portrait')
        fields[0x1021]=(4,bytes(240))
        stale=self.bases/'portrait.pf3'
        stale.write_bytes(write_source_fields(fields,self.keys))
        result=engine.resolve_independent_base_pf3('Portrait')
        self.assertEqual(result['path'],stale)
        self.assertEqual(read_source_fields(stale.read_bytes(),self.keys),engine._generated_pf3_fields('Portrait'))
        self.native.assert_not_called()

    def test_editor_can_change_base_after_opening_a_portable_project_with_empty_cache(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:self.skipTest('Qt unavailable')
        from canon_style_studio import CanonStyleStudioQt
        from project_state import ProjectDocument
        app=QApplication.instance() or QApplication([])
        source=self.root/'portable-base.pf3'
        source.write_bytes(write_source_fields(engine._generated_pf3_fields('Neutral'),self.keys))
        project=ProjectDocument(edit=dict(base_name='Imported PF3',basePictureStyle='Imported PF3',
            base_path=str(source),custom_pf3=str(source),luts=[]))
        bundle=self.root/'portable.canonstyleproject'
        engine.save_compiled_style_project(None,source,bundle,project,source)
        source.unlink()
        with patch.dict(os.environ,{'CANON_STYLE_STUDIO_PORTABLE_ROOT':str(self.root)}), \
             patch('canon_engine.runtime_cache_dir',return_value=self.root/'empty-cache'), \
             patch('canon_style_studio.discover_pse',return_value=None), \
             patch('canon_style_studio.find_dll',return_value=None):
            window=CanonStyleStudioQt()
            try:
                window.open_project(bundle)
                window.base_combo.setCurrentText('Portrait')
                created=window.resolve_current_base()
                self.assertTrue(created['independent'])
                self.assertEqual(read_source_fields(created['path'].read_bytes(),self.keys),engine._generated_pf3_fields('Portrait'))
            finally:
                window.engine_pool.waitForDone(15000)
                window.dirty=False;window.close();app.processEvents()
        self.native.assert_not_called()

    def test_export_encodes_controls_and_lut_then_reopens_without_canon(self):
        source = engine.ensure_runtime_base_pf3(None, 'Neutral')
        original = source.read_bytes()
        output = self.root / 'changed.pf3'
        cube = dict(size=2, domain_min=[0, 0, 0], domain_max=[1, 1, 1],
                    values=[value for b in (0, 1) for g in (0, 1) for r in (0, 1)
                            for value in (1-r, 1-g, 1-b)])
        controls = dict(contrast=-3, saturation=2, color_tone=-1,
                        sharpness_override=True, sharp_strength=5, fineness=3, threshold=4)
        size, _digest = engine.export_pf3(None, source, output,
            [dict(cube=cube, enabled=True, opacity=1)], controls, 'Own style')
        reopened = engine.inspect_pf3(None, output)
        self.assertEqual(size, 434511)
        self.assertEqual(reopened['title'], 'Own style')
        fields = read_source_fields(output.read_bytes(), self.keys)
        self.assertEqual(fields[0x1031][1], struct.pack('<i', -3))
        self.assertEqual(fields[0x1032][1], struct.pack('<i', 2))
        self.assertEqual(fields[0x1033][1], struct.pack('<i', -1))
        for table in (reopened['table'], reopened['table70']):
            self.assertEqual(struct.unpack_from('<HHH', table, 6), (4095, 4095, 4095))
            self.assertEqual(struct.unpack_from('<HHH', table, len(table)-6), (0, 0, 0))
        self.assertEqual(source.read_bytes(), original)
        isolated = self.root / 'isolated'
        isolated.mkdir()
        single_file = isolated / 'only.pf3'
        single_file.write_bytes(output.read_bytes())
        with patch('canon_engine.runtime_cache_dir', return_value=self.root / 'empty-cache'):
            self.assertEqual(engine.inspect_pf3(None, single_file)['title'], 'Own style')
        self.native.assert_not_called()

    def test_old_reference_bank_survives_edit_and_portable_project(self):
        from project_state import ProjectDocument, load_project
        source = engine.ensure_runtime_base_pf3(None, 'Neutral')
        fields = dict(read_source_fields(source.read_bytes(), self.keys))
        fields[0x1002] = (2, b'Neutral\0' + bytes(range(24)))
        fields[0x9002] = (2, b'Reference title'.ljust(32, b'\0'))
        fields[0x9032] = (4, struct.pack('<i', -2))
        source.write_bytes(write_source_fields(fields, self.keys))
        noop = self.root / 'unchanged.pf3'
        original_controls = dict(engine.inspect_pf3(None, source)['basic'], sharpness_override=True)
        engine.export_pf3(None, source, noop, [], original_controls, 'Neutral')
        self.assertEqual(noop.read_bytes(), source.read_bytes())
        controls = dict(contrast=-3, saturation=2, color_tone=1)
        edit = dict(basePictureStyle='Imported PF3', base_name='Imported PF3',
                    base_path=str(source), custom_pf3=str(source), luts=[], **controls)
        project = ProjectDocument(name='Old style', edit=edit)
        bundle = self.root / 'Old style.canonstyleproject'
        engine.export_style_project(None, source, bundle, [], controls, 'Old style', project)
        source.unlink()
        self.reference.unlink()
        restored = load_project(bundle, extraction_root=self.root / 'reopened')
        compiled = Path(restored.renderedPf3)
        output = read_source_fields(compiled.read_bytes(), self.keys)
        self.assertEqual(len(compiled.read_bytes()), len(write_source_fields(fields, self.keys)))
        self.assertEqual(tuple(output), tuple(fields))
        self.assertEqual(output[0x1032], (4, struct.pack('<i', 2)))
        for identifier in (0x9002, 0x9032):
            self.assertEqual(output[identifier], fields[identifier])
        with patch('canon_engine.runtime_cache_dir', return_value=self.root / 'empty-cache'):
            self.assertEqual(engine.inspect_pf3(None, compiled)['title'], 'Old style')
        self.native.assert_not_called()

    def test_dense_compact_route_changes_only_the_selected_user_table(self):
        from camera_install.compact_carrier_reference import build_accepted_compact16752
        from camera_install.offline_registration_reference import prepare
        source = engine.ensure_runtime_base_pf3(None, 'Neutral')
        fields = dict(read_source_fields(source.read_bytes(), self.keys))
        self.assertEqual(fields[0x1061][1],struct.pack('<2I',2,0)+bytes(504))
        with patch('camera_install.compact_carrier_reference.compact_upstream_grid',
                   return_value=[[64.,64.,64.]]*1000):
            before = build_accepted_compact16752(fields, bytes(14796), self.keys,
                                                internal_selector=0x80000433)
            planned = prepare(source.read_bytes(),self.keys,route='compact16752-dense-pixel',
                internal_selector=0x80000433,normalized_descriptor=bytes(14796),
                handler_selector=0x23,supported_operations=(0x9110,))
            self.assertEqual(planned.carrier,before)
            self.assertEqual(planned.send.opcode,0x9110)
            self.assertEqual(planned.send.slot,3)
            with self.assertRaisesRegex(ValueError,'normalized modern descriptor'):
                prepare(source.read_bytes(),self.keys,route='compact16752-dense-pixel',
                    internal_selector=0x80000433,handler_selector=0x23,supported_operations=(0x9110,))
            kind, table = fields[0x1070]
            words = struct.unpack('<107814H', table)
            fields[0x1070] = (kind, struct.pack('<107814H',*words[:3],*(4095-v for v in words[3:])))
            after = build_accepted_compact16752(fields, bytes(14796), self.keys,
                                               internal_selector=0x80000433)
        self.assertEqual(len(after),16752)
        self.assertEqual(before[:368],after[:368])
        self.assertNotEqual(before[368:4464],after[368:4464])
        self.assertEqual(before[4464:],after[4464:])
        self.native.assert_not_called()

    def test_missing_calibration_and_failed_replace_preserve_existing_output(self):
        output = self.root / 'existing.pf3'
        output.write_bytes(b'existing user file')
        self.reference.unlink()
        with self.assertRaisesRegex(ValueError, 'cipher calibration'):
            engine.create_generated_base_pf3(None, output)
        self.assertEqual(output.read_bytes(), b'existing user file')
        self.reference.write_bytes(write_source_fields({0x1070: (3, engine.identity_canon_table())}, self.keys))
        with patch('canon_engine.os.replace', side_effect=OSError('replacement refused')):
            with self.assertRaisesRegex(OSError, 'replacement refused'):
                engine.create_generated_base_pf3(None, output)
        self.assertEqual(output.read_bytes(), b'existing user file')
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_one_file_preserves_base_luts_snapshots_and_compiled_pf3_after_originals_are_removed(self):
        from project_state import ProjectDocument, load_project
        source = engine.ensure_runtime_base_pf3(None, 'Neutral')
        lut = self.root / 'look.cube'
        lut.write_text('LUT_3D_SIZE 2\n' + '\n'.join(f'{1-r} {1-g} {1-b}'
            for b in (0, 1) for g in (0, 1) for r in (0, 1)), encoding='utf-8')
        controls = dict(contrast=-2, saturation=1, color_tone=2)
        edit = dict(base_name='Imported PF3', basePictureStyle='Imported PF3',
                    base_path=str(source), custom_pf3=str(source), **controls,
                    luts=[dict(id='look', path=str(lut), enabled=True, opacity=.75)])
        project = ProjectDocument(name='One file', edit=edit,
                                  snapshots={'A': dict(edit), 'B': None, 'C': None})
        output = self.root / 'One file.canonstyleproject'
        entry = dict(cube=engine.parse_lut_file(lut), enabled=True, opacity=.75)
        engine.export_style_project(None, source, output, [entry], controls, 'One file', project)
        self.assertTrue(zipfile.is_zipfile(output))
        source.unlink()
        lut.unlink()
        self.reference.unlink()
        restored = load_project(output, extraction_root=self.root / 'reopened')
        self.assertEqual(restored.edit['basePictureStyle'], 'Imported PF3')
        self.assertEqual(restored.edit['contrast'], -2)
        self.assertEqual(restored.edit['luts'][0]['opacity'], .75)
        self.assertEqual(restored.snapshots['A']['luts'], restored.edit['luts'])
        base = Path(restored.edit['custom_pf3'])
        reopened_lut = Path(restored.edit['luts'][0]['path'])
        compiled = Path(restored.renderedPf3)
        self.assertTrue(all(p.is_file() for p in (base, reopened_lut, compiled)))
        repeat = self.root / 'repeat.pf3'
        entry['cube'] = engine.parse_lut_file(reopened_lut)
        engine.export_pf3(None, base, repeat, [entry], controls, 'One file')
        self.assertEqual(repeat.read_bytes(), compiled.read_bytes())
        controls['contrast'] = 3
        engine.export_pf3(None, base, repeat, [entry], controls, 'One file')
        self.assertEqual(read_source_fields(repeat.read_bytes(), self.keys)[0x1031][1], struct.pack('<i', 3))
        imported = ProjectDocument(edit=dict(basePictureStyle='Imported PF3', base_name='Imported PF3',
                                             base_path=str(compiled), custom_pf3=str(compiled), luts=[]))
        own_bundle = self.root / 'Own.canonstyleproject'
        engine.save_compiled_style_project(None, compiled, own_bundle, imported, compiled)
        self.assertFalse(load_project(own_bundle, extraction_root=self.root / 'own').cipherReference)
        legacy_fields = dict(read_source_fields(compiled.read_bytes(), self.keys))
        kind, matrix = legacy_fields[0x1021]
        legacy_fields[0x1021] = (kind, bytes([matrix[0] ^ 1]) + matrix[1:])
        compiled.write_bytes(write_source_fields(legacy_fields, self.keys))
        standalone = self.root / 'Imported.canonstyleproject'
        engine.save_compiled_style_project(None, compiled, standalone, imported, compiled)
        shutil.rmtree(self.root / 'reopened')
        standalone_doc = load_project(standalone, extraction_root=self.root / 'standalone')
        self.assertTrue(Path(standalone_doc.cipherReference).is_file())
        self.assertEqual(engine.inspect_pf3(None, standalone_doc.edit['custom_pf3'])['title'], 'One file')
        self.native.assert_not_called()

    def test_existing_editor_exports_with_canon_discovery_and_parser_disabled(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        try:
            from PySide6.QtWidgets import QApplication
        except ModuleNotFoundError:
            self.skipTest('Editor UI test requires the application PySide6 dependency')
        from canon_style_studio import CanonStyleStudioQt, ExportDialog
        app = QApplication.instance() or QApplication([])
        with patch.dict(os.environ, {'CANON_STYLE_STUDIO_PORTABLE_ROOT': str(self.root)}), \
                patch('canon_runtime.documents_dir', return_value=self.root / 'Documents'), \
                patch('canon_style_studio.discover_pse', return_value=None), \
                patch('canon_style_studio.QMessageBox.critical', side_effect=AssertionError('Unexpected UI error')), \
                patch('canon_style_studio.find_dll', return_value=None):
            data = self.root / 'app_data'
            data.mkdir()
            (data / 'settings.json').write_text('{}', encoding='utf-8')
            window = CanonStyleStudioQt()
            dialog = None
            try:
                window.base_combo.setCurrentText('Portrait')
                self.assertTrue(window.resolve_current_base()['independent'])
                window.settings.data['last_export_folder'] = str(self.root / 'old' / 'nested' / 'folder')
                dialog = ExportDialog(window)
                self.assertEqual(Path(dialog.path.text()).parent, self.root / 'Documents' / 'Canon Style Studio PF3')
                output = self.root / 'FromEditor.canonstyleproject'
                dialog.path.setText(str(output))
                dialog.start_export()
                deadline = time.monotonic() + 15
                while not dialog.export.isEnabled() and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                self.assertTrue(dialog.open_folder.isEnabled(), dialog.log.toPlainText())
                from project_state import load_project
                document = load_project(output)
                compiled = Path(document.renderedPf3)
                self.assertEqual(engine.inspect_pf3(None, compiled)['title'], 'FromEditor')
                self.assertFalse(output.with_suffix('.manifest.json').exists())
                self.assertFalse(output.with_suffix('.canonstyle.json').exists())
                window.open_project(output)
                self.assertEqual(window.current_base_path(), Path(document.edit['base_path']))
                self.native.assert_not_called()
                from camera_install.ui import CameraInstallDialog
                camera_dialog = CameraInstallDialog(window)
                try:
                    window.base_resolution = dict(cameraReady=True)
                    with patch.object(camera_dialog, 'prepare_block_reasons', return_value=[]), \
                            patch.object(window, 'dll_path', return_value=Path('unused.dll')), \
                            patch.object(window, 'current_base_path', return_value=compiled), \
                            patch.object(camera_dialog.pool, 'start'), \
                            patch('camera_install.ui.EosRpInstaller') as installer, \
                            patch('camera_install.ui.export_pf3') as export:
                        def fake_export(_dll, _base, target, *_args, **_kwargs):
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(compiled, target)
                            return 434511, 'test-hash'
                        export.side_effect = fake_export
                        camera_dialog.start_prepare()
                        camera_dialog.worker.function()
                        self.assertEqual(export.call_args.args[2].parent.parent,
                                         self.root / 'app_data' / 'logs' / 'camera_install')
                        self.assertEqual(len(list((self.root / 'Documents' / 'Canon Style Studio PF3').iterdir())), 1)
                        self.assertEqual(installer.return_value.prepare_and_arm.call_args.args[3].parent,
                                         self.root / 'app_data' / 'logs' / 'camera_install')
                finally:
                    camera_dialog._shutdown(confirm=False)
                    camera_dialog.close()
            finally:
                window.engine_pool.waitForDone(15000)
                if dialog is not None:
                    dialog.close()
                window.dirty = False
                window.close()
                app.processEvents()


if __name__ == '__main__':
    unittest.main()
