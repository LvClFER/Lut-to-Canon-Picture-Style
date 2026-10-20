import unittest
from camera_install.wpd_data_phase_reference import (
    COMMON, MTP, CommandPropertyMapAdapter, Completion)


class WpdCommandTests(unittest.TestCase):
    def test_exact_no_data_map_and_completion(self):
        calls = []
        def sender(request):
            calls.append(dict(request))
            return {(COMMON,1003):0, (MTP,1003):0x2001, (MTP,1004):[4,5]}
        adapter = CommandPropertyMapAdapter(sender)
        result = adapter.execute(0x9127,(0xd17f,))
        self.assertEqual(calls,[{(COMMON,1001):MTP,(COMMON,1002):12,
                                 (MTP,1001):0x9127,(MTP,1002):(0xd17f,)}])
        self.assertEqual(result,Completion(0x2001,(4,5)))
        self.assertIs(result,adapter.last_completion)

    def test_preflight_does_not_call_sender(self):
        calls = []
        adapter = CommandPropertyMapAdapter(lambda r:calls.append(r))
        for opcode,parameters in ((True,()),(-1,()),(65536,()),
                                  (1,[1]),(1,(True,)),(1,(-1,)),(1,(1,)*6)):
            with self.assertRaises(ValueError):
                adapter.execute(opcode,parameters)
        self.assertEqual(calls,[])

    def test_failure_never_retries_or_reuses_completion(self):
        responses = iter(({(COMMON,1003):0,(MTP,1003):0x2001,(MTP,1004):()},
                          {(COMMON,1003):0,(MTP,1003):0xa106,(MTP,1004):()},
                          {(COMMON,1003):0x80004005},
                          {(COMMON,1003):0,(MTP,1003):0x2001}))
        calls = []
        def sender(request):
            calls.append(request)
            return next(responses)
        adapter = CommandPropertyMapAdapter(sender)
        adapter.execute(1)
        with self.assertRaisesRegex(RuntimeError, r'Command 0x0001 returned PTP 0xA106; expected 0x2001'):
            adapter.execute(1)
        self.assertEqual(adapter.last_completion,Completion(0xa106,()))
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                adapter.execute(1)
            self.assertIsNone(adapter.last_completion)
        self.assertEqual(len(calls),4)


if __name__ == '__main__':
    unittest.main()
