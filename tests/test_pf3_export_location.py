import ctypes
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canon_runtime import documents_dir, exported_styles_dir, style_export_path


class ExportLocationTests(unittest.TestCase):
    def test_flat_documents_folder_safe_names_and_existing_exports_survive(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('canon_runtime.documents_dir', return_value=Path(directory)):
            folder = exported_styles_dir()
            self.assertEqual(folder, Path(directory) / 'Canon Style Studio PF3')
            original = style_export_path('Classic Cuban')
            original.write_bytes(b'original')
            self.assertEqual(style_export_path('Classic Cuban').name, 'Classic Cuban (2).canonstyleproject')
            for name in ('folder/style', '..\\outside', 'CON', 'name.with.dots', ' . '):
                path = style_export_path(name, '.pf3')
                self.assertEqual(path.parent, folder)
                self.assertEqual(path.suffix, '.pf3')
            self.assertEqual(original.read_bytes(), b'original')
            self.assertFalse(any(path.is_dir() for path in folder.iterdir()))

    @unittest.skipUnless(os.name == 'nt', 'Windows redirected Documents folder')
    def test_documents_uses_windows_folder_redirection(self):
        def redirected(_window, folder_id, _token, _flags, buffer):
            self.assertEqual(folder_id, 5)
            buffer.value = r'C:\Redirected\Documents'
            return 0
        with patch.object(ctypes.windll.shell32, 'SHGetFolderPathW', side_effect=redirected):
            self.assertEqual(documents_dir(), Path(r'C:\Redirected\Documents'))


if __name__ == '__main__':
    unittest.main()
