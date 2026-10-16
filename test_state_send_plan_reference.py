import struct,unittest
from camera_install.state_send_plan_reference import plan_slot_state


class StateSendPlanTests(unittest.TestCase):
    def test_extended_preserves_all_control_words_for_each_slot(self):
        control=bytearray(range(32))
        for handler,prop in ((0x21,0xd163),(0x22,0xd164),(0x23,0xd165)):
            plan=plan_slot_state(control,handler,observed_marker=1,observed_selector=65)
            self.assertEqual(plan.property_code,prop)
            self.assertTrue(plan.extended)
            self.assertEqual(plan.data,struct.pack('<IIIII',52,prop,44,1,65)+bytes(control))
            self.assertNotIn('data=',repr(plan))
        control[0]=255
        self.assertEqual(plan.data[-32],0)

    def test_legacy_serialization_is_explicit_not_control_mutation(self):
        control=bytes(range(32))
        for handler,prop in ((0x21,0xd160),(0x22,0xd161),(0x23,0xd162)):
            plan=plan_slot_state(control,handler,observed_marker=0,observed_selector=65)
            self.assertFalse(plan.extended)
            self.assertEqual(plan.data,struct.pack('<IIII',40,prop,32,65)+control[:24])
        self.assertEqual(control,bytes(range(32)))

    def test_aliases_and_invalid_state_are_rejected(self):
        for control,handler,marker,selector in ((bytes(32),0,1,65),
                (bytes(32),True,1,65),(bytes(31),0x21,1,65),
                (bytes(33),0x21,1,65),(32,0x21,1,65),
                (bytes(32),0x21,True,65),(bytes(32),0x21,1,-1)):
            with self.assertRaises(ValueError):
                plan_slot_state(control,handler,observed_marker=marker,observed_selector=selector)
