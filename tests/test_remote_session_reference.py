import unittest
import struct
from unittest.mock import Mock, patch
from camera_install.remote_session_reference import RemoteEventSession
from camera_install.event_mode_plan_reference import plan_event_modes, EventModePlan
from camera_install.canon_event_receive_reference import CompletedEvents
from camera_install.canon_events import PropertyEvent


class RemoteSessionTests(unittest.TestCase):
    def test_requested_reads_retain_side_state_and_reject_later_conflicts(self):
        empty = CompletedEvents((),1,8)
        state = PropertyEvent(0xd165,struct.pack('<III',44,1,0x43)+bytes(32))
        style = PropertyEvent(0xd172,struct.pack('<II',11,1)+b'abc')
        incoming = CompletedEvents((state,style),1,90)
        contradictory = PropertyEvent(0xd165,struct.pack('<III',44,1,0x43)+bytes([1])*32)
        commands = Mock()
        with patch('camera_install.remote_session_reference.drain',
                   side_effect=[empty,incoming,CompletedEvents((contradictory,style),1,90)]):
            with self.assertRaisesRegex(ValueError,'Contradictory'):
                with RemoteEventSession(commands,Mock(),self.plan()) as session:
                    session.request_slot_style(0x23)
                    self.assertEqual(session.observed_inputs.slots[0].handler_selector,0x23)
                    self.assertEqual(session.observed_inputs.slots[0].control,bytes(32))
                    self.assertEqual(session.startup_events,empty)
                    session.request_slot_style(0x23)
        self.assertEqual([call.args for call in commands.execute.call_args_list][-2:],
                         [(0x9115,(0,)),(0x9114,(0,))])

    def test_requested_slot_style_is_decoded_only_from_requested_event(self):
        empty = CompletedEvents((), 1, 8)
        for handler, code in ((0x21, 0xd170), (0x22, 0xd171), (0x23, 0xd172)):
            value = struct.pack('<II', 11, 1) + b'abc'
            incoming = CompletedEvents((PropertyEvent(code, value),), 1, 31)
            commands = Mock()
            with patch('camera_install.remote_session_reference.drain', side_effect=[empty, incoming]):
                with RemoteEventSession(commands, Mock(), self.plan()) as session:
                    for invalid in (0, True, 0x24):
                        with self.assertRaises(ValueError):
                            session.request_slot_style(invalid)
                    self.assertEqual(session.request_slot_style(handler), struct.pack('<II', 1, 3) + b'abc')
            self.assertEqual(commands.execute.call_args_list[2].args, (0x9127, (code,)))

    def test_contradictory_requested_values_are_not_selected_by_order(self):
        empty = CompletedEvents((), 1, 8)
        incoming = CompletedEvents((PropertyEvent(0xd17f, b'a'), PropertyEvent(0xd17f, b'b')), 1, 34)
        with patch('camera_install.remote_session_reference.drain', side_effect=[empty, incoming]):
            with self.assertRaisesRegex(ValueError, 'Contradictory'):
                with RemoteEventSession(Mock(), Mock(), self.plan()) as session:
                    session.request_descriptor()

    def test_descriptor_request_uses_completed_events_and_no_startup_cache(self):
        commands = Mock()
        session = RemoteEventSession(commands, Mock(), self.plan())
        descriptor = b'opaque descriptor'
        value = struct.pack('<I', len(descriptor) + 4) + descriptor
        incoming = CompletedEvents((PropertyEvent(0xd17f, value),), 1, len(value) + 20)
        empty = CompletedEvents((), 1, 8)
        with self.assertRaisesRegex(RuntimeError, 'active'):
            session.request_descriptor()
        commands.execute.assert_not_called()
        with patch('camera_install.remote_session_reference.drain',
                   side_effect=[incoming, empty, incoming]) as drain:
            with session:
                self.assertEqual(session.request_descriptor(), descriptor)
                self.assertEqual(drain.call_count, 3)
        self.assertEqual([call.args for call in commands.execute.call_args_list],
            [(0x9114, (1,)), (0x9115, (1,)), (0x9127, (0xd17f,)),
             (0x9115, (0,)), (0x9114, (0,))])
        with self.assertRaisesRegex(RuntimeError, 'active'):
            session.request_descriptor()

    def test_missing_or_invalid_descriptor_fails_and_cleans_modes(self):
        empty = CompletedEvents((), 1, 8)
        invalid = CompletedEvents((PropertyEvent(0xd17f, b'bad'),), 1, 23)
        for batches, expected_calls in (([empty] * 7, 7), ([empty, invalid], 2)):
            commands = Mock()
            with patch('camera_install.remote_session_reference.drain', side_effect=batches) as drain:
                with self.assertRaises((RuntimeError, ValueError)):
                    with RemoteEventSession(commands, Mock(), self.plan()) as session:
                        session.request_descriptor()
                self.assertEqual(drain.call_count, expected_calls)
            self.assertEqual([call.args for call in commands.execute.call_args_list][-2:],
                             [(0x9115, (0,)), (0x9114, (0,))])

    def plan(self):
        return plan_event_modes(1, helper_predicate=True, registry_option_enabled=False)

    def test_modes_drain_body_reverse_cleanup_and_no_reuse(self):
        commands, reader = Mock(), Mock()
        events = CompletedEvents((), 1, 8)
        session = RemoteEventSession(commands, reader, self.plan())
        with patch('camera_install.remote_session_reference.drain', return_value=events) as drain:
            with session as opened:
                self.assertIs(opened.startup_events, events)
                self.assertIsNone(opened.observed_inputs.camera_id)
                self.assertIsNone(opened.observed_inputs.raw_descriptor)
                self.assertEqual(opened.observed_inputs.slots, ())
                self.assertEqual(commands.execute.call_count, 2)
            drain.assert_called_once_with(reader)
        self.assertEqual([call.args for call in commands.execute.call_args_list],
                         [(0x9114, (1,)), (0x9115, (1,)),
                          (0x9115, (0,)), (0x9114, (0,))])
        with self.assertRaises(RuntimeError):
            session.__enter__()

    def test_ambiguous_setup_failure_still_cleans_attempted_mode(self):
        commands = Mock()
        commands.execute.side_effect = [RuntimeError('uncertain'), None]
        with self.assertRaisesRegex(RuntimeError, 'uncertain') as error:
            with RemoteEventSession(commands, None, self.plan()):
                self.fail('Body must not run')
        self.assertTrue(error.exception.temporary_modes_cleanup_completed)
        self.assertEqual([call.args for call in commands.execute.call_args_list],
                         [(0x9114, (1,)), (0x9114, (0,))])

    def test_failed_drain_and_failed_cleanup_preserve_primary_error(self):
        commands = Mock()
        commands.execute.side_effect = [None, None, RuntimeError('cleanup'), None]
        with patch('camera_install.remote_session_reference.drain', side_effect=ValueError('events')):
            with self.assertRaisesRegex(ValueError, 'events') as error:
                RemoteEventSession(commands, None, self.plan()).__enter__()
        self.assertEqual(commands.execute.call_count, 4)
        self.assertIn('cleanup', error.exception.__notes__[0])
        self.assertFalse(error.exception.temporary_modes_cleanup_completed)

    def test_body_failure_reports_successful_mode_cleanup(self):
        with patch('camera_install.remote_session_reference.drain', return_value=CompletedEvents((),1,8)):
            with self.assertRaisesRegex(ValueError,'compiler') as error:
                with RemoteEventSession(Mock(),Mock(),self.plan()):
                    raise ValueError('compiler')
        self.assertTrue(error.exception.temporary_modes_cleanup_completed)

    def test_body_failure_cleans_both_and_cleanup_alone_is_not_success(self):
        for body_error in (False, True):
            commands = Mock()
            commands.execute.side_effect = [None, None, RuntimeError('cleanup'), None]
            with patch('camera_install.remote_session_reference.drain', return_value=CompletedEvents((), 1, 8)):
                with self.assertRaisesRegex(RuntimeError, 'body' if body_error else 'cleanup'):
                    with RemoteEventSession(commands, None, self.plan()):
                        if body_error:
                            raise RuntimeError('body')
            self.assertEqual(commands.execute.call_count, 4)

    def test_forged_mode_plan_is_rejected_without_io(self):
        for plan in (None, EventModePlan(1, 1, ((0x9110, (1,)),)),
                     EventModePlan(0, 1, ((0x9114, (0,)), (0x9115, (1,))))):
            with self.assertRaises(ValueError):
                RemoteEventSession(None, None, plan)
