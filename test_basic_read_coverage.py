import unittest
from camera_install.basic_read_coverage import summarize


class BasicReadCoverageTests(unittest.TestCase):
    def report(self):
        return dict(cameraAccess=False,compilerPatched=False,sourceFilesModified=False,
                    rows=[dict(model='synthetic',cameraId=1,source='fixture',mutation='control',compiled=False)])

    def test_missing_observer_is_not_no_reads(self):
        report=self.report()
        self.assertEqual(summarize(report)['rows'][0]['observation'],'observer-missing')
        report['rows'][0]['basicReads']=[]
        self.assertEqual(summarize(report)['rows'][0]['observation'],'no-reads-at-observed-getter')

    def test_failed_compilation_stays_failed(self):
        report=self.report();report['rows'][0]['basicReads']=[dict(stage='compile',property='1034',rc=80)]
        row=summarize(report)['rows'][0]
        self.assertFalse(row['compiled']);self.assertEqual(row['failedReadFields'],['1034'])
        self.assertEqual(row['physicalCompatibility'],'not-tested')

    def test_duplicates_and_truncation_refused(self):
        report=self.report();report['rows'].append(dict(report['rows'][0]))
        with self.assertRaises(ValueError):summarize(report)
        report=self.report();report['rows'][0]['basicReads']=[{}]*64
        with self.assertRaises(ValueError):summarize(report)
