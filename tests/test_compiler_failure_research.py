import unittest
from camera_install.compiler_failure_research import summarize


class FailureResearchTests(unittest.TestCase):
    def test_getter_success_does_not_erase_setup_error(self):
        report=self.report('0x1007',1460,0)
        report['files'][0]['rcId']=7
        row=summarize(report)['cases'][0]
        self.assertEqual(row['category'],'camera-id-setup-rejected')
        self.assertEqual(row['apiErrors'],{'rcId':7})
        self.assertEqual(row['cameraCompatibility'],'not-tested')

    def test_other_upstream_errors(self):
        for key in ('rcCreate','rcDescriptor','rcSize'):
            report=self.report('0x1007',1460,0)
            report['files'][0][key]=81
            row=summarize(report)['cases'][0]
            self.assertEqual(row['category'],'upstream-compiler-api-failure')
            self.assertEqual(row['apiErrors'],{key:81})
    def report(self, prop, size, rc=80):
        return dict(cameraAccess=False, compilerPatched=False, files=[dict(rcGet=rc,
            mlibCalls=dict(captures=[dict(functionRva='0x4ef20Raw', property=prop, size=size, rc=rc)]))])

    def test_metadata_is_not_camera_incompatibility(self):
        row = summarize(self.report('0x1007', 1460))['cases'][0]
        self.assertEqual(row['category'], 'legacy-metadata-read-failed')
        self.assertEqual(row['cameraCompatibility'], 'not-tested')

    def test_derived_table_failure(self):
        self.assertEqual(summarize(self.report('0x1022', 4096))['cases'][0]['category'],
                         'derived-4096-table-read-failed')

    def test_successful_read_not_failure(self):
        self.assertEqual(summarize(self.report('0x1007', 1460, 0))['cases'][0]['category'],
                         'no-failure-observed')

    def test_reject_live_or_patched_trace(self):
        for key in ('cameraAccess', 'compilerPatched'):
            report = self.report('0x1007', 1460)
            report[key] = True
            with self.assertRaises(ValueError):
                summarize(report)
