import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from mobile_camera import install


class MobileCameraTests(unittest.TestCase):
    def test_source_validation_precedes_usb_and_session_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            owner = Mock(unusable=False)
            owner.execute.side_effect = lambda *args: calls.append(args)
            with patch('camera_install.rp_preflight_reference.load_preflight_source', return_value=('source',)) as preflight, \
                 patch('camera_install.android_ptp.Transactions', return_value=owner) as transactions, \
                 patch('camera_install.independent_registration_reference.register_open_connection', return_value={'verified':True}) as register:
                transactions.side_effect = lambda *a, **k: (self.assertTrue(preflight.called) or owner)
                report = json.loads(install(object(), 'input.pf3', 2, str(Path(folder)/'backup.bin')))
            self.assertEqual(calls, [(0x1002, (1,)), (0x1003,)])
            self.assertEqual(register.call_args.kwargs['slot'], 2)
            self.assertTrue(report['ptpSessionClosed'])
            self.assertTrue(owner.unusable)

    def test_registration_failure_is_never_reported_as_success(self):
        with tempfile.TemporaryDirectory() as folder:
            owner = Mock(unusable=False)
            with patch('camera_install.rp_preflight_reference.load_preflight_source', return_value=('source',)), \
                 patch('camera_install.android_ptp.Transactions', return_value=owner), \
                 patch('camera_install.independent_registration_reference.register_open_connection', side_effect=ValueError('readback mismatch')):
                with self.assertRaisesRegex(ValueError,'readback mismatch'):
                    install(object(), 'input.pf3', 2, str(Path(folder)/'backup.bin'))
            self.assertEqual(owner.execute.call_args.args, (0x1003,))

    def test_bad_source_never_creates_usb_transactions(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('camera_install.rp_preflight_reference.load_preflight_source', side_effect=ValueError('bad source')), \
                 patch('camera_install.android_ptp.Transactions') as transactions:
                with self.assertRaisesRegex(ValueError,'bad source'):
                    install(object(), 'input.pf3', 2, str(Path(folder)/'backup.bin'))
                transactions.assert_not_called()


if __name__ == '__main__':
    unittest.main()
