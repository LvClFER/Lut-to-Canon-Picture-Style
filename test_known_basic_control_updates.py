import struct
import tempfile
from pathlib import Path
import unittest
from dataclasses import replace
from unittest.mock import Mock,patch,call

from camera_install.family_registration_reference import prepare_family_registration,prepare_family_sequence
from camera_install.session_inputs_reference import SlotObservation,SessionInputs
from camera_install.remote_session_reference import RemoteEventSession
from camera_install.event_mode_plan_reference import plan_event_modes
from camera_install.canon_event_receive_reference import CompletedEvents
from camera_install.canon_events import PropertyEvent
from camera_install.rp_preflight_reference import SlotControlMismatch
import test_family_registration_integration as fixtures


class KnownBasicControlPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.FamilyRegistrationIntegrationTests.setUpClass();cls.fixture=fixtures.FamilyRegistrationIntegrationTests()
        cls.job,_=prepare_family_registration(cls.fixture.raw,cls.fixture.keys,**cls.fixture.fixture(0x80000433))

    def state(self):
        control=bytearray(32)
        for _name,offset,value,_signed in self.job.control_words:control[offset:offset+4]=value
        control[:4]=struct.pack('<i',-1);control[16:24]=b'PRIVATE!'
        return SlotObservation(0x23,1,0x43,bytes(control))

    def test_opt_in_changes_only_known_words_and_preserves_default_block(self):
        before=self.state();original=before.control
        with self.assertRaises(SlotControlMismatch):prepare_family_sequence(self.job,(before,))
        sequence=prepare_family_sequence(self.job,(before,),update_known_basic_controls=True)
        actual=sequence.state.data[-32:]
        self.assertEqual(actual[:4],bytes(4))
        self.assertEqual(actual[4:],original[4:])
        self.assertEqual(actual[16:24],b'PRIVATE!')
        self.assertEqual(before.control,original)
        self.assertEqual(sequence.style,self.job.send)

    def test_controller_requires_changed_state_after_two_writes_and_always_cleans_up(self):
        from camera_install.independent_registration_reference import register_in_session
        helper=KnownBasicControlEventTests();before=self.state()
        after=replace(before,control=bytes(4)+before.control[4:])
        expected=self.job.carrier[:8]+self.job.carrier[40:]
        baseline=bytearray(expected);baseline[12]^=1;baseline=bytes(baseline)
        for outcome in ('confirmed','missing','unknown'):
            commands=Mock();packets=[]
            session=RemoteEventSession(commands,Mock(),
                plan_event_modes(1,helper_predicate=True,registry_option_enabled=False))
            final=[helper.style(expected[8:])]
            if outcome=='confirmed':final.append(helper.event(after))
            if outcome=='unknown':final.append(helper.event(replace(after,control=after.control[:16]+b'changed!'+after.control[24:])))
            batches=[helper.batch(helper.event(before)),helper.batch(helper.style(baseline[8:])),
                     helper.batch(helper.style(baseline[8:])),helper.batch(*final)]
            batches += [helper.batch()]*6
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as temporary:
                backup=Path(temporary)/'baseline.bin'
                def transfer(_writer,_opcode,_parameters,payload):
                    self.assertEqual(backup.read_bytes(),baseline);packets.append(payload)
                prefix='camera_install.independent_registration_reference.'
                with patch('camera_install.remote_session_reference.drain',side_effect=batches), \
                        patch(prefix+'prepare_family_registration',return_value=(self.job,{})), \
                        patch.object(session,'request_descriptor',return_value=b'descriptor'), \
                        patch('camera_install.registration_sequence_reference.transfer',side_effect=transfer):
                    def run():
                        with session:
                            return register_in_session(session,(b'source',b'keys'),'writer',commands,slot=3,
                                vendor_operations=(),device_operations=(),backup_path=backup,
                                allow_experimental_write=True,update_known_basic_controls=True)
                    if outcome=='confirmed':
                        report=run()
                        self.assertTrue(report['requestedSlotStateMatched'])
                        self.assertEqual(report['knownBasicControlChanges'],
                            [dict(control='Contrast',slotValue=-1,candidateValue=0)])
                    else:
                        with self.assertRaises((RuntimeError,ValueError)):run()
                self.assertEqual(len(packets),2)
                self.assertEqual(packets[-1][-32:],after.control)
                queries=[c.args[1] for c in commands.execute.call_args_list if c.args[0]==0x9127]
                self.assertEqual(queries,[(0xd172,)]*3)
                self.assertEqual(commands.execute.call_args_list[-2:],
                    [call(0x9115,(0,)),call(0x9114,(0,))])

    def test_only_documented_word_positions_and_ranges_are_accepted(self):
        before=self.state()
        for name,invalid in (('Contrast',5),('Strength',8),('Saturation',-5),
                             ('Color Tone',5),('Fineness',0),('Threshold',6)):
            words=tuple((n,o,invalid.to_bytes(4,'little',signed=s) if n==name else v,s)
                        for n,o,v,s in self.job.control_words)
            with self.subTest(control=name),self.assertRaisesRegex(ValueError,'range'):
                prepare_family_sequence(replace(self.job,control_words=words),(before,),update_known_basic_controls=True)
        for words in ((('Unknown',16,bytes(4),False),),
                      (('Contrast',16,bytes(4),True),),self.job.control_words+(self.job.control_words[0],)):
            with self.subTest(words=tuple(w[0] for w in words)),self.assertRaisesRegex(ValueError,'Unknown or duplicate'):
                prepare_family_sequence(replace(self.job,control_words=words),(before,),update_known_basic_controls=True)
        for value in (1,None,'yes'):
            with self.assertRaisesRegex(ValueError,'boolean'):
                prepare_family_sequence(self.job,(before,),update_known_basic_controls=value)
        self.assertEqual(before.control[16:24],b'PRIVATE!')

    def test_legacy24_updates_four_words_without_inventing_extended_bytes(self):
        before=replace(self.state(),marker=0,control=self.state().control[:24])
        job=replace(self.job,control_words=self.job.control_words[:4])
        sequence=prepare_family_sequence(job,(before,),update_known_basic_controls=True)
        self.assertEqual(len(sequence.state.data),40)
        self.assertFalse(sequence.state.extended)
        self.assertEqual(sequence.state.data[-24:],bytes(4)+before.control[4:])
        mixed=replace(before,control=self.state().control)
        with self.assertRaisesRegex(ValueError,'wire layout'):
            prepare_family_sequence(job,(mixed,),update_known_basic_controls=True)

    def test_known_control_updates_reach_each_family_with_both_state_layouts(self):
        from camera_install.independent_registration_reference import register_in_session
        representatives={family:identifier for identifier,(family,_name) in fixtures.CAMERA_FAMILIES.items()}
        for family,identifier in representatives.items():
            options=self.fixture.fixture(identifier)
            job,_=prepare_family_registration(self.fixture.raw,self.fixture.keys,**options)
            expected=job.carrier[:8]+job.carrier[40:]
            for length in (24,32):
                with self.subTest(family=family,controlBytes=length):
                    control=bytearray(length);control[16:24]=b'PRIVATE!'
                    for offset,number,signed in ((0,-1,True),(4,6,False),(8,2,True),
                            (12,3,True),(24,5,False),(28,4,False)):
                        if offset+4<=length:control[offset:offset+4]=number.to_bytes(4,'little',signed=signed)
                    before=SlotObservation(0x23,int(length==32),0x43,bytes(control))
                    session=Mock()
                    session.observed_inputs=SessionInputs(identifier,None,(before,))
                    session.request_descriptor.return_value=options['descriptor']
                    session.request_slot_style.return_value=options['slot_style']
                    session.request_registered_slot_style.return_value=expected
                    commands=Mock();packets=[]
                    with tempfile.TemporaryDirectory() as temporary:
                        backup=Path(temporary)/'baseline.bin'
                        def transfer(_writer,_opcode,_parameters,payload):
                            self.assertEqual(backup.read_bytes(),options['slot_style'])
                            packets.append(payload)
                        with patch('camera_install.registration_sequence_reference.transfer',side_effect=transfer):
                            report=register_in_session(session,(self.fixture.raw,self.fixture.keys),'writer',commands,
                                slot=3,vendor_operations=self.fixture.operations,device_operations=self.fixture.operations,
                                backup_path=backup,allow_experimental_write=True,update_known_basic_controls=True)
                    self.assertEqual(len(packets),2)
                    actual=packets[-1][-length:]
                    self.assertEqual(actual[16:24],b'PRIVATE!')
                    represented={offset for _name,offset,_value,_signed in job.control_words if offset+4<=length}
                    for offset in range(0,length,4):
                        wanted=next((value for _name,o,value,_signed in job.control_words if o==offset),None)
                        self.assertEqual(actual[offset:offset+4],wanted if offset in represented else control[offset:offset+4])
                    call_before,call_after=session.request_registered_slot_style.call_args.args
                    self.assertEqual(call_before,before)
                    self.assertEqual(call_after,replace(before,control=actual))
                    self.assertEqual(session.request_slot_style.call_args_list,[call(0x23)]*2)
                    self.assertEqual(commands.execute.call_args_list,[call(0x911b,(1,)),call(0x911c,())])
                    self.assertTrue(report['requestedSlotStateMatched'])
                    self.assertEqual(len(report['knownBasicControlChanges']),len(represented))
                    self.assertNotIn('PRIVATE',repr(report))


