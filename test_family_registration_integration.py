import hashlib
import json
import struct
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch,call

import canon_engine as engine
from camera_install.camera_families_reference import CAMERA_FAMILIES,FAMILY_SIZES,camera_family
from camera_install.family_registration_reference import (prepare_family_registration,
    prepare_family_sequence,inspect_family_style,REQUIRED_OPERATIONS)
from camera_install.independent_registration_reference import register_in_session
from camera_install.descriptor_import_reference import (normalize_modern,normalize_compact,
    parameterless_matrix_reference)
from camera_install.compact_branch_reference import coefficient_policy,compact16752_plan
from camera_install.compact_carrier_reference import (build_observed_compact_integer,
    build_observed_compact16752)
from camera_install.accepted_modern_reference import build_accepted_modern17
from camera_install.legacy_dense9_carrier_reference import build_legacy_dense9_carrier
from camera_install.full33_packing_reference import encode_app_dense_full33
from camera_install.modern_header_reference import build_full33_prefix
from camera_install.control_section_reference import build_control_plain
from camera_install.cipher_stream_reference import decode
from camera_install.pf3_source_reference import write_source_fields
from camera_install.session_inputs_reference import SessionInputs,SlotObservation,collect_inputs
from camera_install.canon_event_receive_reference import CompletedEvents
from camera_install.canon_events import PropertyEvent


