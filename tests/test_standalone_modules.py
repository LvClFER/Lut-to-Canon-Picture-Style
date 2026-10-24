from types import ModuleType,SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from build_standalone import audit_modules,RESEARCH_ONLY_MODULES


class StandaloneModuleTests(unittest.TestCase):
    def test_required_compilers_and_research_exclusion(self):
        required={'sample_images','sample_browser','rawpy','nikon_conversion','nikon_import','nikon_profile_data',
                  'camera_install.family_registration_reference','camera_install.camera_families_reference',
                  'camera_install.independent_registration_reference','camera_install.legacy_dense9_carrier_reference'}
        reader=ModuleType('PyInstaller.archive.readers')
        reader.CArchiveReader=Mock()
        archive=SimpleNamespace(toc=dict.fromkeys(required))
        reader.CArchiveReader.return_value.open_embedded_archive.return_value=archive
        with patch.dict('sys.modules',{'PyInstaller.archive.readers':reader}):
            audit_modules('injected.exe')
            for name in RESEARCH_ONLY_MODULES:
                archive.toc=dict.fromkeys(required|{name})
                with self.subTest(module=name),self.assertRaisesRegex(RuntimeError,'Research'):
                    audit_modules('injected.exe')
            archive.toc={}
            with self.assertRaisesRegex(RuntimeError,'Missing'):audit_modules('injected.exe')
            for name in required:
                archive.toc=dict.fromkeys(required-{name})
                with self.subTest(missing=name),self.assertRaisesRegex(RuntimeError,'Missing'):
                    audit_modules('injected.exe')
