import struct,unittest
from camera_install.style_send_plan_reference import plan_style_send


class StyleSendPlanTests(unittest.TestCase):
    def test_capability_priority_and_caption_exclusion(self):
        carrier=struct.pack('<II',1,4)+b'N'*32+b'LOOK'
        for operations,opcode in (((0x918a,0x9192),0x9192),((0x918a,),0x918a)):
            plan=plan_style_send(carrier,0x23,operations)
            self.assertEqual((plan.opcode,plan.parameters,plan.slot),(opcode,(3,12),3))
            self.assertEqual(plan.data,struct.pack('<II',12,1)+b'LOOK')
            self.assertNotIn('LOOK',repr(plan))

    def test_property_route_has_slot_specific_property_and_nested_lengths(self):
        for selector,prop in ((0x21,0xd170),(0x22,0xd171),(0x23,0xd172)):
            raw=bytearray(struct.pack('<II',1,1)+bytes(32)+b'X')
            plan=plan_style_send(raw,selector,frozenset())
            raw[-1]=0
            self.assertEqual(plan.opcode,0x9110)
            self.assertEqual(plan.parameters,())
            self.assertEqual(plan.data,struct.pack('<IIII',17,prop,9,1)+b'X')

    def test_invalid_inputs_fail_before_packet_creation(self):
        good=struct.pack('<II',1,0)+bytes(32)
        for carrier,selector,ops in ((good,True,()),(good,0x24,()),(good,0x21,[]),
                (good,0x21,(True,)),(good,0x21,(65536,)),(good[:-1],0x21,()),
                (good+b'X',0x21,()),(40,0x21,())):
            with self.assertRaises(ValueError):plan_style_send(carrier,selector,ops)
