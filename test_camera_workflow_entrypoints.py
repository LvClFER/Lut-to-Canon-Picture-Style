import os
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch


class CameraWorkflowEntrypointTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:self.skipTest('Qt unavailable')
        import canon_style_studio as studio
        self.studio=studio
        self.app=QApplication.instance() or QApplication([])
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        temporary=self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch.dict(os.environ,{'CANON_STYLE_STUDIO_PORTABLE_ROOT':temporary}))
        self.stack.enter_context(patch.object(studio,'discover_pse',return_value=None))
        self.stack.enter_context(patch.object(studio,'find_dll',return_value=None))
        self.stack.enter_context(patch.object(studio.QTimer,'singleShot'))
        self.window=studio.CanonStyleStudioQt()
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window.dirty=False
        self.window.close();self.window.deleteLater();self.app.processEvents()

    def test_default_click_is_independent_and_does_not_resolve_native_prerequisites(self):
        with patch.object(self.studio,'CameraInstallDialog') as independent, \
             patch.object(self.studio,'CanonNativeInstallDialog') as native, \
             patch.object(self.window,'current_base_path',side_effect=AssertionError('Native base lookup')), \
             patch.object(self.window,'dll_path',side_effect=AssertionError('Canon DLL lookup')):
            self.window.camera_btn.click()
            independent.assert_called_once_with(self.window,self.window)
            independent.return_value.exec.assert_called_once_with()
            native.assert_not_called()

    def test_optional_fallback_menu_reaches_native_dialog_only_after_explicit_selection(self):
        with patch.object(self.studio,'CameraInstallDialog') as independent, \
             patch.object(self.studio,'CanonNativeInstallDialog') as native, \
             patch.object(self.window,'current_base_path',return_value=Path('owned.pf3')) as base, \
             patch.object(self.window,'dll_path',return_value=Path('external.dll')) as dll:
            actions=self.window.camera_btn.menu().actions()
            self.assertIn('requires EOS Utility',actions[1].text())
            actions[1].trigger()
            base.assert_called_once_with();dll.assert_called_once_with()
            native.assert_called_once_with(self.window,self.window)
            native.return_value.exec.assert_called_once_with()
            independent.assert_not_called()

    def test_missing_canon_runtime_explains_fallback_failure_without_opening_a_dialog(self):
        with patch.object(self.studio,'CanonNativeInstallDialog') as native, \
             patch.object(self.window,'current_base_path',return_value=Path('owned.pf3')), \
             patch.object(self.window,'dll_path',side_effect=RuntimeError('Canon runtime missing')), \
             patch.object(self.studio.QMessageBox,'warning') as warning:
            self.window.camera_btn.menu().actions()[1].trigger()
            native.assert_not_called()
            self.assertEqual(warning.call_args.args[2],'Canon runtime missing')

    def test_test_report_separates_independent_and_native_physical_evidence(self):
        report=self.window.test_report_payload()['camera_install']
        self.assertFalse(report['canon_runtime_required'])
        self.assertEqual(report['physically_tested_bodies'],['EOS RP'])
        self.assertEqual(report['serializer_families'],10)
        self.assertEqual(report['known_model_identifiers'],77)
        fallback=report['canon_fallback']
        self.assertTrue(fallback['available'])
        self.assertTrue(fallback['canon_runtime_required'])
        self.assertEqual(fallback['physically_tested_bodies'],['EOS RP','EOS R8'])
        self.assertFalse(fallback['edsdk_payload_replaced'])
