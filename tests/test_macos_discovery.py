import unittest
import json
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess
from unittest.mock import Mock,patch
from camera_install import macos_discovery as discovery


class MacDiscoveryTests(unittest.TestCase):
    def test_selected_camera_is_unique_and_keeps_discovery_alive(self):
        device=Mock();device.UUIDString.return_value='selected'
        device.usbVendorID.return_value=0x04a9;device.usbProductID.return_value=123
        fingerprint=discovery.summarize_device(device)['idFingerprint']
        lifecycle=[]
        @contextmanager
        def scan():
            lifecycle.append('start')
            try:yield [device]
            finally:lifecycle.append('stop')
        with patch.object(discovery,'_discovered_cameras',side_effect=scan):
            with discovery.selected_camera(fingerprint) as selected:
                self.assertIs(selected,device)
                self.assertEqual(lifecycle,['start'])
        self.assertEqual(lifecycle,['start','stop'])
        device.requestOpenSession.assert_not_called()

    def test_missing_duplicate_and_noncanon_selection_never_resolves(self):
        device=Mock();device.UUIDString.return_value='selected'
        device.usbVendorID.return_value=0x04a9;device.usbProductID.return_value=123
        fingerprint=discovery.summarize_device(device)['idFingerprint']
        for devices in ([],[device,device]):
            @contextmanager
            def scan():yield devices
            with patch.object(discovery,'_discovered_cameras',side_effect=scan),self.assertRaises(RuntimeError):
                with discovery.selected_camera(fingerprint):self.fail('resolved')
        device.usbVendorID.return_value=0x04b0
        @contextmanager
        def scan():yield [device]
        with patch.object(discovery,'_discovered_cameras',side_effect=scan),self.assertRaises(RuntimeError):
            with discovery.selected_camera(fingerprint):self.fail('resolved non-Canon')

    def test_summary_uses_vendor_not_model_and_keeps_uuid_private(self):
        device=Mock()
        device.UUIDString.return_value='private-camera-id'
        device.name.return_value='Unlisted Canon model'
        device.usbVendorID.return_value=0x04a9;device.usbProductID.return_value=123
        result=discovery.summarize_device(device)
        self.assertTrue(result['canonCandidate'])
        self.assertFalse(result['deviceOpenAttempted'])
        self.assertEqual(len(result['idFingerprint']),16)
        self.assertNotIn('private-camera-id',str(result))
        device.requestOpenSession.assert_not_called()
        device.usbVendorID.return_value=0x04b0
        self.assertFalse(discovery.summarize_device(device)['canonCandidate'])

    def test_invalid_identity_is_rejected(self):
        device=Mock()
        for identifier in (None,'',42,'a'*4097):
            device.UUIDString.return_value=identifier
            with self.subTest(identifier=str(identifier)[:20]),self.assertRaises(ValueError):
                discovery.summarize_device(device)

    def test_windows_never_imports_native_frameworks(self):
        with patch.object(discovery.sys,'platform','win32'):
            with self.assertRaisesRegex(RuntimeError,'requires macOS'):discovery.enumerate_cameras()

    def test_scan_completion_and_timeout_both_stop_the_browser(self):
        for completes in (True,False):
            with self.subTest(completes=completes):
                delegate=Mock();browser=Mock();browser.devices.return_value=[]
                bridge=Mock();bridge.lookUpClass.return_value.alloc.return_value.init.return_value=delegate
                capture=Mock(ICDeviceTypeMaskCamera=1,ICDeviceLocationTypeMaskLocal=256)
                capture.ICDeviceBrowser.alloc.return_value.init.return_value=browser
                if completes:browser.start.side_effect=lambda:setattr(delegate,'finished',True)
                with patch.object(discovery.sys,'platform','darwin'), \
                        patch.dict('sys.modules',{'objc':bridge,'Foundation':Mock(),'ImageCaptureCore':capture}), \
                        patch.object(discovery.time,'monotonic',side_effect=[0,4]):
                    if completes:self.assertEqual(discovery.enumerate_cameras(),[])
                    else:
                        with self.assertRaises(TimeoutError):discovery.enumerate_cameras()
                browser.stop.assert_called_once()
                self.assertIsNone(browser.setDelegate_.call_args.args[0])
                browser.requestOpenSession.assert_not_called()

    def test_isolated_scan_returns_report_and_does_not_retry_timeout(self):
        def worker(command,**kwargs):
            Path(command[-1]).write_text('[]',encoding='utf-8')
            self.assertEqual(kwargs['timeout'],8)
            self.assertIn('--mac-discovery-worker',command)
        with patch.object(discovery.sys,'platform','darwin'), \
                patch.object(discovery.subprocess,'run',side_effect=worker) as run:
            self.assertEqual(discovery.enumerate_isolated(),[])
            run.assert_called_once()
        with patch.object(discovery.sys,'platform','darwin'), \
                patch.object(discovery.subprocess,'run',side_effect=subprocess.TimeoutExpired('scan',8)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):discovery.enumerate_isolated()
            run.assert_called_once()

    def test_isolated_scan_rejects_corrupt_report(self):
        def worker(command,**kwargs):
            Path(command[-1]).write_text(json.dumps([{'canonCandidate':True}]),encoding='utf-8')
        with patch.object(discovery.sys,'platform','darwin'), \
                patch.object(discovery.subprocess,'run',side_effect=worker):
            with self.assertRaisesRegex(ValueError,'identity'):discovery.enumerate_isolated()

    def test_mac_dialog_uses_isolated_discovery_without_enabling_wpd_install(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from types import SimpleNamespace
        from camera_install import ui
        app=QApplication.instance() or QApplication([])
        with patch.object(ui.sys,'platform','darwin'):
            dialog=ui.IndependentInstallDialog(SimpleNamespace())
            try:
                with patch.object(dialog.pool,'start'),patch.object(discovery,'enumerate_isolated',return_value=[]) as scan:
                    dialog.find_devices()
                    self.assertEqual(dialog.worker.function(),[])
                    scan.assert_called_once()
                dialog.devices_found([dict(canonCandidate=True,idFingerprint='0123456789abcdef',name='Canon new model')])
                self.assertEqual(dialog.devices.currentText(),'Canon new model')
                self.assertFalse(dialog.install.isEnabled())
                self.assertIn('under development',dialog.camera_status.text())
                with patch.object(ui,'export_pf3') as export:
                    dialog.start_install();export.assert_not_called()
            finally:dialog.close();dialog.deleteLater();app.processEvents()


if __name__=='__main__':unittest.main()
