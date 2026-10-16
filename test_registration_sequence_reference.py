import struct
import unittest
from camera_install.registration_sequence_reference import plan_registration
from camera_install.state_send_plan_reference import plan_slot_state


class RegistrationSequenceTests(unittest.TestCase):
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
