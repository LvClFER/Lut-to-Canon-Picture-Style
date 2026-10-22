import unittest
from camera_install.context_dispatch_research import summarize


def evidence(events=()):
    return dict(cameraAccess=False, compilerPatched=False, sourceFilesModified=False,
                rows=[dict(sourceName='source.pf3', cameraId=1, model='scratch', mutation='control',
                           compiled=True, contextDispatch=list(events))])


class ContextDispatchTests(unittest.TestCase):
    def test_context_is_observed_not_inferred_from_extension(self):
        result = summarize(evidence([dict(name='baseOutput', stage='compile')]))
        self.assertEqual(result['rows'][0]['observedContext'], 'baseOutput')
        self.assertEqual(result['cameraCompatibility'], 'not-tested')

    def test_missing_or_input_only_observation_is_unknown(self):
        self.assertIsNone(summarize(evidence())['rows'][0]['observedContext'])
        self.assertIsNone(summarize(evidence([dict(name='pf3Output', stage='inputs')]))['rows'][0]['observedContext'])

    def test_mixed_contexts_and_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            summarize(evidence([dict(name=name, stage='compile') for name in ('baseOutput', 'pf3Output')]))
        report = evidence()
        report['rows'] *= 2
        with self.assertRaises(ValueError):
            summarize(report)

    def test_unsafe_evidence_rejected(self):
        report = evidence()
        report['compilerPatched'] = True
        with self.assertRaises(ValueError):
            summarize(report)
