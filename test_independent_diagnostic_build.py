from pathlib import Path
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from build_independent_diagnostic import audit_bundle


class DiagnosticBuildTests(unittest.TestCase):
    def test_audit_checks_preflight_help_and_rejects_resources_or_unknown_dlls(self):
        reader = ModuleType('PyInstaller.archive.readers')
        reader.CArchiveReader = Mock(return_value=SimpleNamespace(
            open_embedded_archive=lambda _: SimpleNamespace(toc=dict.fromkeys((
                'numpy', 'PIL', 'canon_runtime', 'canon_engine', 'project_state',
                'camera_install.rp_preflight_reference',
                'camera_install.family_registration_reference',
                'camera_install.camera_families_reference',
                'camera_install.independent_registration_reference',
                'camera_install.registration_sequence_reference')))))
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict('sys.modules', {'PyInstaller.archive.readers': reader}), \
                patch.dict('os.environ', {'SystemRoot': temporary}), \
                patch('build_independent_diagnostic.subprocess.run', return_value=SimpleNamespace(
                    returncode=0, stdout='--allow-temporary-session --preflight-style --experimental-register')) as run:
            root = Path(temporary)
            (root / 'CanonIndependentDiagnostic.exe').write_bytes(b'test executable')
            report = audit_bundle(root)
            self.assertFalse(report['cameraAccessAttempted'])
            self.assertTrue(report['registrationImplemented'])
            self.assertFalse(report['registrationEnabledByDefault'])
            self.assertFalse(report['physicalRegistrationValidated'])
            self.assertNotIn('PYTHONPATH', run.call_args.kwargs['env'])
            self.assertEqual(run.call_args.args[0][-1], '--help')
            for filename in ('DppCore.dll', 'carrier.bin', 'base.pf3', 'profile.icc'):
                resource = root / filename
                resource.write_bytes(b'forbidden')
                with self.subTest(filename=filename), self.assertRaises(RuntimeError):
                    audit_bundle(root)
                resource.unlink()
            library = root / 'numerical.dll'
            library.write_bytes(b'changed wheel library')
            import numpy
            fake_numpy = root / 'wheel' / 'numpy' / '__init__.py'
            libraries = fake_numpy.parent.parent / 'numpy.libs'
            libraries.mkdir(parents=True)
            (libraries / library.name).write_bytes(b'original wheel library')
            with patch.object(numpy, '__file__', str(fake_numpy)), self.assertRaises(RuntimeError):
                audit_bundle(root)
            library.unlink()
            (libraries / library.name).unlink()
            run.return_value.stdout = '--allow-temporary-session'
            with self.assertRaisesRegex(RuntimeError, 'help smoke'):
                audit_bundle(root)


if __name__ == '__main__':
    unittest.main()
