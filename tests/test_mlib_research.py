import unittest
from types import SimpleNamespace

from camera_install.mlib_research import reachable_instructions


class FlowTests(unittest.TestCase):
    def inspect(self, code):
        base = 0x1000
        pe = SimpleNamespace(OPTIONAL_HEADER=SimpleNamespace(ImageBase=base, SizeOfImage=0x1000),
                             get_data=lambda rva, size: bytes(size))

        class Decoder:
            def disasm(self, data, address, count=1):
                entry = code.get(address - base)
                if entry:
                    mnemonic, operand = entry
                    yield SimpleNamespace(mnemonic=mnemonic, op_str=operand, size=1, bytes=b"\x90")

        return reachable_instructions(pe, Decoder(), 0)

    def test_branches_exclude_unreachable_neighbors(self):
        flow = self.inspect({0: ("call", "0x1010"), 1: ("jne", "0x1004"),
                             2: ("ret", ""), 3: ("call", "0x1020"), 4: ("ret", "")})
        self.assertEqual(flow["instructionCount"], 4)
        self.assertEqual(flow["directCallTargets"], ["0x10"])
        self.assertFalse(flow["unresolvedEdges"])

    def test_indirect_jump_is_not_silently_followed(self):
        flow = self.inspect({0: ("jmp", "eax"), 1: ("ret", "")})
        self.assertEqual(flow["instructionCount"], 1)
        self.assertEqual(flow["unresolvedEdges"][0]["reason"], "indirect branch")

    def test_loop_does_not_run_forever(self):
        flow = self.inspect({0: ("jmp", "0x1000")})
        self.assertEqual(flow["instructionCount"], 1)
        self.assertFalse(flow["budgetExhausted"])


if __name__ == "__main__":
    unittest.main()
