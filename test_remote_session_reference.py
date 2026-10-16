import unittest
from unittest.mock import Mock, patch
from camera_install.remote_session_reference import RemoteEventSession
from camera_install.event_mode_plan_reference import plan_event_modes, EventModePlan
from camera_install.canon_event_receive_reference import CompletedEvents


class RemoteSessionTests(unittest.TestCase):
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
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            with RemoteEventSession(commands, None, self.plan()):
                self.fail('Body must not run')
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
