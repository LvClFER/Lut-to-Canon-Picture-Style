import tempfile
import unittest
from concurrent.futures import CancelledError
from pathlib import Path
from unittest.mock import patch
from nikon_import import convert_asset
from project_state import ProjectDocument,save_project,load_project


class NikonImportTests(unittest.TestCase):
    def test_generated_cube_embeds_in_portable_project_without_nikon_data(self):
        cube=dict(title='Synthetic',size=33,values=[0.25,0.5,0.75]*(33**3))
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'style.np3';source.write_bytes(b'synthetic')
            with patch('nikon_import.compile_cube',return_value=cube):
                entry=convert_asset(source,'local-profile',folder/'cache')
            path=entry['cube']['path'];self.assertTrue(path.is_file())
            project=folder/'style.canonstyleproject'
            save_project(project,ProjectDocument(edit={'luts':[{'path':str(path),'metadata':entry['metadata']}]}))
            loaded=load_project(project)
            self.assertEqual(loaded.edit['luts'][0]['metadata']['sourceFormat'],'Nikon NP3')
            self.assertTrue(Path(loaded.edit['luts'][0]['path']).is_file())
            self.assertEqual(source.read_bytes(),b'synthetic')

    def test_failed_or_cancelled_conversion_preserves_existing_cache(self):
        cube=dict(title='Synthetic',values=[0.0]*(33**3*3))
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'style.np3';source.write_bytes(b'synthetic');cache=folder/'cache'
            with patch('nikon_import.compile_cube',return_value=cube):
                entry=convert_asset(source,'profile',cache);path=entry['cube']['path'];previous=path.read_bytes()
                with patch('nikon_import.os.replace',side_effect=OSError('disk failure')):
                    with self.assertRaises(OSError):convert_asset(source,'profile',cache)
                self.assertEqual(path.read_bytes(),previous);self.assertEqual(list(cache.glob('*.tmp')),[])
                with self.assertRaises(CancelledError):convert_asset(source,'profile',cache,cancel=lambda:True)
                self.assertEqual(path.read_bytes(),previous)


if __name__=='__main__':unittest.main()
