import struct
import unittest
from camera_install.stage_trace_validation import validate


class StageTraceTests(unittest.TestCase):
    def trace(self):
        coefficients = [0.]*57
        for index in (0,20,40): coefficients[index] = 1.
        return {'files':[{'model':'synthetic','payloadSize':123,'mlibCalls':{'counts':{},'captures':[
            {'functionRva':'0xf070','phase':1,'callIndex':1,'bits':8,'mode':1,
             'input':[255,0,0],'output':[3488670,5249782,4405512]},
            {'functionRva':'0x1d380','phase':1,'callIndex':1,'input':[.2,.4,.8],
             'output':[.2,.4,.8],'coefficientsFloat64Hex':struct.pack('<57d',*coefficients).hex()},
            {'functionRva':'0x1dd50','phase':1,'callIndex':1,'callerRva':'0x123',
             'domainSize':2,'pairsHex':struct.pack('<4d',0,0,1,1).hex()}]}}]}

    def test_exact_stages_and_order(self):
        result = validate(self.trace())
        self.assertEqual(result['passed'],2)
        self.assertFalse(result['cameraAcceptanceEstablished'])
        self.assertTrue(result['curveInputsOutputsNotCaptured'])
        self.assertEqual(len(result['routes'][0]['phases'][0]['sampledOrder']),3)

    def test_bad_math_is_not_accepted(self):
        trace = self.trace()
        trace['files'][0]['mlibCalls']['captures'][0]['output'][0] += 1
        self.assertEqual(validate(trace)['passed'],1)

    def test_corrupt_cache_rejected(self):
        trace = self.trace()
        trace['files'][0]['mlibCalls']['captures'][2]['pairsHex'] = '00'
        with self.assertRaises(ValueError): validate(trace)

    def test_failed_route_recorded(self):
        result = validate({'files':[{'model':'failed','error':'compiler failed'}]})
        self.assertEqual(result['passed'],0)
        self.assertEqual(result['routes'][0]['error'],'compiler failed')
