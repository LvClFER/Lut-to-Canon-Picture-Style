import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from android_raw import decode
from mobile_editor import Editor


class AndroidRawTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_native_sensor_pixels_and_white_balance_are_used(self):
        def develop(source, output, mode, exposure):
            self.assertEqual(mode, 1)
            self.assertEqual(exposure, -2.0)
            Image.new('RGB', (6, 10), (255, 0, 100)).save(output, format='PPM')
            return json.dumps(dict(width=6, height=10, embedded_preview_used=False))
        native = types.SimpleNamespace(develop=develop)
        with patch.dict('sys.modules', java=types.SimpleNamespace(jclass=lambda name:native)):
            image, metadata = decode(self.root / 'input.cr3', self.root, wb_mode='Auto', exposure=-2)
        self.assertEqual(image.size, (6, 10))
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 100))
        self.assertFalse(metadata['embedded_preview_used'])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_native_preview_or_bad_geometry_is_rejected(self):
        for embedded, width in ((True, 6), (False, 7)):
            def develop(source, output, mode, exposure):
                Image.new('RGB', (6, 10)).save(output, format='PPM')
                return json.dumps(dict(width=width, height=10, embedded_preview_used=embedded))
            with patch.dict('sys.modules', java=types.SimpleNamespace(jclass=lambda name:types.SimpleNamespace(develop=develop))):
                with self.assertRaises(ValueError):
                    decode('input.cr3', self.root)

    def test_raw_failure_cannot_fall_back_to_a_styled_jpeg(self):
        source = self.root / 'input.cr3'; source.write_bytes(b'raw fixture')
        with patch.dict(os.environ):
            editor = Editor(self.root / 'editor')
            with patch('android_raw.decode', side_effect=RuntimeError('unsupported RAW')), \
                 patch.object(editor.engine, 'load_reference_image') as thumbnail:
                with self.assertRaisesRegex(RuntimeError, 'unsupported RAW'):
                    editor.open(source)
                thumbnail.assert_not_called()
                self.assertEqual(editor.project.references, [])

    def test_control_changes_reuse_sensor_decode_but_white_balance_invalidates_it(self):
        source = self.root / 'input.cr3'; source.write_bytes(b'raw fixture')
        with patch.dict(os.environ):
            editor = Editor(self.root / 'editor')
            with patch('android_raw.decode', return_value=(Image.new('RGB', (6, 10)), dict(decoder='sensor', canon_base_render_verified=False))) as native:
                editor.open(source); editor.render()
                editor.update('{"contrast":2}'); editor.render()
                self.assertEqual(native.call_count, 1)
                editor.update('{"raw_wb_mode":"Auto"}'); editor.render()
                self.assertEqual(native.call_count, 2)
                self.assertIn('Canon base look not calibrated', editor.decoder)

    def test_exposure_is_developed_once_and_invalidates_raw_cache(self):
        source = self.root / 'input.cr3'; source.write_bytes(b'raw fixture')
        with patch.dict(os.environ):
            editor = Editor(self.root / 'editor')
            metadata = dict(decoder='sensor', sensor_exposure_applied=True)
            with patch('android_raw.decode', return_value=(Image.new('RGB', (6, 10)), metadata)) as native, \
                 patch.object(editor.renderer, 'render', return_value=(Image.new('RGB', (6, 10)), Image.new('RGB', (6, 10)))) as render:
                editor.open(source); editor.render()
                editor.update('{"raw_exposure":-2}'); editor.render()
                self.assertEqual(native.call_count, 2)
                self.assertEqual(native.call_args.kwargs['exposure'], -2)
                self.assertEqual(render.call_args.kwargs['raw_preview']['exposure'], 0)
                editor.render()
                self.assertEqual(native.call_count, 2)

    def test_invalid_exposure_is_rejected_before_native_access(self):
        for value in (True, float('nan'), float('inf'), -6, 6, '1'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Invalid RAW exposure'):
                decode('input.cr3', self.root, exposure=value)

    def test_ordinary_image_keeps_editor_exposure(self):
        source = self.root / 'input.png'; Image.new('RGB', (6, 10)).save(source)
        with patch.dict(os.environ):
            editor = Editor(self.root / 'editor'); editor.open(source)
            editor.update('{"raw_exposure":-2}')
            with patch.object(editor.renderer, 'render', return_value=(Image.new('RGB', (6, 10)), Image.new('RGB', (6, 10)))) as render:
                editor.render()
            self.assertEqual(render.call_args.kwargs['raw_preview']['exposure'], -2)


if __name__ == '__main__':
    unittest.main()
