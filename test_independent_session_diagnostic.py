import json
import struct
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from camera_install.independent_session_diagnostic import inspect_open_connection
from camera_install.wpd_data_phase_reference import COMMON, MTP


class SessionDiagnosticTests(unittest.TestCase):
    def test_fingerprint_selection_never_guesses_or_opens_a_device(self):
        from camera_install.independent_session_diagnostic import resolve_fingerprint
        fingerprint = '0123456789abcdef'
        def discover(**kwargs):
            kwargs['_on_device']('PRIVATE_USB_ID', dict(canonCandidate=True, idFingerprint=fingerprint))
            return []
        with patch('camera_install.independent_session_diagnostic.enumerate_portable_devices', side_effect=discover), \
             patch('camera_install.independent_session_diagnostic.WpdConnection') as connection:
            self.assertEqual(resolve_fingerprint(fingerprint), 'PRIVATE_USB_ID')
            with self.assertRaises(RuntimeError):
                resolve_fingerprint('fedcba9876543210')
            connection.assert_not_called()
        with patch('camera_install.independent_session_diagnostic.enumerate_portable_devices') as discovery:
            for invalid in ('', 'A'*16, 'g'*16, None):
                with self.assertRaises(ValueError):
                    resolve_fingerprint(invalid)
            discovery.assert_not_called()

    def test_standalone_entry_help_without_site_packages_or_device_access(self):
        root = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, '-S', str(root / 'independent_camera_diagnostic.py'), '--help'],
            cwd=root, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--allow-temporary-session', result.stdout)
        self.assertIn('--device-id', result.stdout)

    def test_import_does_not_load_editor_or_native_compiler_dependencies(self):
        root = Path(__file__).resolve().parent
        script = """
import sys
import independent_camera_diagnostic
for name in sys.modules:
    assert name.split('.')[0] not in ('numpy', 'frida', 'PySide6'), name
    assert name not in ('camera_install.compiler_regression',
                        'camera_install.virtual_compatibility'), name
"""
        result = subprocess.run([sys.executable, '-S', '-c', script], cwd=root,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def connection(self, codes=(0x9114, 0x9115, 0x9116)):
        descriptor = b'PRIVATE_DESCRIPTOR_DO_NOT_EXPORT'
        values = ((0xd116, struct.pack('<I', 0x33040080)),
                  (0xd17f, struct.pack('<I', len(descriptor)+4)+descriptor),
                  (0xd163, struct.pack('<III', 44, 1, 0x41)+bytes(range(32))))
        body = b''.join(struct.pack('<III', len(value)+12, 0xc189, code)+value
                        for code, value in values) + struct.pack('<II', 8, 0)
        calls = []
        def command(request):
            calls.append(('command', request[(MTP, 1001)], request[(MTP, 1002)]))
            return {(COMMON, 1003): 0, (MTP, 1003): 0x2001, (MTP, 1004): ()}
        def data(request):
            stage = request[(COMMON, 1002)]
            calls.append(('data', stage))
            if stage == 13:
                self.assertEqual(request[(MTP, 1001)], 0x9116)
                return {(COMMON, 1003): 0, (MTP, 1006): 'fake', (MTP, 1007): len(body)}
            if stage == 15:
                return {(COMMON, 1003): 0, (MTP, 1012): body, (MTP, 1009): len(body)}
            self.assertEqual(stage, 17)
            return {(COMMON, 1003): 0, (MTP, 1003): 0x2001, (MTP, 1004): ()}
        connection = Mock()
        connection.commands.side_effect = command
        connection.data.side_effect = data
        connection.capabilities.return_value = {(COMMON, 1003): 0, (MTP, 1005): codes}
        return connection, calls

    def test_session_report_omits_state_and_descriptor_bytes(self):
        connection, calls = self.connection()
        report = inspect_open_connection(connection)
        self.assertEqual(report['cameraId'], '0x33040080')
        self.assertEqual(report['observedSlotHandlers'], ['0x21'])
        self.assertTrue(report['temporaryModesCleanupCompleted'])
        self.assertFalse(report['stateFreshnessEstablished'])
        self.assertFalse(report['styleRegistrationAttempted'])
        self.assertNotIn('PRIVATE_DESCRIPTOR', json.dumps(report))
        self.assertNotIn(bytes(range(32)).hex(), json.dumps(report))
        self.assertEqual(calls, [('command', 0x9114, (1,)),
                                ('command', 0x9115, (1,)),
                                ('data', 13), ('data', 15), ('data', 17),
                                ('command', 0x9115, (0,)), ('command', 0x9114, (0,))])

    def test_missing_capabilities_abort_before_mode_commands(self):
        for codes in ((), (0x9114, 0x9115), [0x9114, 0x9115, 0x9116]):
            connection, calls = self.connection(codes)
            with self.assertRaises(RuntimeError):
                inspect_open_connection(connection)
            self.assertEqual(calls, [])

    def test_cli_without_explicit_consent_never_constructs_connection(self):
        from camera_install.independent_session_diagnostic import main
        with patch('sys.argv', ['diagnostic', '--device-id', 'fake', '--output', 'unused.json']), \
             patch('camera_install.independent_session_diagnostic.WpdConnection') as connection, \
             patch('argparse.ArgumentParser.error', side_effect=ValueError('consent')):
            with self.assertRaisesRegex(ValueError, 'consent'):
                main()
            connection.assert_not_called()
