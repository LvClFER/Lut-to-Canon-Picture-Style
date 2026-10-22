import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import package_public_alpha as package


class PublicSourcePackageTests(unittest.TestCase):
    def test_clean_package_contains_independent_runtime_and_executes_without_native_oracles(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder,archive,manifest=package.build(Path(temporary))
            self.assertEqual(manifest['portable_storage']['style_format'],'single .canonstyleproject archive')
            self.assertTrue((folder/'independent_camera_diagnostic.py').is_file())
            for excluded in ('compiler_regression.py','virtual_compatibility.py'):
                self.assertFalse((folder/'camera_install'/excluded).exists())
            with zipfile.ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
            script='''
import sys,ctypes,tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
def denied(*args,**kwargs):raise AssertionError('Native runtime access')
ctypes.WinDLL=denied
import canon_engine as engine
engine.EdsCFParse=denied
from camera_install.pf3_source_reference import write_source_fields,read_source_fields
from camera_install.offline_registration_reference import prepare
from camera_install.independent_registration_reference import register_in_session
from camera_install.camera_families_reference import CAMERA_FAMILIES
from camera_install.family_registration_reference import prepare_family_registration
assert len(CAMERA_FAMILIES)==77
from camera_install.family_preflight_reference import prepare_observed_preflight
from camera_install.ptp_wire import Container,Decoder
command=Container(1,0x1001,7)
assert Decoder().feed(command.encode())==[command]
with tempfile.TemporaryDirectory() as scratch:
    root=Path(scratch)
    engine.runtime_cache_dir=lambda:root/'empty-cache'
    keys=(bytes(512),bytes(513))
    source=root/'owned.pf3'
    source.write_bytes(write_source_fields(engine._generated_pf3_fields('Neutral'),keys))
    result=engine.resolve_independent_base_pf3('Portrait',cipher_reference=source)
    raw=result['path'].read_bytes()
    assert read_source_fields(raw,keys)==engine._generated_pf3_fields('Portrait')
    job=prepare(raw,keys,route='compact16752-dense-pixel',internal_selector=0x80000433,
        normalized_descriptor=bytes(14796),handler_selector=0x23,supported_operations=(0x9110,))
    assert job.send.slot==3 and len(job.send.data)==16728
assert 'camera_install.compiler_regression' not in sys.modules
assert 'camera_install.virtual_compatibility' not in sys.modules
'''
            result=subprocess.run([sys.executable,'-I','-B','-c',script],cwd=folder,
                capture_output=True,text=True,timeout=40)
            self.assertEqual(result.returncode,0,result.stderr)
            help_result=subprocess.run([sys.executable,'-S','-B','independent_camera_diagnostic.py','--help'],
                cwd=folder,capture_output=True,text=True,timeout=20)
            self.assertEqual(help_result.returncode,0,help_result.stderr)
            self.assertIn('--preflight-style',help_result.stdout)
            self.assertEqual(package.audit_tree(folder),[])


if __name__=='__main__':unittest.main()