class KnownBasicControlEventTests(unittest.TestCase):
    def observation(self,control=None,*,legacy=False):
        return SlotObservation(0x23,0 if legacy else 1,0x43,
            bytes(24 if legacy else 32) if control is None else control)

    def event(self,state):
        if state.marker:
            return PropertyEvent(state.handler_selector+0xd142,
                struct.pack('<III',44,state.marker,state.selector)+state.control)
        return PropertyEvent(state.handler_selector+0xd13f,
            struct.pack('<II',32,state.selector)+state.control)

    def batch(self,*events):return CompletedEvents(tuple(events),1,20+sum(len(e.value) for e in events))

    def run_confirmation(self,before,after,batches):
        commands=Mock();session=RemoteEventSession(commands,Mock(),
            plan_event_modes(1,helper_predicate=True,registry_option_enabled=False))
        with patch('camera_install.remote_session_reference.drain',side_effect=[self.batch(self.event(before)),*batches]):
            with session:result=session.request_registered_slot_style(before,after)
        return result,commands

    def style(self,value=b'abc'):
        return PropertyEvent(0xd172,struct.pack('<II',len(value)+8,1)+value)

    def test_expected_state_and_style_confirm_without_directed_state_request(self):
        for legacy in (False,True):
            before=self.observation(legacy=legacy)
            after=replace(before,control=struct.pack('<i',1)+before.control[4:])
            with self.subTest(legacy=legacy):
                result,commands=self.run_confirmation(before,after,
                    [self.batch(self.event(before),self.event(after),self.style())])
                self.assertEqual(result,struct.pack('<II',1,3)+b'abc')
                queries=[call.args for call in commands.execute.call_args_list if call.args[0]==0x9127]
                self.assertEqual(queries,[(0x9127,(0xd172,))])

    def test_late_expected_event_is_required_and_empty_reads_are_bounded(self):
        before=self.observation();after=replace(before,control=struct.pack('<i',1)+before.control[4:])
        self.run_confirmation(before,after,[self.batch(self.style()),self.batch(self.event(after))])
        with self.assertRaisesRegex(RuntimeError,'not observed'):
            self.run_confirmation(before,after,[self.batch(self.style())]+[self.batch()]*6)

    def test_unknown_word_change_reversion_and_wrong_style_never_confirm(self):
        before=self.observation();after=replace(before,control=struct.pack('<i',1)+before.control[4:])
        bad=bytearray(after.control);bad[16]=1;unknown=replace(after,control=bytes(bad))
        batches=([self.batch(self.event(unknown),self.style())],
                 [self.batch(self.event(after),self.event(before),self.style())],
                 [self.batch(self.style()),self.batch(self.event(after),self.style(b'wrong'))])
        for events in batches:
            with self.subTest(events=len(events)),self.assertRaises(ValueError):
                self.run_confirmation(before,after,events)

    def test_transition_requires_live_matching_metadata(self):
        before=self.observation();after=replace(before,control=struct.pack('<i',1)+before.control[4:])
        commands=Mock();session=RemoteEventSession(commands,Mock(),
            plan_event_modes(1,helper_predicate=True,registry_option_enabled=False))
        with patch('camera_install.remote_session_reference.drain',return_value=self.batch(self.event(before))):
            with session:
                for invalid in (replace(after,selector=0x42),replace(after,marker=0),replace(after,control=after.control[:24])):
                    with self.assertRaises(ValueError):session.request_registered_slot_style(before,invalid)
                with self.assertRaises(ValueError):session.request_registered_slot_style(after,before)
        self.assertFalse(any(call.args[0]==0x9127 for call in commands.execute.call_args_list))
