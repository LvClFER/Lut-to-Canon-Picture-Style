import unittest
from camera_install.mtp_write_reference import transfer
from camera_install.wpd_data_phase_reference import COMMON, MTP, PropertyMapAdapter, ReadPropertyMapAdapter, decode_completion
from camera_install.mtp_read_reference import receive


class WpdDataPhaseReferenceTests(unittest.TestCase):
    def test_receive_maps_actual_bytes_and_completion(self):
        requests=[]
        chunks=iter((b'abc',b'de'))
        def sender(request):
            requests.append(request)
            result={(COMMON,1003):0}
            command=request[(COMMON,1002)]
            if command==13: result.update({(MTP,1006):'receive',(MTP,1007):5})
            elif command==15:
                result[(MTP,1012)]=next(chunks)
                result[(MTP,1009)]=len(result[(MTP,1012)])
            elif command==17: result.update({(MTP,1003):0x2001,(MTP,1004):()})
            return result
        adapter=ReadPropertyMapAdapter(sender,chunk_size=3)
        self.assertEqual(receive(adapter,0x9116,(1,)),b'abcde')
        self.assertEqual([r[(COMMON,1002)] for r in requests],[13,15,15,17])
        self.assertEqual(requests[0][(MTP,1002)],(1,))
        self.assertEqual([r[(MTP,1008)] for r in requests[1:3]],[3,2])
        self.assertEqual(requests[1][(MTP,1012)],bytes(3))
        self.assertEqual(adapter.last_completion.response_code,0x2001)

    def test_receive_begin_invalid_total_completes_known_context_once(self):
        for total in (None,True,-1,2**64):
            commands=[]
            def sender(request):
                command=request[(COMMON,1002)];commands.append(command)
                return {(COMMON,1003):0,(MTP,1006):'receive',(MTP,1007):total,
                        (MTP,1003):0x2001,(MTP,1004):()}
            with self.assertRaises(RuntimeError): receive(ReadPropertyMapAdapter(sender),0x9116)
            self.assertEqual(commands,[13,17])

    def test_receive_requires_actual_buffer_and_immutable_copy(self):
        for value in (None,3,b'abcd'):
            adapter=ReadPropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1012):value,(MTP,1009):3})
            with self.assertRaises(RuntimeError): adapter.read('context',3)
        value=bytearray(b'abc')
        adapter=ReadPropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1012):value,(MTP,1009):3})
        chunk=adapter.read('context',3)
        value[0]=0
        self.assertEqual((chunk.buffer,chunk.actual),(b'abc',3))

    def test_receive_request_bounds_and_policy(self):
        for size in (0,True,1048577):
            with self.assertRaises(ValueError): ReadPropertyMapAdapter(None,chunk_size=size)
            adapter=ReadPropertyMapAdapter(lambda request:self.fail('No send expected'))
            with self.assertRaises(ValueError): adapter.read('context',size)

    def test_receive_failure_cleanup_and_final_response_gate(self):
        for failed_read in (True,False):
            commands=[]
            def sender(request):
                command=request[(COMMON,1002)];commands.append(command)
                result={(COMMON,1003):0}
                if command==13:result.update({(MTP,1006):'receive',(MTP,1007):3})
                elif command==15:
                    if failed_read:result[(COMMON,1003)]=0x80004005
                    else:result.update({(MTP,1012):b'abc',(MTP,1009):3})
                else:result.update({(MTP,1003):0x2002,(MTP,1004):()})
                return result
            with self.assertRaises(RuntimeError):receive(ReadPropertyMapAdapter(sender),0x9116)
            self.assertEqual(commands,[13,15,17])

    def test_receive_required_count_and_padded_actual_prefix(self):
        for actual in (None,True,-1,4):
            adapter=ReadPropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1012):b'abc',(MTP,1009):actual})
            with self.assertRaises(RuntimeError):adapter.read('context',3)
        commands=[]
        def sender(request):
            command=request[(COMMON,1002)];commands.append(command)
            result={(COMMON,1003):0}
            if command==13:result.update({(MTP,1006):'ctx',(MTP,1007):0xffffffff,(MTP,1013):3})
            elif command==15:result.update({(MTP,1012):b'ab\0',(MTP,1009):2})
            else:result.update({(MTP,1003):0x2001,(MTP,1004):()})
            return result
        self.assertEqual(receive(ReadPropertyMapAdapter(sender),0x9116),b'ab')
        self.assertEqual(commands,[13,15,17])

    def test_receive_driver_optimal_is_optional_and_bounded(self):
        for optimal,expected in ((None,7),(3,3),(100,7)):
            result={(COMMON,1003):0,(MTP,1006):'ctx',(MTP,1007):12}
            if optimal is not None:result[(MTP,1013)]=optimal
            start=ReadPropertyMapAdapter(lambda request:result,chunk_size=7).begin(0x9116,())
            self.assertEqual(start.optimal_size,expected)


    def test_complete_transfer_property_maps(self):
        requests=[]
        def sender(request):
            requests.append(request)
            result={(COMMON,1003):0}
            command=request[(COMMON,1002)]
            if command==14: result[(MTP,1006)]='new-context'
            elif command==16: result[(MTP,1011)]=request[(MTP,1010)]
            elif command==17:
                result[(MTP,1003)]=0x2001
                result[(MTP,1004)]=()
            return result
        self.assertEqual(transfer(PropertyMapAdapter(sender),0x9110,(2,),b'abcde',chunk_size=3),0x2001)
        self.assertEqual([r[(COMMON,1002)] for r in requests],[14,16,16,17])
        self.assertEqual(requests[0][(MTP,1007)],5)
        self.assertEqual(requests[0][(MTP,1002)],(2,))
        self.assertEqual(requests[1][(MTP,1012)],b'abc')
        self.assertEqual(requests[2][(MTP,1010)],2)
        self.assertTrue(all(r[(COMMON,1001)]==MTP for r in requests))

    def test_hresult_and_ptp_response_are_not_conflated(self):
        for result in ({(COMMON,1003):0x80004005,(MTP,1003):0x2001},
                       {(COMMON,1003):0}, {(COMMON,1003):True}, {}):
            adapter=PropertyMapAdapter(lambda request:result)
            with self.assertRaises(RuntimeError): adapter.complete('context')
        adapter=PropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1003):0x2002,(MTP,1004):()})
        self.assertEqual(adapter.complete('context'),0x2002)

    def test_missing_ack_is_not_assumed_full_length(self):
        for value in (None,True,-1,0x100000000):
            adapter=PropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1011):value})
            with self.assertRaises(RuntimeError): adapter.write('context',b'abc')

    def test_missing_context_is_rejected(self):
        for context in (None,'',3):
            adapter=PropertyMapAdapter(lambda request:{(COMMON,1003):0,(MTP,1006):context})
            with self.assertRaises(RuntimeError): adapter.begin(0x9110,(),3)

    def test_completion_preserves_bounded_parameters(self):
        values=[0,1,2,3,0xffffffff]
        result={(MTP,1003):0x2001,(MTP,1004):values}
        completion=decode_completion(result)
        values[0]=99
        self.assertEqual(completion.parameters,(0,1,2,3,0xffffffff))

    def test_bad_completion_collection(self):
        for parameters in (None,(),(1,)*6,(True,),(-1,),(0x100000000,),('1',),(1.5,)):
            result={(MTP,1003):0x2001}
            if parameters is not None: result[(MTP,1004)]=parameters
            if parameters==():
                self.assertEqual(decode_completion(result).parameters,())
            else:
                with self.assertRaises(RuntimeError): decode_completion(result)

    def test_failed_completion_clears_previous_result(self):
        result={(COMMON,1003):0,(MTP,1003):0x2001,(MTP,1004):(3,)}
        adapter=PropertyMapAdapter(lambda request:result)
        adapter.complete('context')
        self.assertEqual(adapter.last_completion.parameters,(3,))
        result[(MTP,1004)]=(1,)*6
        with self.assertRaises(RuntimeError): adapter.complete('context')
        self.assertIsNone(adapter.last_completion)
