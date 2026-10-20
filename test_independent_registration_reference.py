import hashlib
from pathlib import Path
import tempfile
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch, call

from camera_install.independent_registration_reference import register_in_session, register_open_connection
from camera_install.session_inputs_reference import SessionInputs, SlotObservation
from camera_install.canon_event_receive_reference import CompletedEvents
from camera_install.canon_events import PropertyEvent
from camera_install.wpd_data_phase_reference import COMMON, MTP
import test_rp_preflight_reference as fixtures


class IndependentRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RpPreflightTests.setUpClass()
        cls.fixture = fixtures.RpPreflightTests()

    def inputs(self):
        job,_ = self.fixture.candidate()
        expected = job.carrier[:8] + job.carrier[40:]
        baseline = bytearray(expected)
        baseline[12] ^= 1  # Different caption, same valid compact grammar/controls.
        control = bytearray(32)
        for offset, header in ((0,76),(4,80),(8,84),(12,88),(24,100),(28,104)):
            control[offset:offset+4] = job.carrier[header:header+4]
        session = Mock()
        session.request_descriptor.return_value = self.fixture.descriptor
        session.request_slot_style.side_effect = [bytes(baseline), bytes(baseline), expected]
        session.observed_inputs = SessionInputs(0x80000433,self.fixture.descriptor,
            (SlotObservation(0x23,1,0x43,bytes(control)),))
        return session,bytes(baseline),expected

    def run_flow(self,session,backup,commands,**changes):
        options = dict(slot=3,vendor_operations=self.fixture.operations,
            device_operations=self.fixture.operations,backup_path=backup,
            allow_experimental_write=True)
        options.update(changes)
        with patch('camera_install.rp_preflight_reference.RP_DESCRIPTOR_SHA256',
                   hashlib.sha256(self.fixture.descriptor).hexdigest()):
            return register_in_session(session,(self.fixture.raw,self.fixture.keys),
                                       'injected writer',commands,**options)

    def test_complete_flow_backs_up_before_writes_and_compares_after_unlock(self):
        session,baseline,expected = self.inputs()
        commands = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            backup = Path(temporary)/'slot3.bin'
            def transfer(*args):
                self.assertEqual(backup.read_bytes(),baseline)
                self.assertEqual(commands.execute.call_args_list,[call(0x911b,(1,))])
            with patch('camera_install.registration_sequence_reference.transfer',side_effect=transfer) as send:
                report = self.run_flow(session,backup,commands)
            self.assertEqual(send.call_count,2)
        self.assertEqual(commands.execute.call_args_list,[call(0x911b,(1,)),call(0x911c,())])
        self.assertEqual(session.request_slot_style.call_args_list,[call(0x23)]*3)
        self.assertTrue(report['requestedSlotContentMatched'])
        self.assertTrue(report['visualConfirmationRequired'])
        self.assertFalse(report['physicalAcceptanceEstablished'])
        self.assertFalse(report['automaticRetry'])

    def test_absent_permission_has_no_session_activity(self):
        for consent in (False,1,None):
            session = Mock()
            with self.subTest(consent=consent),self.assertRaises(ValueError):
                self.run_flow(session,'unused',Mock(),allow_experimental_write=consent)
            self.assertEqual(session.mock_calls,[])

    def test_connection_scope_and_capabilities_fail_before_remote_modes(self):
        connection = Mock()
        with self.assertRaises(ValueError):
            register_open_connection(connection,None,slot=3,backup_path='unused')
        self.assertEqual(connection.mock_calls,[])
        connection.capabilities.return_value = {(COMMON,1003):0,(MTP,1005):()}
        with self.assertRaisesRegex(ValueError,'operations'):
            register_open_connection(connection,None,slot=3,backup_path='unused',
                                     allow_experimental_write=True)
        connection.commands.assert_not_called()
        connection.data.assert_not_called()
        connection.capabilities.return_value[(MTP,1005)] = self.fixture.operations
        prefix = 'camera_install.independent_registration_reference.'
        with patch(prefix+'receive',return_value=b'info'), \
                patch(prefix+'decode_device_info',return_value=SimpleNamespace(operations=(0x9110,))):
            with self.assertRaisesRegex(ValueError,'complete registration profile'):
                register_open_connection(connection,None,slot=3,backup_path='unused',
                                         allow_experimental_write=True)
        connection.commands.assert_not_called()

    def test_noop_changed_slot_or_existing_backup_prevents_lock_and_transfer(self):
        for reason in ('noop','changed','backup','state'):
            session,baseline,expected = self.inputs()
            if reason=='noop': session.request_slot_style.side_effect=[expected]
            if reason=='changed': session.request_slot_style.side_effect=[baseline,expected]
            if reason=='state': session.observed_inputs=SessionInputs(0x80000433,None,())
            with tempfile.TemporaryDirectory() as temporary:
                backup = Path(temporary)/'slot3.bin'
                if reason=='backup': backup.write_bytes(b'preserve')
                commands = Mock()
                with patch('camera_install.registration_sequence_reference.transfer') as send:
                    with self.subTest(reason=reason),self.assertRaises((ValueError,FileExistsError)):
                        self.run_flow(session,backup,commands)
                    send.assert_not_called()
                    commands.execute.assert_not_called()
                if reason=='backup': self.assertEqual(backup.read_bytes(),b'preserve')

    def test_write_failure_unlocks_once_and_never_retries(self):
        session,_,_ = self.inputs()
        commands = Mock()
        with tempfile.TemporaryDirectory() as temporary, \
                patch('camera_install.registration_sequence_reference.transfer',
                      side_effect=RuntimeError('transport failed')) as send:
            with self.assertRaisesRegex(RuntimeError,'transport failed'):
                self.run_flow(session,Path(temporary)/'slot3.bin',commands)
        send.assert_called_once()
        self.assertEqual(commands.execute.call_args_list,[call(0x911b,(1,)),call(0x911c,())])
        self.assertEqual(session.request_slot_style.call_count,2)

    def test_real_session_and_wpd_maps_complete_the_flow_with_injected_device(self):
        session,baseline,expected = self.inputs()
        state = session.observed_inputs.slots[0]
        startup = CompletedEvents((PropertyEvent(0xd116,struct.pack('<I',0x80000433)),
            PropertyEvent(0xd165,struct.pack('<III',44,1,0x43)+state.control)),1,80)
        descriptor = self.fixture.descriptor
        def batch(code,value):
            return CompletedEvents((PropertyEvent(code,value),),1,len(value)+20)
        def style(value):
            return batch(0xd172,struct.pack('<II',len(value),1)+value[8:])
        events = [startup,batch(0xd17f,struct.pack('<I',len(descriptor)+4)+descriptor),
                  style(baseline),style(baseline),style(expected)]
        calls,packets = [],[]
        connection = Mock()
        connection.capabilities.return_value = {(COMMON,1003):0,(MTP,1005):self.fixture.operations}
        def command(request):
            calls.append(('command',request[(MTP,1001)],request[(MTP,1002)]))
            return {(COMMON,1003):0,(MTP,1003):0x2001,(MTP,1004):()}
        def data(request):
            stage = request[(COMMON,1002)]
            calls.append(('data',stage))
            if stage==14:
                self.assertEqual(request[(MTP,1001)],0x9110)
                self.assertEqual(request[(MTP,1002)],())
                return {(COMMON,1003):0,(MTP,1006):'injected-context'}
            if stage==16:
                packets.append(request[(MTP,1012)])
                return {(COMMON,1003):0,(MTP,1011):len(packets[-1])}
            self.assertEqual(stage,17)
            return {(COMMON,1003):0,(MTP,1003):0x2001,(MTP,1004):()}
        connection.commands.side_effect = command
        connection.data.side_effect = data
        prefix = 'camera_install.independent_registration_reference.'
        with tempfile.TemporaryDirectory() as temporary, \
                patch(prefix+'receive',return_value=b'info'), \
                patch(prefix+'decode_device_info',return_value=SimpleNamespace(operations=self.fixture.operations)), \
                patch('camera_install.remote_session_reference.drain',side_effect=events), \
                patch('camera_install.rp_preflight_reference.RP_DESCRIPTOR_SHA256',
                      hashlib.sha256(descriptor).hexdigest()):
            backup = Path(temporary)/'slot3.bin'
            report = register_open_connection(connection,(self.fixture.raw,self.fixture.keys),
                slot=3,backup_path=backup,allow_experimental_write=True)
            self.assertEqual(backup.read_bytes(),baseline)
        self.assertEqual([len(value) for value in packets],[16728,52])
        self.assertEqual(packets[-1][-32:],state.control)
        lock = calls.index(('command',0x911b,(1,)))
        self.assertEqual(calls[lock:lock+8],[('command',0x911b,(1,)),
            ('data',14),('data',16),('data',17),('data',14),('data',16),('data',17),
            ('command',0x911c,())])
        self.assertEqual(calls[-3:],[('command',0x9127,(0xd172,)),
            ('command',0x9115,(0,)),('command',0x9114,(0,))])
        self.assertTrue(report['temporaryModesCleanupCompleted'])
        self.assertTrue(report['requestedSlotContentMatched'])


if __name__=='__main__': unittest.main()
