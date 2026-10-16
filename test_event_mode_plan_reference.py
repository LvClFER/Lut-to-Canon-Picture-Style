import unittest
import struct
from camera_install.event_mode_plan_reference import plan_event_modes,plan_observed_windows_record


class EventModeTests(unittest.TestCase):
    def test_manager_record_kind_not_camera_model(self):
        record=bytearray(0x314)
        for kind in (1,2,4):
            struct.pack_into('<I',record,0x30c,kind)
            result=plan_observed_windows_record(record,registry_option_enabled=False)
            self.assertEqual(result,plan_event_modes(kind,helper_predicate=True,registry_option_enabled=False))
            record[:64]=bytes([0xaa])*64
            self.assertEqual(result,plan_observed_windows_record(record,registry_option_enabled=False))

    def test_manager_record_rejects_other_geometries(self):
        for record in (0x314,None,b'',bytes(0x313),bytes(0x315)):
            with self.assertRaises(ValueError):
                plan_observed_windows_record(record,registry_option_enabled=False)

    def test_predicate_matrix_and_override_order(self):
        for kind in (0,1,2,3,4,0xffffffff):
            for helper in (False,True):
                for option in (False,True):
                    result=plan_event_modes(kind,helper_predicate=helper,registry_option_enabled=option)
                    expected=0x41 if kind==4 else (5 if kind==2 else 1)|(0x10 if option else 0)
                    self.assertEqual(result.remote_mode,expected)
                    self.assertEqual(result.event_mode,1 if helper else 2)
                    self.assertEqual(result.commands,((0x9114,(expected,)),(0x9115,(1 if helper else 2,))))

    def test_reject_inferred_or_ambiguous_predicates(self):
        for kind in (True,-1,0x100000000,'USB',None):
            with self.assertRaises(ValueError):
                plan_event_modes(kind,helper_predicate=True,registry_option_enabled=False)
        for helper,option in ((1,False),(False,0),(None,True)):
            with self.assertRaises(ValueError):
                plan_event_modes(2,helper_predicate=helper,registry_option_enabled=option)


if __name__=='__main__':unittest.main()
