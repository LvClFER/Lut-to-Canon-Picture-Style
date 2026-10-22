import struct,unittest
from camera_install.compiler_input_events_reference import camera_id_from_d116,descriptor_from_d17f
from camera_install.compiler_input_events_reference import initial_property_dispatch_order
from camera_install.canon_events import PropertyEvent


class CompilerInputEventTests(unittest.TestCase):
    def test_initial_dispatch_duplicates_first_id_then_preserves_entire_order(self):
        events=tuple(PropertyEvent(p,b'') for p in (0xd17f,0xd116,0xd163,0xd116))
        self.assertEqual(initial_property_dispatch_order(events,initial=True),(1,0,1,2,3))
        self.assertEqual(initial_property_dispatch_order(events,initial=False),(0,1,2,3))
        self.assertEqual(initial_property_dispatch_order(events[:1],initial=True),(0,))
        self.assertEqual(initial_property_dispatch_order((),initial=True),())

    def test_initial_projection_rejects_untyped_flags_and_events(self):
        for events,flag in (([],True),((),1),((None,),True),((PropertyEvent(True,b''),),True)):
            with self.assertRaises(ValueError):initial_property_dispatch_order(events,initial=flag)

    def test_id_alias_is_specific_not_mirrorless_model_inference(self):
        for raw,expected in ((0x80000227,0x40000227),(0x33040080,0x33040080),
                (0x80000228,0x80000228),(0,0)):
            self.assertEqual(camera_id_from_d116(struct.pack('<I',raw)),expected)
        for bad in (4,True,b'',bytes(5)):
            with self.assertRaises(ValueError):camera_id_from_d116(bad)

    def test_descriptor_length_removed_once_without_normalization(self):
        for payload in (b'',bytes(range(256)),bytes(7772),bytes(15076)):
            raw=bytearray(struct.pack('<I',len(payload)+4)+payload)
            result=descriptor_from_d17f(memoryview(raw))
            self.assertEqual(result,payload)
            raw[0]=0
            self.assertEqual(result,payload)

    def test_types_bounds_and_truncations(self):
        raw=struct.pack('<I',8)+b'abcd'
        for bad in (8,None,'event',memoryview(bytes(1048577)),raw+b'x',
                *(raw[:n] for n in range(len(raw)))):
            with self.assertRaises(ValueError):descriptor_from_d17f(bad)
