import hashlib
import tempfile
import unittest
from pathlib import Path
from camera_install.runtime_seed_research import compare_outputs
from camera_install.pf3_field_experiments import compile_stock


class RuntimeSeedResearchTests(unittest.TestCase):
    def test_reject_unbounded_or_wrong_agent_seed_before_spawning(self):
        for seed in (1,0):
            with self.assertRaises(ValueError):
                compile_stock(None,Path('dll'),Path('wrong_agent.js'),Path('source'),0,b'',runtime_seed=seed)

    def test_seed_independence_requires_both_and_matching_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'payload.bin'
            path.write_bytes(b'compiled')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            def case(seed):
                return dict(model='virtual',cameraId=1,seedByte=seed,rcGet=0,
                            privatePayload=str(path),payloadSha256=digest)
            report = dict(cameraAccess=False,compilerPatched=False,sourceSha256='source',rows=[case(0)])
            reference = dict(files=[dict(rcGet=0,sourceSha256='source',payloadSha256=digest)])
            self.assertFalse(compare_outputs(report,reference)['seedIndependent']['0x1'])
            report['rows'].append(case(255))
            self.assertTrue(compare_outputs(report,reference)['seedIndependent']['0x1'])
            path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                compare_outputs(report,reference)

    def test_failed_cases_never_become_exact(self):
        report = dict(cameraAccess=False,compilerPatched=False,sourceSha256='source',
                      rows=[dict(model='virtual',cameraId=1,seedByte=0,rcGet=80)])
        reference = dict(files=[dict(rcGet=0,sourceSha256='source',payloadSha256='hash')])
        result = compare_outputs(report,reference)
        self.assertEqual(result['exactStockReferenceCases'],0)
        self.assertEqual(result['rows'][0]['cameraCompatibility'],'not-tested')
