import unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_camera_workflow_entrypoints as camera_tests


class NikonImportUiTests(unittest.TestCase):
    setUp=camera_tests.CameraWorkflowEntrypointTests.setUp
    close_window=camera_tests.CameraWorkflowEntrypointTests.close_window

    def test_success_appends_lut_without_clearing_raw_references(self):
        window=self.window
        profile=Path(self.stack.enter_context(__import__('tempfile').TemporaryDirectory()))/'prm.bin';profile.touch()
        window.settings.data['nikon_profile_path']=str(profile)
        refs=[Path('loaded.CR3')];pixels=object()
        window.references=refs;window.source_full=pixels;window.source_is_raw=True
        entry=dict(cube={'title':'Synthetic NP3'},metadata={},enabled=True,opacity=1)
        pending=[]
        with patch.object(window,'start_worker',side_effect=lambda w,pool,result,error:pending.append((w,result,error))), \
                patch('nikon_import.convert_asset',return_value=entry), \
                patch.object(window,'refresh_lut_list'),patch.object(window,'commit_history'):
            window.import_np3_paths([Path('synthetic.np3')])
            worker,result,error=pending[0];result(worker.fn())
        self.assertIsNone(window._np3_import_dialog)
        self.assertEqual(len(window.luts),1)
        self.assertIs(window.references,refs);self.assertIs(window.source_full,pixels)
        self.assertTrue(window.source_is_raw)
        self.assertIn('Added 1 NP3',window.status.text())
        window.source_full=None


if __name__=='__main__':unittest.main()
