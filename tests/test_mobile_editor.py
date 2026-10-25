import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from mobile_editor import Editor
from project_state import load_project


class MobileEditorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.environment = patch.dict(os.environ)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.editor = Editor(self.root / 'private')
        self.photo = self.root / 'portrait.png'
        Image.new('RGB', (40, 80), (100, 80, 60)).save(self.photo)

    def test_project_import_keeps_photos_and_selection(self):
        self.editor.open(self.photo)
        self.editor.update('{"contrast":2}')
        project = self.root / 'style.canonstyleproject'
        self.editor.export(project)
        self.editor.update('{"contrast":-1}')
        self.editor.open(project)
        self.assertEqual(self.editor.project.references, [str(self.photo)])
        self.assertEqual(self.editor.project.edit['contrast'], 2)
        self.assertEqual(self.editor.project.current_reference, 0)
        self.assertTrue(Path(load_project(project).renderedPf3).is_file())

    def test_portrait_render_preserves_ratio_and_exports_pf3(self):
        self.editor.open(self.photo)
        state = json.loads(self.editor.render())
        with Image.open(state['after']) as image:
            self.assertEqual(image.size, (40, 80))
        output = self.root / 'style.pf3'
        self.editor.export(output, project=False)
        self.assertEqual(output.stat().st_size, 434511)
        with self.assertRaises(ValueError):
            self.editor.export(output, project=False)

    def test_undo_redo_and_snapshots(self):
        self.editor.snapshot('A')
        self.editor.update('{"contrast":2,"raw_exposure":1.5}')
        self.editor.undo()
        self.assertEqual(self.editor.project.edit['contrast'], 0)

        self.editor.undo(True)
        self.assertEqual(self.editor.project.edit['contrast'], 2)
        self.editor.snapshot('A', True)
        self.assertEqual(self.editor.project.edit['contrast'], 0)

    def test_lut_reordering_is_undoable_and_rejects_invalid_moves(self):
        self.editor.project.edit['luts'] = [dict(path='first'), dict(path='second')]
        before = self.editor.state()
        for index, offset in ((0, -1), (1, 1), (0, 2), (True, 1)):
            with self.assertRaises(ValueError):
                self.editor.move_lut(index, offset)
            self.assertEqual(self.editor.state(), before)
        self.editor.move_lut(0, 1)
        self.assertEqual(self.editor.project.edit['luts'][0]['path'], 'second')
        self.editor.undo()
        self.assertEqual(self.editor.project.edit['luts'][0]['path'], 'first')

    def test_invalid_update_is_atomic(self):
        before = self.editor.state()
        for encoded in ('{"contrast":2,"raw_kelvin":1}', '{"contrast":1.5}', '{"contrast":NaN}', '{"unexpected":1}'):
            with self.assertRaises(ValueError):
                self.editor.update(encoded)
            self.assertEqual(self.editor.state(), before)

    def test_generated_cube_contains_grading_and_does_not_change_project(self):
        from canon_engine import parse_cube, CubeSampler
        self.editor.update('{"creative":{"grading":{"saturation":-100}}}')
        before = self.editor.state()
        output = self.root / 'generated.cube'
        self.editor.export_cube(output)
        cube = parse_cube(output)
        self.assertEqual(cube['size'], 33)
        rgb = CubeSampler(cube).sample(.75, .25, .125)
        self.assertLess(max(rgb)-min(rgb), .01)
        self.assertEqual(self.editor.state(), before)
        with self.assertRaises(ValueError):
            self.editor.export_cube(output)

    def test_undo_photo_import_clears_comparison(self):
        self.editor.open(self.photo)
        self.editor.render()
        self.editor.undo()
        state = json.loads(self.editor.render())
        self.assertEqual((state['before'], state['after'], state['decoder']), ('', '', ''))

    def test_private_session_restores_edits_and_images(self):
        self.editor.open(self.photo)
        self.editor.update('{"contrast":3}')
        self.editor.snapshot('B')
        self.editor.checkpoint()
        restored = Editor(self.root / 'private')
        self.assertEqual(restored.project.edit['contrast'], 3)
        self.assertEqual(restored.project.references, [str(self.photo)])
        self.assertEqual(restored.project.snapshots['B']['contrast'], 3)

    def test_np3_import_requires_profile_and_preserves_edit_on_failure(self):
        source = self.root / 'look.np3'
        source.write_bytes(b'invalid')
        before = self.editor.state()
        with self.assertRaisesRegex(ValueError, 'coefficient'):
            self.editor.open(source)
        self.assertEqual(self.editor.state(), before)
        (self.editor.root / 'nikon-prm.bin').write_bytes(b'invalid')
        with self.assertRaises(ValueError):
            self.editor.open(source)
        self.assertEqual(self.editor.state(), before)

    def test_np3_import_is_portable_and_keeps_photo(self):
        source = self.root / 'look.np3'
        source.write_bytes(b'fixture')
        (self.editor.root / 'nikon-prm.bin').write_bytes(b'fixture')
        cube = self.root / 'look.cube'
        cube.write_text('LUT_3D_SIZE 2\n' + '\n'.join(
            f'{r} {g} {b}' for b in (0, 1) for g in (0, 1) for r in (0, 1)), encoding='utf-8')
        self.editor.open(self.photo)
        asset = dict(cube=dict(path=cube), metadata=dict(conversionVersion='relative-flexible-v5'))
        with patch('nikon_import.convert_asset', return_value=asset) as convert:
            self.editor.open(source)
            convert.assert_called_once()
        project = self.root / 'np3.canonstyleproject'
        self.editor.export(project)
        cube.unlink()
        loaded = load_project(project, extraction_root=self.root / 'reopened')
        self.assertTrue(Path(loaded.edit['luts'][0]['path']).is_file())
        self.assertEqual(loaded.edit['luts'][0]['metadata'], asset['metadata'])
        self.assertEqual(self.editor.project.references, [str(self.photo)])
        self.editor.undo()
        self.assertEqual(self.editor.project.edit.get('luts', []), [])

    def test_invalid_profile_does_not_replace_previous_setup(self):
        profile = self.editor.root / 'nikon-prm.bin'
        profile.write_bytes(b'previous')
        source = self.root / 'prm.bin'
        source.write_bytes(b'invalid')
        with self.assertRaises(ValueError):
            self.editor.open(source, 'nikon_profile')
        self.assertEqual(profile.read_bytes(), b'previous')


if __name__ == '__main__':
    unittest.main()
