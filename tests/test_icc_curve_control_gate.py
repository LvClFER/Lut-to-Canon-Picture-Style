import unittest
from pathlib import Path
from camera_install.pf3_field_experiments import validate_icc_curve_control, compile_stock


class ICCControlGateTests(unittest.TestCase):
    agent=Path(__file__).resolve().parents[2]/'tmp/PF3_FIELD_EXPERIMENTS_20261004/ALTERNATE_FF0001_20261007/private_icc_curve_agent.js'

    def test_bounded_controls(self):
        for prop in (0x1018,0x1019,0x1065):
            for channel in (0,1,2):
                validate_icc_curve_control(self.agent,{'property':prop,'channel':channel})
                validate_icc_curve_control(self.agent,{'property':prop,'channel':channel,'shape':'mid96'})
        validate_icc_curve_control(Path('other.js'),None)

    def test_reject_wrong_agent_fields_and_types(self):
        with self.assertRaises(ValueError):
            validate_icc_curve_control(Path('other.js'),{'property':0x1018,'channel':0})
        for control in ([],{}, {'property':0x1018,'channel':0,'extra':1},
                        {'property':0x115,'channel':0},{'property':True,'channel':0},
                        {'property':0x1018,'channel':True},{'property':0x1018,'channel':3},
                        {'property':0x1018,'channel':0,'shape':'unknown'}):
            with self.assertRaises(ValueError):validate_icc_curve_control(self.agent,control)

    def test_no_native_start_without_revision_gate(self):
        with self.assertRaisesRegex(ValueError,'known-hash'):
            compile_stock(None,Path('unused.dll'),self.agent,Path('unused.pf3'),0,b'',
                          icc_curve_control={'property':0x1018,'channel':0})
