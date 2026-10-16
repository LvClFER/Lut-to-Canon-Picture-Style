import unittest
from camera_install.managed_switch_research import constant, switches, summarize


class ManagedSwitchTests(unittest.TestCase):
    def test_constants_and_case_values(self):
        self.assertEqual(constant(dict(opcode='ldc.i4.m1')), -1)
        instructions = [dict(offset=0, opcode='ldarg.1'), dict(offset=1, opcode='ldc.i4.s', operand=-2),
                        dict(offset=3, opcode='sub'), dict(offset=4, opcode='switch', operand=[0, 1], branchTargets=[10, 11]),
                        dict(offset=10, opcode='ret'), dict(offset=11, opcode='ret')]
        result = switches(dict(instructions=instructions))[0]
        self.assertEqual(result['entries'], [dict(value=-2, target=10), dict(value=-1, target=11)])

    def test_reject_invalid_boundary(self):
        instructions = [dict(offset=0, opcode='ldloc.1'), dict(offset=1, opcode='ldc.i4.1'),
                        dict(offset=2, opcode='sub'), dict(offset=3, opcode='switch', operand=[0], branchTargets=[99])]
        with self.assertRaises(ValueError):
            switches(dict(instructions=instructions))

    def test_partial_evidence_is_not_success(self):
        with self.assertRaises(ValueError):
            summarize(dict(cameraAccess=False, applicationExecuted=False, dllModified=False, complete=False))


if __name__ == '__main__':
    unittest.main()
