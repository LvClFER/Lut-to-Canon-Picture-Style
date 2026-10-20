import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class IndependentInstallUiTests(unittest.TestCase):
    def test_frozen_main_dispatches_worker_before_qt_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'report.json'
            result=subprocess.run([sys.executable,'-S','canon_style_studio.py','--session-worker',
                '--device-id','NO_DEVICE_TEST','--allow-temporary-session','--request-descriptor',
                '--request-slot','3','--preflight-style',str(Path(temporary)/'missing.pf3'),
                '--output',str(output)],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0)
            report=json.loads(output.read_text())
            self.assertFalse(report['deviceOpenAttempted'])
            self.assertFalse(report['styleRegistrationAttempted'])
            self.assertNotIn('PySide6',result.stderr)

    def test_ui_requires_consent_snapshots_state_and_exports_without_canon(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication,QMessageBox
            from camera_install.ui import IndependentInstallDialog
        except ImportError:
            self.skipTest('Qt unavailable')
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);base=root/'owned.pf3';base.write_bytes(b'owned')
            main=SimpleNamespace(base_resolution=dict(path=base),luts=[],
                controls_dict=Mock(return_value=dict(contrast=2,saturation=-1,color_tone=3,
                    sharpness_override=True,sharp_strength=5,fineness=3,threshold=2)),
                project_document=Mock(return_value=SimpleNamespace(name='Original',edit={})),
                project_name=SimpleNamespace(text=lambda:'Aerochrome'),
                dll_path=Mock(side_effect=AssertionError('No Canon DLL lookup')))
            dialog=IndependentInstallDialog(main)
            try:
                self.assertEqual(dialog.devices.count(),0)
                self.assertFalse(dialog.install.isEnabled())
                dialog.devices_found([dict(canonCandidate=True,idFingerprint='0123456789abcdef',friendlyName='Canon EOS RP')])
                self.assertTrue(dialog.install.isEnabled())
                dialog.slot.setCurrentIndex(0)
                dialog.style_name.setText('Custom RP')
                styles=root/'styles';styles.mkdir()
                bundle=styles/'Aerochrome.canonstyleproject'
                with patch.object(dialog.pool,'start') as start, \
                        patch('camera_install.ui.QMessageBox.warning',return_value=QMessageBox.StandardButton.Yes) as approve, \
                        patch('camera_install.ui.style_export_path',return_value=bundle), \
                        patch('camera_install.ui.logs_dir',return_value=root/'logs'), \
                        patch('camera_install.ui.export_pf3') as export, \
                        patch('camera_install.ui.save_compiled_style_project',side_effect=lambda *args: bundle.write_bytes(b'compiled project')) as save, \
                        patch('camera_install.independent_session_diagnostic._run_isolated',
                            return_value=(dict(requestedSlotContentMatched=True,requestedSlot=1,
                                knownBasicControlChanges=[dict(control='Contrast',slotValue=0,candidateValue=2)],
                                requestedSlotStateMatched=True,
                                temporaryModesCleanupCompleted=True,connectionCleanupCompleted=True),0)) as isolated, \
                        patch('camera_install.ui.QMessageBox.information') as success:
                    dialog.start_install()
                    start.assert_called_once()
                    self.assertTrue(dialog.busy)
                    main.controls_dict.side_effect=AssertionError('Worker read editor state')
                    main.project_document.side_effect=AssertionError('Worker read editor state')
                    prepared=dialog.worker.function()
                    approve.assert_not_called()
                    isolated.assert_not_called()
                    self.assertTrue(bundle.is_file())
                    self.assertIsNone(export.call_args.args[0])
                    self.assertIsNone(save.call_args.args[0])
                    self.assertEqual(export.call_args.args[1],base)
                    controls=export.call_args.args[4]
                    self.assertEqual(controls['contrast'],2)
                    self.assertEqual(controls['sharp_strength'],5)
                    self.assertTrue(controls['sharpness_override'])
                    self.assertEqual(export.call_args.args[5],'Custom RP')
                    saved=save.call_args.args[3]
                    self.assertEqual(saved.name,'Custom RP')
                    self.assertEqual(saved.edit['color_tone'],3)
                    self.assertEqual(saved.edit['threshold'],2)
                    self.assertEqual(main.project_document.return_value.edit,{})
                    self.assertNotEqual(export.call_args.args[2].parent,styles)
                    self.assertEqual(list(styles.iterdir()),[bundle])
                    dialog.installation_prepared(prepared)
                    self.assertEqual(start.call_count,2)
                    self.assertIn(str(bundle),approve.call_args.args[2])
                    result=dialog.worker.function()
                    request=isolated.call_args.args[0]
                    self.assertTrue(request.experimental_register)
                    self.assertFalse(request.update_known_basic_controls)
                    self.assertIn('must match',approve.call_args.args[2])
                    self.assertEqual(request.request_slot,1)
                    self.assertEqual(request.device_fingerprint,'0123456789abcdef')
                    self.assertEqual(request.preflight_style,bundle)
                    self.assertTrue(request.baseline_backup.is_relative_to(root/'logs'))
                    dialog.installation_finished(result)
                    self.assertFalse(dialog.busy)
                    self.assertFalse(dialog.install.isEnabled())
                    self.assertTrue((Path(result['folder'])/'INDEPENDENT_INSTALL_REPORT.json').is_file())
                    success.assert_called_once()
                    self.assertIn('User Def. 1',success.call_args.args[2])
                    self.assertIn('Custom RP',success.call_args.args[2])
                    self.assertIn('Canon EOS RP',success.call_args.args[2])
                    self.assertIn('Basic controls were also confirmed',success.call_args.args[2])
                main.dll_path.assert_not_called()
            finally:
                dialog.set_busy(False);dialog.close();dialog.deleteLater();app.processEvents()

    def test_main_send_opens_independent_form_without_base_or_dll_resolution(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication
            import canon_style_studio as editor
            from camera_install.ui import IndependentInstallDialog
        except ImportError:self.skipTest('Qt unavailable')
        self.assertIs(editor.CameraInstallDialog,IndependentInstallDialog)
        main=SimpleNamespace(current_base_path=Mock(side_effect=AssertionError('Canon resolution forbidden')))
        with patch.object(editor,'CameraInstallDialog') as dialog:
            editor.CanonStyleStudioQt.open_camera_install(main)
            dialog.assert_called_once_with(main,main)
            dialog.return_value.exec.assert_called_once()
        main.current_base_path.assert_not_called()

    def test_send_uses_latest_editor_settings_without_duplicate_controls(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication
            from camera_install.ui import IndependentInstallDialog
        except ImportError:self.skipTest('Qt unavailable')
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);base=root/'owned.pf3';base.write_bytes(b'owned')
            values=dict(contrast=0,creative={'color_chrome':'Strong'})
            main=SimpleNamespace(base_resolution=dict(path=base),luts=[],
                base_combo=SimpleNamespace(currentText=lambda:'Portrait'),
                controls_dict=lambda:values,
                project_document=lambda **_:SimpleNamespace(name='Original',edit={}),
                project_name=SimpleNamespace(text=lambda:'Style'))
            dialog=IndependentInstallDialog(main)
            try:
                self.assertFalse(hasattr(dialog,'basic_fields'))
                self.assertFalse(hasattr(dialog,'base_style'))
                self.assertFalse(hasattr(dialog,'sharpness_override'))
                values.update(contrast=3,sharpness_override=False,sharp_strength=4)
                dialog.devices_found([dict(canonCandidate=True,idFingerprint='device',friendlyName='RP')])
                with patch.object(dialog.pool,'start'), \
                     patch('canon_engine.ensure_runtime_base_pf3',side_effect=AssertionError('Existing base must be reused')), \
                     patch('camera_install.ui.style_export_path',return_value=root/'style.canonstyleproject'), \
                     patch('camera_install.ui.logs_dir',return_value=root/'logs'), \
                     patch('camera_install.ui.export_pf3') as export, \
                     patch('camera_install.ui.save_compiled_style_project') as save:
                    dialog.start_install()
                    values['creative']['color_chrome']='Off'
                    dialog.worker.function()
                    self.assertIsNone(export.call_args.args[0])
                    self.assertEqual(export.call_args.args[1],base)
                    self.assertEqual(export.call_args.args[4]['contrast'],3)
                    self.assertFalse(export.call_args.args[4]['sharpness_override'])
                    self.assertEqual(export.call_args.args[4]['creative']['color_chrome'],'Strong')
                    self.assertEqual(save.call_args.args[3].edit['basePictureStyle'],'Portrait')
                    self.assertEqual(save.call_args.args[3].edit['base_path'],str(base))
                    self.assertEqual(save.call_args.args[3].edit['sharp_strength'],4)
            finally:
                dialog.set_busy(False);dialog.close();dialog.deleteLater();app.processEvents()

    def test_no_success_confirmation_without_readback_and_complete_cleanup(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication
            from camera_install.ui import IndependentInstallDialog
        except ImportError:self.skipTest('Qt unavailable')
        app=QApplication.instance() or QApplication([])
        good=dict(requestedSlotContentMatched=True,requestedSlot=3,
            temporaryModesCleanupCompleted=True,connectionCleanupCompleted=True)
        for change,code in ((dict(requestedSlotContentMatched=False),0),
                (dict(temporaryModesCleanupCompleted=False),0),
                (dict(connectionCleanupCompleted=None),0),(dict(requestedSlot=2),0),
                (dict(knownBasicControlChanges=[dict(control='Contrast')]),0),
                (dict(knownBasicControlChanges=[dict(control='Contrast')],requestedSlotStateMatched=False),0),
                (dict(knownBasicControlChanges='invalid'),0),
                (dict(failed=True),0),(dict(recoveryRequired=True),0),({},124)):
            with self.subTest(change=change,code=code):
                dialog=IndependentInstallDialog(SimpleNamespace())
                try:
                    with patch('camera_install.ui.QMessageBox.information') as success:
                        dialog.installation_finished(dict(report={**good,**change},code=code,
                            slot=3,device_name='RP',style_name='Style',bundle='Style.canonstyleproject',folder='logs'))
                        success.assert_not_called()
                    self.assertIn('not confirmed',dialog.camera_status.text())
                    self.assertTrue(dialog.details.isChecked())
                finally:
                    dialog.close();dialog.deleteLater();app.processEvents()

    def test_declining_prepared_style_keeps_saved_file_without_launching_camera_worker(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PySide6.QtWidgets import QApplication,QMessageBox
            from camera_install.ui import IndependentInstallDialog
        except ImportError:self.skipTest('Qt unavailable')
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temporary:
            bundle=Path(temporary)/'saved.canonstyleproject';bundle.write_bytes(b'saved')
            dialog=IndependentInstallDialog(SimpleNamespace())
            try:
                dialog.set_busy(True)
                with patch('camera_install.ui.QMessageBox.warning',return_value=QMessageBox.StandardButton.No), \
                     patch.object(dialog.pool,'start') as start:
                    dialog.installation_prepared(dict(args=SimpleNamespace(request_slot=3),
                        bundle=str(bundle),folder=str(Path(temporary)/'logs'),device_name='RP'))
                    start.assert_not_called()
                self.assertFalse(dialog.busy)
                self.assertEqual(bundle.read_bytes(),b'saved')
            finally:
                dialog.set_busy(False);dialog.close();dialog.deleteLater();app.processEvents()


if __name__=='__main__':unittest.main()
