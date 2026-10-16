import unittest
from camera_install.mtp_write_reference import transfer


class Fake:
    def __init__(self, count=None, response=0x2001):
        self.count=count; self.response=response; self.calls=[]
    def begin(self, opcode, parameters, size):
        self.calls.append(('begin',opcode,parameters,size)); return 'fresh-context'
    def write(self, context, chunk):
        self.calls.append(('write',context,chunk))
        if isinstance(self.count,Exception): raise self.count
        return len(chunk) if self.count is None else self.count
    def complete(self, context):
        self.calls.append(('complete',context))
        if isinstance(self.response,Exception): raise self.response
        return self.response


class MtpWriteReferenceTests(unittest.TestCase):
    def test_exact_chunks_and_one_completion(self):
        adapter=Fake()
        self.assertEqual(transfer(adapter,0x9110,(),b'abcdefgh',chunk_size=3),0x2001)
        self.assertEqual([c[2] for c in adapter.calls if c[0]=='write'],[b'abc',b'def',b'gh'])
        self.assertEqual(adapter.calls[-1],('complete','fresh-context'))

    def test_short_overlong_zero_and_bool_ack_rejected(self):
        for count in (0,2,4,True):
            adapter=Fake(count=count)
            with self.assertRaises(RuntimeError): transfer(adapter,0x9110,(),b'abc')
            self.assertEqual(sum(c[0]=='complete' for c in adapter.calls),1)

    def test_no_retries_after_write_exception(self):
        adapter=Fake(count=OSError('failure'))
        with self.assertRaises(OSError): transfer(adapter,0x9110,(),b'abcdef',chunk_size=3)
        self.assertEqual(sum(c[0]=='write' for c in adapter.calls),1)
        self.assertEqual(sum(c[0]=='complete' for c in adapter.calls),1)

    def test_cleanup_does_not_hide_original_error(self):
        adapter=Fake(count=OSError('original'),response=RuntimeError('cleanup'))
        with self.assertRaisesRegex(OSError,'original'): transfer(adapter,0x9110,(),b'abc')

    def test_failed_completion_not_reissued(self):
        for response in (0x2002,RuntimeError('completion')):
            adapter=Fake(response=response)
            with self.assertRaises(RuntimeError): transfer(adapter,0x9110,(),b'abc')
            self.assertEqual(sum(c[0]=='complete' for c in adapter.calls),1)

    def test_bounds_fail_before_adapter(self):
        for kwargs in ({'payload':b''},{'opcode':0x10000},{'parameters':(1,)*6},
                       {'parameters':(-1,)},{'chunk_size':0},{'max_bytes':2},
                       {'opcode':True},{'opcode':1.5},{'parameters':(True,)},
                       {'chunk_size':1.5},{'max_bytes':True},{'max_bytes':1048577},
                       {'payload':1000000000}):
            adapter=Fake(); args={'opcode':0x9110,'parameters':(),'payload':b'abc'};args.update(kwargs)
            with self.assertRaises(ValueError): transfer(adapter,**args)
            self.assertEqual(adapter.calls,[])
