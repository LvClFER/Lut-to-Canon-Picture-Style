import struct
import unittest
from camera_install.canon_event_receive_reference import drain
from camera_install.wpd_data_phase_reference import COMMON,MTP,ReadPropertyMapAdapter


class EventReceiveTests(unittest.TestCase):
    def sender(self,batches,fail_completion_at=None):
        pending=iter(batches);commands=[];state={'index':0}
        def send(request):
            command=request[(COMMON,1002)];commands.append(command)
            result={(COMMON,1003):0}
            if command==13:
                self.assertEqual(request[(MTP,1001)],0x9116)
                state['body']=next(pending);state['index']+=1
                result.update({(MTP,1006):str(state['index']),(MTP,1007):len(state['body'])})
            elif command==15:
                body=state['body'];result.update({(MTP,1012):body,(MTP,1009):len(body)})
            else:
                result.update({(MTP,1003):0x2002 if state['index']==fail_completion_at else 0x2001,(MTP,1004):()})
            return result
        return ReadPropertyMapAdapter(send),commands

    def test_completed_continuation_preserves_order_not_freshness(self):
        first=struct.pack('<III',15,0xc189,0xd163)+b'abc'+struct.pack('<II',8,0xffffffff)
        second=struct.pack('<III',15,0xc189,0xd163)+b'def'+struct.pack('<II',8,0)
        adapter,commands=self.sender((first,second))
        result=drain(adapter)
        self.assertEqual([p.value for p in result.properties],[b'abc',b'def'])
        self.assertEqual((result.batch_count,result.received_bytes),(2,len(first)+len(second)))
        self.assertEqual(commands,[13,15,17,13,15,17])
        self.assertNotIn('abc',repr(result))

    def test_failed_second_completion_does_not_return_partial_events(self):
        adapter,commands=self.sender((struct.pack('<II',8,0xffffffff),bytes(8)),2)
        with self.assertRaises(RuntimeError):drain(adapter)
        self.assertEqual(commands.count(17),2)

    def test_continuation_bounds_and_malformed_completed_batch(self):
        for kwargs in ({'max_batches':1},{'max_bytes':8}):
            adapter,commands=self.sender((struct.pack('<II',8,0xffffffff),))
            with self.assertRaises(RuntimeError):drain(adapter,**kwargs)
            self.assertEqual(commands,[13,15,17])
        adapter,commands=self.sender((b'x',))
        with self.assertRaises(ValueError):drain(adapter)
        self.assertEqual(commands,[13,15,17])

    def test_invalid_bounds_do_not_call_adapter(self):
        for kwargs in ({'max_batches':True},{'max_batches':0},{'max_bytes':0},{'max_bytes':16*1048576+1}):
            with self.assertRaises(ValueError):drain(None,**kwargs)
