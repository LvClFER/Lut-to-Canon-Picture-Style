import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import canon_runtime as runtime
import build_macos


class MacPortabilityTests(unittest.TestCase):
    def test_mac_writes_outside_the_app_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary)
            with patch('canon_runtime.sys.platform','darwin'),patch.dict(os.environ,{},clear=True), \
                    patch.object(Path,'home',return_value=home), \
                    patch('canon_runtime.application_root',side_effect=AssertionError('App bundle is read-only')):
                self.assertEqual(runtime.app_data_dir(),home/'Library/Application Support/CanonStyleStudio')
                self.assertEqual(runtime.cache_dir(),home/'Library/Caches/CanonStyleStudio')
                self.assertEqual(runtime.logs_dir().parent,runtime.app_data_dir())

    def test_portable_override_remains_available_on_mac_and_windows(self):
        with tempfile.TemporaryDirectory() as temporary:
            for system in ('darwin','win32'):
                with self.subTest(platform=system),patch('canon_runtime.sys.platform',system), \
                        patch.dict(os.environ,{'CANON_STYLE_STUDIO_PORTABLE_ROOT':temporary}):
                    self.assertEqual(runtime.app_data_dir(),Path(temporary).resolve()/'app_data')
                    self.assertEqual(runtime.cache_dir(),Path(temporary).resolve()/'app_data/cache')

    def test_windows_default_storage_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary,patch('canon_runtime.sys.platform','win32'), \
                patch('canon_runtime.application_root',return_value=Path(temporary)):
            self.assertEqual(runtime.app_data_dir(),Path(temporary)/'app_data')
            self.assertEqual(runtime.cache_dir(),Path(temporary)/'app_data/cache')

    def test_open_folder_uses_a_local_url_without_shell_interpolation(self):
        with patch('PySide6.QtGui.QDesktopServices.openUrl',return_value=True) as opener:
            runtime.open_local_path(Path.cwd()/'A folder & another')
            self.assertEqual(Path(opener.call_args.args[0].toLocalFile()),Path.cwd()/'A folder & another')
        with patch('PySide6.QtGui.QDesktopServices.openUrl',return_value=False):
            with self.assertRaises(OSError):runtime.open_local_path(Path.cwd())

    def test_mac_build_plan_includes_bases_and_explicit_architecture(self):
        for arch in build_macos.ARCHITECTURES:
            with self.subTest(arch=arch):
                worker,app=build_macos.commands(Path('local work'),arch)
                self.assertEqual(worker[worker.index('--target-arch')+1],arch)
                self.assertEqual(app[app.index('--target-arch')+1],arch)
                self.assertIn(str(build_macos.HERE/'basic_pf3')+':basic_pf3',app)
                self.assertIn(str(build_macos.HERE/'assets/canon-logo.png')+':assets',app)
                self.assertIn('--windowed',app)
                self.assertIn('camera_install.macos_ptp',app)
                self.assertFalse(any('upload' in value or 'publish' in value for value in worker+app))
        with self.assertRaises(ValueError):build_macos.commands(Path('work'),'i386')

    def test_build_refuses_to_emit_a_mac_app_on_windows(self):
        with patch('build_macos.sys.platform','win32'),patch('build_macos.subprocess.run') as run:
            with self.assertRaisesRegex(RuntimeError,'must be built on macOS'):
                build_macos.build(Path('unused'),'arm64')
            run.assert_not_called()

    def test_missing_native_bridge_fails_without_device_access(self):
        with patch.dict('sys.modules',{'ImageCaptureCore':None}):
            with self.assertRaisesRegex(RuntimeError,'completion APIs'):
                build_macos.require_native_camera_api()


if __name__=='__main__':unittest.main()
