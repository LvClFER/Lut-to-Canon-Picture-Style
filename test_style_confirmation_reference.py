import struct
import unittest
from camera_install.style_confirmation_reference import verify_readback_content
from camera_install.style_send_plan_reference import plan_style_send


class StyleConfirmationTests(unittest.TestCase):
    def test_send_to_readback_roundtrip_all_slots_and_routes(self):
        for body in (b'', bytes(range(256)), b'\x00' * 16712):
            carrier = struct.pack('<II', 1, len(body)) + b'N' * 32 + body
            for slot in (0x21, 0x22, 0x23):
                for caps in ((0x9192,), (0x918a,), ()):
                    plan = plan_style_send(carrier, slot, caps)
                    # Property transport adds total-size and property code.
                    wire = plan.data[8:] if plan.opcode == 0x9110 else plan.data
                    self.assertTrue(verify_readback_content(carrier, wire))
                    renamed = carrier[:8] + b'X' * 32 + carrier[40:]
                    self.assertTrue(verify_readback_content(renamed, wire))

    def test_mismatch_disabled_and_bad_lengths_fail(self):
        carrier = struct.pack('<II', 1, 3) + bytes(32) + b'abc'
        wire = struct.pack('<II', 11, 1) + b'abc'
        for wrong in (wire[:-1], wire + b'x', wire[:-1] + b'd',
                      struct.pack('<II', 11, 0) + b'abc'):
            with self.assertRaises(ValueError):
                verify_readback_content(carrier, wrong)
        for wrong in (None, carrier[:39], struct.pack('<II', 0, 3) + carrier[8:],
                      struct.pack('<II', 1, 4) + carrier[8:]):
            with self.assertRaises(ValueError):
                verify_readback_content(wrong, wire)


if __name__ == '__main__':
    unittest.main()