class FamilyRegistrationIntegrationTests(unittest.TestCase):
    keys=(bytes(512),bytes(513))
    operations=tuple(sorted(REQUIRED_OPERATIONS))

    @classmethod
    def setUpClass(cls):
        cls.fields=engine._generated_pf3_fields('Neutral')
        cls.raw=write_source_fields(cls.fields,cls.keys)
        cls.descriptors={}
        for modern in (False,True):
            size,stride,count=(14796,0x9a0,6) if modern else (7492,0x5d8,5)
            normalized=bytearray(size)
            struct.pack_into('<I',normalized,0,0x2000000b if modern else 0x2000000a)
            for ordinal in range(count):
                for index in (1,2):
                    offset=ordinal*stride+0x104+index*240
                    normalized[offset:offset+240]=parameterless_matrix_reference()
                    if modern:
                        struct.pack_into('<HH',normalized,ordinal*stride+0x2d0+index*0x104,1,0)
                        axis=ordinal*stride+0x3f8+index*0x1e4
                        struct.pack_into('<HH',normalized,axis,2,2)
                        groups=([0,0,0,0,1,0,0,0,2,0,0,0,3,0,0,0,5,0,0,0],
                                [0,180,50,50,1,0,0,0,2,360,100,100,3,0,0,0,5,5,5,5])
                        for group,words in enumerate(groups):
                            struct.pack_into('<20h',normalized,axis+4+group*40,*words)
                        struct.pack_into('<H',normalized,ordinal*stride+0x1ee+index*2,1)
            normalized=bytes(normalized)
            raw=(normalize_modern if modern else normalize_compact)(normalized,cls.keys)+bytes(280)
            cls.descriptors[modern]=(raw,normalized)
        cls.baselines={}

    def fixture(self,identifier,style='Neutral'):
        family,_=CAMERA_FAMILIES[identifier]
        modern=family>=7 or (family==6 and not coefficient_policy(identifier))
        raw_descriptor,normalized=self.descriptors[modern]
        key=(family,modern,style)
        if key not in self.baselines:
            fields=engine._generated_pf3_fields(style);fields[0x1002]=(2,b'Baseline\0')
            if family<=2:
                carrier=build_legacy_dense9_carrier(fields,self.keys,struct.pack('<I',1460)+bytes(1456),
                    total_size=FAMILY_SIZES[family])
            elif family<=6 and coefficient_policy(identifier):
                paths=('cache','cache') if family==3 else ('cache',)*4
                carrier=build_observed_compact_integer(fields,normalized,self.keys,
                    block_paths=paths,internal_selector=identifier,total_size=FAMILY_SIZES[family])
            elif family<=7:
                plan=compact16752_plan(normalized,engine.PICTURE_STYLE_IDS[style],identifier,0,family,base_callback_noop=True)
                paths=tuple('dense-pixel' if i<2 and p=='pixel' else p for i,p in enumerate(plan['blockPaths']))
                carrier=build_observed_compact16752(fields,normalized,self.keys,
                    block_paths=paths,pixel_scale=plan['pixelScale'],internal_selector=identifier)
            elif family<=9:
                carrier=build_accepted_modern17(fields,normalized,self.keys,extended=family==9)
            else:
                control=build_control_plain({i:fields[i] for i in (0x100a,0x100d)})
                encoded=control[:8]+decode(control[8:],self.keys,0x22e1)
                carrier=build_full33_prefix(fields,encoded)+b''.join(
                    encode_app_dense_full33(fields[i][1]) for i in (0x1070,0x1071))
            self.baselines[key]=carrier[:8]+carrier[40:]
        return dict(camera_id=identifier,descriptor=raw_descriptor,slot_style=self.baselines[key],
            slot=3,vendor_operations=self.operations,device_operations=self.operations)

    def test_every_catalogued_identifier_negotiates_a_real_compiler_without_canon(self):
        seen=set()
        with patch('canon_engine.EdsCFParse',side_effect=AssertionError('Canon forbidden')):
            for identifier,(family,model) in CAMERA_FAMILIES.items():
                with self.subTest(model=model):
                    args=self.fixture(identifier)
                    job,report=prepare_family_registration(self.raw,self.keys,**args)
                    self.assertEqual(len(job.carrier),FAMILY_SIZES[family])
                    self.assertEqual(report['model'],model)
                    self.assertEqual(report['serializerFamily'],family)
                    self.assertFalse(report['physicalAcceptanceEstablished'])
                    self.assertEqual(job.send.opcode,0x9110)
                    seen.add(family)
        self.assertEqual(seen,set(range(1,11)))

    def test_full_session_for_each_family_preserves_live_state_and_verifies_selected_slot(self):
        representatives={family:identifier for identifier,(family,_) in CAMERA_FAMILIES.items()}
        for family,identifier in representatives.items():
            with self.subTest(family=family):
                options=self.fixture(identifier)
                slot=family%3+1;options['slot']=slot
                if family%2==0:
                    options['device_operations']=options['vendor_operations']=self.operations+(0x9192,)
                job,_=prepare_family_registration(self.raw,self.keys,**options)
                control=bytearray(24 if family<=4 else 32)
                for _,offset,value,_ in job.control_words:
                    if offset+4<=len(control):control[offset:offset+4]=value
                control[16:24]=b'PRIVATE!'
                if family==5:control[24:32]=b'OPAQUE!!'
                state=SlotObservation(0x20+slot,0 if family<=4 else 1,0x40+slot,bytes(control))
                session=Mock()
                baseline=options['slot_style'];expected=job.carrier[:8]+job.carrier[40:]
                self.assertNotEqual(baseline,expected)
                session.request_descriptor.return_value=options['descriptor']
                session.request_slot_style.side_effect=[baseline,baseline,expected]
                session.observed_inputs=SessionInputs(identifier,options['descriptor'],(state,))
                commands=Mock()
                with tempfile.TemporaryDirectory() as temporary, \
                     patch('camera_install.registration_sequence_reference.transfer') as transfer:
                    backup=Path(temporary)/'baseline.bin'
                    report=register_in_session(session,(self.raw,self.keys),'writer',commands,slot=slot,
                        vendor_operations=options['vendor_operations'],device_operations=options['device_operations'],
                        backup_path=backup,allow_experimental_write=True)
                    self.assertEqual(backup.read_bytes(),baseline)
                self.assertEqual(transfer.call_count,2)
                self.assertEqual(transfer.call_args_list[0].args[1],job.send.opcode)
                self.assertEqual(transfer.call_args_list[1].args[-1][-len(control):],bytes(control))
                self.assertEqual(session.request_slot_style.call_args_list,[call(0x20+slot)]*3)
                if family<=2:session.request_descriptor.assert_not_called()
                else:session.request_descriptor.assert_called_once_with()
                self.assertEqual(commands.execute.call_args_list,[call(0x911b,(1,)),call(0x911c,())])
                self.assertTrue(report['requestedSlotContentMatched'])
                self.assertNotIn('PRIVATE',json.dumps(report))

    def test_each_family_compiles_every_generated_base_in_its_reconstructed_domain(self):
        representatives={family:identifier for identifier,(family,_) in CAMERA_FAMILIES.items()}
        for family,identifier in representatives.items():
            for style,selector in engine.PICTURE_STYLE_IDS.items():
                with self.subTest(family=family,style=style):
                    raw=write_source_fields(engine._generated_pf3_fields(style),self.keys)
                    if selector==0x88 and (family<=5 or coefficient_policy(identifier)):
                        with self.assertRaisesRegex(ValueError,'Selected base'):
                            prepare_family_registration(raw,self.keys,**self.fixture(identifier))
                        continue
                    job,report=prepare_family_registration(raw,self.keys,**self.fixture(identifier,style))
                    self.assertEqual(inspect_family_style(job.carrier[:8]+job.carrier[40:],self.keys,family),selector)
                    self.assertEqual(len(job.carrier),FAMILY_SIZES[family])
                    self.assertFalse(report['physicalAcceptanceEstablished'])

    def test_fine_detail_allows_5ds_and_5dsr_but_not_coefficient_7d2(self):
        raw=write_source_fields(engine._generated_pf3_fields('Fine Detail'),self.keys)
        for identifier in (0x80000382,0x80000401):
            with self.subTest(camera=hex(identifier)):
                job,report=prepare_family_registration(raw,self.keys,**self.fixture(identifier,'Fine Detail'))
                self.assertEqual(len(job.carrier),16752)
                self.assertEqual(inspect_family_style(job.carrier[:8]+job.carrier[40:],self.keys,6),0x88)
                self.assertFalse(report['physicalAcceptanceEstablished'])
        with self.assertRaisesRegex(ValueError,'Selected base'):
            prepare_family_registration(raw,self.keys,**self.fixture(0x80000289))

    def test_pf3_reference_bank_is_preserved_but_does_not_change_class5_or6_output(self):
        fields=dict(self.fields)
        for identifier in (0x1011,0x1009,0x1030,0x1031,0x1032,0x1033,
                           0x1034,0x1035,0x1002,0x100a,0x1021,0x1029,0x1018,0x100d):
            fields[identifier|0x8000]=fields[identifier]
        fields[0x9011]=(4,struct.pack('<I',1))
        fields[0x9032]=(4,struct.pack('<i',-4))
        fields[0x9002]=(2,b'Reference name differs\0')
        raw=write_source_fields(fields,self.keys)
        identifiers=[identifier for identifier,(family,_) in CAMERA_FAMILIES.items() if family in (5,6)]
        for identifier in identifiers:
            with self.subTest(camera=hex(identifier)):
                options=self.fixture(identifier)
                ordinary,_=prepare_family_registration(self.raw,self.keys,**options)
                with_reference,report=prepare_family_registration(raw,self.keys,**options)
                self.assertEqual(with_reference.carrier,ordinary.carrier)
                self.assertNotEqual(with_reference.source_sha256,ordinary.source_sha256)
                self.assertEqual(engine._independent_editor_properties(fields,((0x40009032,4),))[0x40009032],struct.pack('<i',-4))
                self.assertFalse(report['physicalAcceptanceEstablished'])
        from camera_install.pf3_source_reference import read_source_fields
        self.assertEqual(dict(read_source_fields(raw,self.keys)),fields)
        unsupported=bytearray(raw);unsupported[2]=0x20
        with self.assertRaisesRegex(ValueError,'Unsupported PF3 envelope'):
            prepare_family_registration(bytes(unsupported),self.keys,**self.fixture(0x03740000))

    def test_legacy_events_do_not_invent_extended_state_and_conflicts_fail(self):
        control=bytes(range(24))
        event=PropertyEvent(0xd160,struct.pack('<II',32,0x41)+control)
        def batch(events):return CompletedEvents(tuple(events),1,100)
        state=collect_inputs(batch([event])).slots[0]
        self.assertEqual(state,SlotObservation(0x21,0,0x41,control))
        other=PropertyEvent(0xd163,struct.pack('<III',44,1,0x41)+bytes(32))
        for events in ([event,other],[PropertyEvent(0xd160,event.value[:-1])]):
            with self.assertRaises(ValueError):collect_inputs(batch(events))

    def test_unknown_model_bad_style_caps_and_control_conflict_stop_before_write(self):
        options=self.fixture(0x80000421)
        for change in (dict(camera_id=True),dict(slot=True),
                dict(slot_style=options['slot_style'][:-1]),dict(device_operations=()),
                dict(descriptor=bytes(100))):
            with self.subTest(change=tuple(change)),self.assertRaises(ValueError):
                prepare_family_registration(self.raw,self.keys,**(options|change))
        compact=self.fixture(0x80000433)
        generic_compact,_=prepare_family_registration(self.raw,self.keys,
            **(compact|dict(camera_id=0x12345678)))
        self.assertEqual(len(generic_compact.carrier),16752)
        self.assertEqual(camera_family(0x12345678)[0],7)
        for identifier,(family,_) in CAMERA_FAMILIES.items():
            self.assertEqual(camera_family(identifier)[0],family)
        generic,report=prepare_family_registration(self.raw,self.keys,
            **(options|dict(camera_id=0x12345678)))
        self.assertEqual(report['serializerFamily'],9)
        self.assertEqual(len(generic.carrier),83076)
        job,_=prepare_family_registration(self.raw,self.keys,**options)
        with self.assertRaises(ValueError):prepare_family_sequence(job,())
        state=SlotObservation(0x23,1,0x43,bytes([255])*32)
        with self.assertRaises(ValueError):prepare_family_sequence(job,(state,))
        corrupted=bytearray(options['slot_style']);corrupted[340]^=128
        # Guaranteed reserved high bit in the decrypted first 17-node word.
        corrupted[343]^=0x80
        with self.assertRaises(ValueError):inspect_family_style(bytes(corrupted),self.keys,9)


if __name__=='__main__':unittest.main()
