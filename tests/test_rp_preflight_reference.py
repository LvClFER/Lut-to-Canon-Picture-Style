import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import canon_engine as engine
from camera_install.rp_preflight_reference import prepare_rp_preflight,load_preflight_source
from camera_install.descriptor_import_reference import normalize_modern
from camera_install.pf3_source_reference import write_source_fields
from camera_install.compact_carrier_reference import build_accepted_compact16752
from camera_install.rp_preflight_reference import preflight_registration_sequence
from camera_install.rp_preflight_reference import SlotControlMismatch
from camera_install.session_inputs_reference import SlotObservation


class RpPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=(bytes(512),bytes(513))
        cls.fields=engine._generated_pf3_fields('Neutral')
        cls.raw=write_source_fields(cls.fields,cls.keys)
        normalized=bytearray(14796)
        struct.pack_into('<I',normalized,0,0x2000000b)
        for index in (1,2):struct.pack_into('<H',normalized,0x1ee+3*0x9a0+index*2,1)
        cls.descriptor=normalize_modern(bytes(normalized),cls.keys)+bytes(280)
        carrier=build_accepted_compact16752(cls.fields,bytes(normalized),cls.keys,internal_selector=0x80000433)
        cls.style=carrier[:8]+carrier[40:]
        cls.operations=(0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127)

    def candidate(self,**changes):
        args=dict(camera_id=0x80000433,descriptor=self.descriptor,slot_style=self.style,slot=3,
            vendor_operations=self.operations,device_operations=self.operations)
        args.update(changes)
        with patch('camera_install.rp_preflight_reference.RP_DESCRIPTOR_SHA256',hashlib.sha256(self.descriptor).hexdigest()):
            return prepare_rp_preflight(self.raw,self.keys,**args)

    def test_profile_gates_grammar_and_caps_select_a_candidate_without_acceptance_claim(self):
        job,report=self.candidate()
        self.assertEqual(job.route,'compact16752-dense-pixel')
        self.assertEqual(report['descriptorGateWords'],[1,1])
        self.assertEqual((report['opcode'],report['slot'],report['packetBytes']),('0x9110',3,16728))
        self.assertFalse(report['stateFreshnessEstablished'])
        self.assertFalse(report['physicalAcceptanceEstablished'])

    def test_complete_sequence_preflight_is_local_private_and_not_write_permission(self):
        job,_ = self.candidate()
        control = bytearray(32)
        for offset, header in ((0,76),(4,80),(8,84),(12,88),(24,100),(28,104)):
            control[offset:offset+4] = job.carrier[header:header+4]
        control[16:24] = b'PRIVATE!'
        control = bytes(control)
        state = SlotObservation(0x23,1,0x43,control)
        with patch('camera_install.registration_sequence_reference.transfer',
                   side_effect=AssertionError('No transport permitted')):
            report = preflight_registration_sequence(job,(state,))
        self.assertTrue(report['sequencePlanValidated'])
        self.assertEqual((report['statePacketBytes'],report['stateProperty']),(52,'0xd165'))
        for flag in ('writeAuthorized','stateFreshnessEstablished','physicalAcceptanceEstablished'):
            self.assertFalse(report[flag])
        self.assertNotIn('PRIVATE',json.dumps(report))
        for offset in (0,4,8,12,24,28):
            changed = bytearray(control)
            changed[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaisesRegex(SlotControlMismatch,'controls differ') as raised:
                preflight_registration_sequence(job,(SlotObservation(0x23,1,0x43,bytes(changed)),))
            self.assertEqual(len(raised.exception.differences),1)
            self.assertNotIn('PRIVATE',json.dumps(raised.exception.differences))
        changed=bytearray(control)
        changed[:4]=(-2).to_bytes(4,'little',signed=True)
        with self.assertRaises(SlotControlMismatch) as raised:
            preflight_registration_sequence(job,(SlotObservation(0x23,1,0x43,bytes(changed)),))
        self.assertEqual(raised.exception.differences[0],dict(control='Contrast',slotValue=-2,candidateValue=0))
        for states in ((),(state,state),(SlotObservation(0x21,1,0x41,control),),
                       (SlotObservation(0x23,0,0x43,control),),
                       (SlotObservation(0x23,1,0x41,control),),
                       (SlotObservation(0x23,1,0x43,b'short'),)):
            with self.subTest(states=states),self.assertRaises(ValueError):
                preflight_registration_sequence(job,states)

    def test_unknown_id_changed_descriptor_missing_operation_and_wrong_style_fail_closed(self):
        for changes in (dict(camera_id=True),dict(camera_id=0x80000487),dict(slot=True),
                dict(descriptor=self.descriptor[:-1]+b'\x01'),dict(slot_style=bytes(16720)),
                dict(device_operations=self.operations[:-1]),dict(vendor_operations=self.operations[1:])):
            with self.subTest(changes=list(changes)),patch('camera_install.rp_preflight_reference.prepare') as compile:
                with self.assertRaises(ValueError):self.candidate(**changes)
                compile.assert_not_called()
        changed=bytearray(normalize_modern(self.descriptor[:14796],self.keys))
        struct.pack_into('<H',changed,0x1ee+3*0x9a0+2,0)
        descriptor=normalize_modern(bytes(changed),self.keys)+bytes(280)
        with patch('camera_install.rp_preflight_reference.RP_DESCRIPTOR_SHA256',hashlib.sha256(descriptor).hexdigest()):
            with self.assertRaisesRegex(ValueError,'gates'):
                prepare_rp_preflight(self.raw,self.keys,camera_id=0x80000433,descriptor=descriptor,
                    slot_style=self.style,slot=3,vendor_operations=self.operations,device_operations=self.operations)

    def test_project_extracts_and_bootstraps_before_any_device_dependency(self):
        from project_state import ProjectDocument
        with tempfile.TemporaryDirectory() as temporary,patch('canon_engine.EdsCFParse',side_effect=AssertionError('Canon forbidden')):
            root=Path(temporary); source=root/'own.pf3';source.write_bytes(self.raw)
            project=ProjectDocument(edit=dict(base_name='Imported PF3',basePictureStyle='Imported PF3',
                base_path=str(source),custom_pf3=str(source),luts=[]))
            bundle=root/'own.canonstyleproject'
            engine.save_compiled_style_project(None,source,bundle,project,source)
            source.unlink()
            with patch('canon_engine.runtime_cache_dir',side_effect=PermissionError('global cache unavailable')) as cache:
                raw,_keys=load_preflight_source(bundle,root/'reopened')
            cache.assert_not_called()
            self.assertEqual(raw,self.raw)


if __name__=='__main__':unittest.main()
