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

    def test_invalid_update_is_atomic(self):
        before = self.editor.state()
        for encoded in ('{"contrast":2,"raw_kelvin":1}', '{"contrast":1.5}', '{"contrast":NaN}', '{"unexpected":1}'):
            with self.assertRaises(ValueError):
                self.editor.update(encoded)
            self.assertEqual(self.editor.state(), before)

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


if __name__ == '__main__':
    unittest.main()
