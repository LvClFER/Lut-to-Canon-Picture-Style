import unittest
from camera_install.curve_stage_research import identify,CURVE_KEYS


class CurveStageTests(unittest.TestCase):
    def fixture(self):
        before={key:bytes(300).hex() for key in CURVE_KEYS};after=before.copy()
        after['postCurvesHex']=(bytes([1])+bytes(299)).hex()
        def trace(arguments):return {'captures':[{'functionRva':'0x11220','initializedArguments':arguments}]}
        return dict(cameraAccess=False,compilerPatched=False,writesOriginals=False,
            baseline={'mlibCalls':trace(before)},experiments=[dict(name='synthetic',mutationProperty='0x40001065',
                rcCreate=0,rcId=0,rcDescriptor=0,rcSize=0,rcGet=0,serializedMutationExact=True,
                changedSerializedFields=['0x1065'],changedByteCount=1,mlibCalls=trace(after))])

    def test_native_slot_not_guessed_from_experiment_name(self):
        self.assertEqual(identify(self.fixture())['rows'][0]['nativeArgument'],'postCurvesHex')

    def test_failed_gate_and_multiple_changed_slots_refused(self):
        report=self.fixture();report['experiments'][0]['rcId']=7
        with self.assertRaises(ValueError):identify(report)
        report=self.fixture();arguments=report['experiments'][0]['mlibCalls']['captures'][0]['initializedArguments']
        arguments['thirdCurvesHex']=arguments['postCurvesHex']
        with self.assertRaises(ValueError):identify(report)

    def test_missing_argument_capture_refused(self):
        report=self.fixture();report['baseline']['mlibCalls']['captures']=[]
        with self.assertRaises(ValueError):identify(report)
