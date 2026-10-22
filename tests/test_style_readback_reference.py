import struct,unittest
from camera_install.style_readback_reference import decode_9189,receive_9189
from camera_install.mtp_read_reference import ReadStart,ReadChunk
from camera_install.registration_encode_reference import encode_style


class StyleReadbackTests(unittest.TestCase):
    def adapter(self,data,response=0x2001):
        calls=[]
        class Fake:
            def begin(inner,opcode,parameters):
                calls.append(('begin',opcode,parameters));inner.offset=0
                return ReadStart('test',len(data),5)
            def read(inner,context,requested):
                calls.append(('read',requested))
                chunk=data[inner.offset:inner.offset+requested];inner.offset+=len(chunk)
                return ReadChunk(chunk,len(chunk))
            def complete(inner,context):
                calls.append(('complete',));return response
        return Fake(),calls

    def test_injected_receive_requires_completed_actual_bytes_for_each_slot(self):
        for handler,slot in ((0x21,1),(0x22,2),(0x23,3)):
            adapter,calls=self.adapter(struct.pack('<II',11,1)+b'abc')
            value=receive_9189(adapter,handler,(0x9189,))
            self.assertEqual(value,struct.pack('<II',1,3)+b'abc')
            self.assertEqual(calls[0],('begin',0x9189,(slot,)))
            self.assertEqual(calls[-1],('complete',))
            self.assertEqual(calls.count(('complete',)),1)

    def test_failed_completion_or_malformed_body_never_returns_success(self):
        for body,response,error in ((struct.pack('<II',11,1)+b'abc',0x2002,RuntimeError),
                (b'broken',0x2001,ValueError)):
            adapter,calls=self.adapter(body,response)
            with self.assertRaises(error):receive_9189(adapter,0x21,(0x9189,))
            self.assertEqual(calls.count(('complete',)),1)

    def test_unsupported_readback_and_invalid_slot_never_call_adapter(self):
        for handler,ops in ((0x21,()),(0x21,(0x918a,)),(0, (0x9189,)),
                (True,(0x9189,)),(0x21,[0x9189]),(0x21,(True,0x9189))):
            with self.assertRaises(ValueError):receive_9189(None,handler,ops)

    def test_explicit_header_roundtrip_and_invalid_clearing(self):
        for payload in (b'',b'abc',bytes(range(256))):
            normalized=struct.pack('<II',1,len(payload))+payload
            self.assertEqual(decode_9189(encode_style(normalized)),normalized)
            invalid=struct.pack('<II',len(payload)+8,0)+payload
            self.assertEqual(decode_9189(invalid),bytes(len(invalid)))

    def test_preallocation_types_length_and_snapshot(self):
        original=struct.pack('<II',11,1)+b'abc'
        for bad in (11,None,True,'abc',original+b'x',memoryview(bytes(1048577)),
                *(original[:n] for n in range(len(original)))):
            with self.assertRaises(ValueError):decode_9189(bad)
        source=bytearray(original);decoded=decode_9189(source);source[-1]=0
        self.assertEqual(decoded[-3:],b'abc')
