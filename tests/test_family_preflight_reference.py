import hashlib
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from camera_install.accepted_modern_reference import inspect_extended17_style
from camera_install.family_preflight_reference import prepare_observed_preflight
from camera_install.rp_preflight_reference import prepare_rp_sequence
from camera_install.cipher_stream_reference import decode


class FamilyPreflightTests(unittest.TestCase):
    keys=(bytes(512),bytes(513))

    def style(self):
        value=bytearray(83044)
        struct.pack_into('<IIIH',value,0,1,83036,83036,0x84)
        struct.pack_into('<II',value,64,0xdeadbeef,0xdeadbeef)
        struct.pack_into('<HH',value,80,0x4c,252)
        struct.pack_into('<HHI',value,84,0x2fff,0xffff,0)
        for index in range(4):
            start=340+index*19652
            value[start:start+19652]=decode(bytes(19652),self.keys,0xb8ed if index%2==0 else 0x33137)
        value[78948:]=decode(bytes(4096),self.keys,0xb8ed)
        return bytes(value)

    def test_extended17_grammar_rejects_framing_high_bits_and_padding(self):
        value=self.style()
        self.assertEqual(inspect_extended17_style(value,self.keys)['gridNodes'],17)
        from camera_install.packed10_reference import packed_index
        used={packed_index(r,g,b) for r in range(10) for g in range(10) for b in range(10)}
        padding=78948+4*next(index for index in range(1024) if index not in used)
        for offset,word in ((0,0),(8,83035),(12,0x81),(64,0),(340,0x80000000),
                            (78948,0x80000000),(padding,1)):
            changed=bytearray(value)
            struct.pack_into('<I',changed,offset,word)
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                inspect_extended17_style(bytes(changed),self.keys)
        with self.assertRaises(ValueError):inspect_extended17_style(value[:-1],self.keys)

    def test_exact_profile_prepares_a_candidate_but_never_a_registration_sequence(self):
        descriptor=bytes(15076)
        operations=(0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127)
        job=SimpleNamespace(route='modern83076-dense',source_sha256='source',carrier=b'carrier',
                            send=SimpleNamespace(data=b'packet',opcode=0x9110,slot=3))
        args=dict(camera_id=0x80000421,descriptor=descriptor,slot_style=self.style(),slot=3,
            vendor_operations=operations,device_operations=operations)
        prefix='camera_install.family_preflight_reference.'
        with patch(prefix+'R8_DESCRIPTOR_SHA256',hashlib.sha256(descriptor).hexdigest()), \
                patch(prefix+'normalize_observed_raw',return_value=(bytes(14796),b'')), \
                patch(prefix+'prepare',return_value=job) as compile:
            result,report=prepare_observed_preflight(b'source',self.keys,**args)
            self.assertIs(result,job)
            self.assertEqual(compile.call_args.kwargs['route'],'modern83076-dense')
            self.assertFalse(report['liveRegistrationEnabled'])
            self.assertFalse(report['physicalAcceptanceEstablished'])
            with self.assertRaisesRegex(ValueError,'Registration state is not validated'):
                prepare_rp_sequence(job,())
            for changes in (dict(camera_id=True),dict(camera_id=0x80000422),dict(slot=True),
                    dict(descriptor=descriptor[:-1]+b'\x01'),dict(slot_style=self.style()[:-1]),
                    dict(device_operations=operations[:-1]),dict(vendor_operations=list(operations))):
                compile.reset_mock()
                with self.subTest(changes=list(changes)),self.assertRaises(ValueError):
                    prepare_observed_preflight(b'source',self.keys,**(args|changes))
                compile.assert_not_called()

    def test_rp_dispatch_preserves_its_existing_validation(self):
        with patch('camera_install.rp_preflight_reference.prepare_rp_preflight',return_value='RP') as compile:
            result=prepare_observed_preflight(b'owned',self.keys,camera_id=0x80000433,
                descriptor=b'descriptor',slot_style=b'style',slot=3,
                vendor_operations=(),device_operations=())
        self.assertEqual(result,'RP')
        self.assertEqual(compile.call_args.kwargs['camera_id'],0x80000433)


if __name__=='__main__':unittest.main()
