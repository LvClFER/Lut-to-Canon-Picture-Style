import unittest
from camera_install.curve_family_sensitivity import summarize,SOURCES


class CurveFamilyTests(unittest.TestCase):
    def fixture(self):
        return dict(cameraAccess=False,compilerPatched=False,sourceFilesModified=False,
            rows=[dict(model='synthetic',cameraId=1,sourceName=name,mutation='control',compiled=True,
                rcCreate=0,rcId=0,rcDescriptor=0,rcSize=0,rcGet=0,payloadSize=4,
                payloadSha256='changed' if i==1 else 'baseline') for i,name in enumerate(SOURCES)])

    def test_complete_hash_sensitivity(self):
        row=summarize(self.fixture())['rows'][0]
        self.assertEqual(row['channelEqualsBaseline'],[False,True,True])
        self.assertIsNone(row['observedCompileLookup1019Count'])

    def test_failed_cells_are_not_identical_outputs(self):
        report=self.fixture();report['rows'][1]['compiled']=False
        row=summarize(report)['rows'][0]
        self.assertIsNone(row['channelEqualsBaseline']);self.assertFalse(row['allFourCompile'])

    def test_incomplete_and_contradictory_evidence_refused(self):
        report=self.fixture();report['rows'].pop()
        with self.assertRaises(ValueError):summarize(report)
        report=self.fixture();report['rows'][0]['rcGet']=80
        with self.assertRaises(ValueError):summarize(report)
