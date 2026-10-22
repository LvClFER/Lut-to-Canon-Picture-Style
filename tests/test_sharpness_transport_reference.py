import hashlib
from pathlib import Path
import tempfile
import unittest
from camera_install.sharpness_transport_reference import verify


class SharpnessTransportTests(unittest.TestCase):
    def fixture(self,folder):
        base=bytes([0,1,0,0])
        report=dict(cameraAccess=False,compilerPatched=False,writesOriginals=False,cameraId=1042,
                    baseline=dict(payloadSize=4,payloadSha256=hashlib.sha256(base).hexdigest(),
                                  rcCreate=0,rcId=0,rcDescriptor=0,rcSize=0,rcGet=0),experiments=[])
        for value in range(1,8):
            data=bytes([0,min(value,5),0,0]);path=Path(folder)/str(value);path.write_bytes(data)
            report['experiments'].append(dict(name=f'SHARPNESS_1034_VALUE{value}',mutationProperty='0x40001034',
                serializedMutationExact=True,changedSerializedFields=['0x1034'],rcCreate=0,rcId=0,
                rcDescriptor=0,rcSize=0,rcGet=0,privateResearchPayload=str(path),
                payloadSha256=hashlib.sha256(data).hexdigest(),changedByteCount=int(value!=1),
                changedOffsets=[] if value==1 else [1]))
        return report

    def test_exact_clamp_and_opaque_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(verify(self.fixture(folder))['allSevenExact'])

    def test_claimed_offsets_do_not_hide_extra_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            report=self.fixture(folder);row=report['experiments'][2];data=bytes([9,3,0,0])
            Path(row['privateResearchPayload']).write_bytes(data)
            row['payloadSha256']=hashlib.sha256(data).hexdigest()
            with self.assertRaisesRegex(ValueError,'Opaque'):verify(report)

    def test_missing_values_and_unsafe_evidence_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            report=self.fixture(folder);report['cameraAccess']=True
            with self.assertRaises(ValueError):verify(report)
            report['cameraAccess']=False;report['experiments'].pop()
            with self.assertRaises(ValueError):verify(report)
