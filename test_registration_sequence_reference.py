import struct
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch, call
from camera_install.registration_sequence_reference import plan_registration, execute_and_compare
from camera_install.state_send_plan_reference import plan_slot_state


class RegistrationSequenceTests(unittest.TestCase):
    def test_inconsistent_plan_is_rejected_before_lock_or_transfer(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        plan = plan_registration(carrier, bytes(32), 0x21, (),
                                 observed_marker=1, selected_cache_value=0x41)
        other = plan_registration(carrier, bytes(32), 0x22, (),
                                  observed_marker=1, selected_cache_value=0x42)
        invalid = (
            replace(plan, state=other.state),
            replace(plan, selector_cache_value=0x42),
            replace(plan, style=replace(plan.style, parameters=(1,))),
            replace(plan, style=replace(plan.style, slot=True)),
            replace(plan, style=replace(plan.style, opcode=0x9111)),
            replace(plan, state=replace(plan.state, extended=1)),
            replace(plan, state=replace(plan.state, data=plan.state.data[:-1])),
            replace(plan, state=replace(plan.state, property_code=0xd164)),
            replace(plan, state=replace(plan.state, property_code=float(plan.state.property_code))),
            replace(plan, style=replace(plan.style,
                data=plan.style.data[:4]+struct.pack('<I',0xd171)+plan.style.data[8:])),
        )
        for sequence in invalid:
            with self.subTest(sequence=sequence), \
                 patch('camera_install.registration_sequence_reference.transfer') as transfer:
                commands, read = Mock(), Mock(return_value=struct.pack('<II',1,3)+b'abc')
                with self.assertRaises(ValueError):
                    execute_and_compare(sequence, 'writer', commands, read, allow_write=True)
                commands.execute.assert_not_called()
                transfer.assert_not_called()
                read.assert_not_called()

    def test_all_planned_slots_routes_and_state_encodings_remain_byte_exact(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        for handler in (0x21, 0x22, 0x23):
            for caps in ((), (0x918a,), (0x9192,)):
                for marker in (0, 1):
                    plan = plan_registration(carrier, bytes(range(32)), handler, caps,
                                             observed_marker=marker, selected_cache_value=0x41)
                    original = plan.wire_steps
                    with patch('camera_install.registration_sequence_reference.transfer') as transfer:
                        self.assertTrue(execute_and_compare(plan, 'writer', Mock(),
                            lambda slot: struct.pack('<II',1,3)+b'abc', allow_write=True))
                        self.assertEqual(transfer.call_args_list,
                            [call('writer', *step) for step in original])
                    self.assertEqual(plan.wire_steps, original)
        direct = plan_registration(carrier, bytes(32), 0x21, (0x9192,),
                                   observed_marker=1, selected_cache_value=0x41)
        with patch('camera_install.registration_sequence_reference.transfer') as transfer:
            commands = Mock()
            bad = replace(direct, style=replace(direct.style,
                          parameters=(True, len(direct.style.data))))
            with self.assertRaises(ValueError):
                execute_and_compare(bad, 'writer', commands, Mock(), allow_write=True)
            commands.execute.assert_not_called()
            transfer.assert_not_called()

    def test_execution_orders_opaque_state_after_style_and_compares_requested_slot(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        control = bytes(range(32))
        for caps in ((), (0x918a,), (0x9192,)):
            plan = plan_registration(carrier, control, 0x23, caps,
                                    observed_marker=1, selected_cache_value=0x43)
            read = Mock(return_value=struct.pack('<II', 1, 3) + b'abc')
            commands = Mock()
            with patch('camera_install.registration_sequence_reference.transfer') as transfer:
                ordered = Mock()
                ordered.attach_mock(commands.execute, 'command')
                ordered.attach_mock(transfer, 'transfer')
                ordered.attach_mock(read, 'read')
                self.assertTrue(execute_and_compare(plan, 'writer', commands, read, allow_write=True))
                self.assertEqual(transfer.call_args_list,
                    [call('writer', opcode, parameters, payload) for opcode, parameters, payload in plan.wire_steps])
                self.assertEqual(ordered.mock_calls,
                    [call.command(0x911b, (1,)),
                     *(call.transfer('writer', opcode, parameters, payload) for opcode, parameters, payload in plan.wire_steps),
                     call.command(0x911c, ()), call.read(0x23)])
            read.assert_called_once_with(0x23)
            self.assertEqual(plan.state.data[-32:], control)

    def test_failed_style_never_writes_state_and_failed_state_never_reads(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        plan = plan_registration(carrier, bytes(32), 0x21, (),
                                 observed_marker=1, selected_cache_value=0x41)
        for results in ([RuntimeError('style')], [None, RuntimeError('state')]):
            read = Mock()
            commands = Mock()
            with patch('camera_install.registration_sequence_reference.transfer', side_effect=results) as transfer:
                with self.assertRaises(RuntimeError) as raised:
                    execute_and_compare(plan, 'writer', commands, read, allow_write=True)
                self.assertEqual(transfer.call_count, len(results))
                self.assertIs(raised.exception, results[-1])
                stage = 'style' if len(results) == 1 else 'state'
                self.assertEqual(raised.exception.__notes__,
                    [f'Registration {stage} transfer failed; camera content is unconfirmed'])
            read.assert_not_called()
            self.assertEqual(commands.execute.call_args_list,
                             [call(0x911b, (1,)), call(0x911c, ())])
        with patch('camera_install.registration_sequence_reference.transfer') as transfer:
            for consent in (False, 1):
                with self.assertRaises(ValueError):
                    execute_and_compare(plan, 'writer', Mock(), Mock(), allow_write=consent)
            transfer.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'differs'):
                execute_and_compare(plan, 'writer', Mock(), lambda handler: b'wrong', allow_write=True)

    def test_lock_or_unlock_failure_never_proceeds_or_retries(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        plan = plan_registration(carrier, bytes(32), 0x21, (),
                                 observed_marker=1, selected_cache_value=0x41)
        for failures, expected_writes in (([RuntimeError('lock'), None], 0),
                                          ([None, RuntimeError('unlock')], 2)):
            commands, read = Mock(), Mock()
            commands.execute.side_effect = failures
            with patch('camera_install.registration_sequence_reference.transfer') as transfer:
                with self.assertRaises(RuntimeError):
                    execute_and_compare(plan, 'writer', commands, read, allow_write=True)
                self.assertEqual(transfer.call_count, expected_writes)
            read.assert_not_called()
            self.assertEqual(commands.execute.call_args_list,
                             [call(0x911b, (1,)), call(0x911c, ())])
        original = RuntimeError('style')
        commands = Mock()
        commands.execute.side_effect = [None, RuntimeError('unlock')]
        with patch('camera_install.registration_sequence_reference.transfer', side_effect=original) as transfer:
            with self.assertRaises(RuntimeError) as raised:
                execute_and_compare(plan, 'writer', commands, Mock(), allow_write=True)
            self.assertIs(raised.exception, original)
            self.assertIn('UI unlock also failed', original.__notes__)
            transfer.assert_called_once()

    def test_explicit_selector_cache_then_style_then_opaque_state(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        control = bytearray(range(32))
        for handler in (0x21, 0x22, 0x23):
            for caps in ((), (0x918a,), (0x9192, 0x918a)):
                for marker in (0, 1):
                    plan = plan_registration(carrier, control, handler, caps,
                        observed_marker=marker, selected_cache_value=0x41)
                    self.assertEqual(plan.selector_cache_value, 0x41)
                    self.assertEqual(plan.state, plan_slot_state(control, handler,
                        observed_marker=marker, observed_selector=0x41))
                    self.assertEqual(len(plan.wire_steps), 2)
                    self.assertEqual(plan.wire_steps[0][0], plan.style.opcode)
                    self.assertEqual(plan.wire_steps[1], (0x9110, (), plan.state.data))
                    self.assertEqual(control, bytearray(range(32)))

    def test_parameter_zero_and_string_selector_are_not_guessed(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        for handler, selector in ((0, 0x41), (0x21, 'Style'), (0x21, True)):
            with self.assertRaises(ValueError):
                plan_registration(carrier, bytes(32), handler, (),
                                  observed_marker=1, selected_cache_value=selector)
