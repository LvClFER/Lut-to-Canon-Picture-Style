import struct
import unittest
from camera_install.session_inputs_reference import collect_inputs
from camera_install.canon_events import PropertyEvent
from camera_install.canon_event_receive_reference import CompletedEvents


class SessionInputTests(unittest.TestCase):
    def batch(self, events):
        return CompletedEvents(tuple(events), 1, sum(len(e.value)+12 for e in events))

    def test_compiler_inputs_and_all_slots_preserve_opaque_control(self):
        control = bytes(range(32))
        descriptor = b'opaque descriptor'
        events = [PropertyEvent(0xd116, struct.pack('<I', 0x80000227)),
                  PropertyEvent(0xd17f, struct.pack('<I', len(descriptor)+4)+descriptor)]
        events += [PropertyEvent(code, struct.pack('<III', 44, 1, 0x41)+control)
                   for code in (0xd165, 0xd164, 0xd163)]
        inputs = collect_inputs(self.batch(events))
        self.assertEqual(inputs.camera_id, 0x40000227)
        self.assertEqual(inputs.raw_descriptor, descriptor)
        self.assertEqual([s.handler_selector for s in inputs.slots], [0x21, 0x22, 0x23])
        self.assertTrue(all(s.control == control for s in inputs.slots))
        self.assertNotIn('opaque descriptor', repr(inputs))

    def test_absent_and_duplicate_inputs_are_not_invented(self):
        self.assertEqual(collect_inputs(self.batch(())).slots, ())
        self.assertIsNone(collect_inputs(self.batch(())).camera_id)
        self.assertIsNone(collect_inputs(self.batch(())).raw_descriptor)
        first = PropertyEvent(0xd116, struct.pack('<I', 0x80000227))
        alias = PropertyEvent(0xd116, struct.pack('<I', 0x40000227))
        self.assertEqual(collect_inputs(self.batch((first, alias))).camera_id, 0x40000227)

    def test_conflicting_or_malformed_inputs_do_not_yield_partial_state(self):
        first = PropertyEvent(0xd116, struct.pack('<I', 1))
        for events in ((first, PropertyEvent(0xd116, struct.pack('<I', 2))),
                       (first, PropertyEvent(0xd163, bytes(44))),
                       (first, PropertyEvent(0xd164, bytes(43))),
                       (first, PropertyEvent(0xd17f, struct.pack('<I', 100))),
                       (PropertyEvent(0xd116, bytearray(4)),)):
            with self.assertRaises(ValueError):
                collect_inputs(self.batch(events))
