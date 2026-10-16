"""Static, read-only disassembly of observed MLib conversion targets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


def reachable_instructions(pe, decoder, start, max_instructions=5000):
    """Follow direct branches only; explicitly retain indirect edges as unresolved."""
    base = pe.OPTIONAL_HEADER.ImageBase
    pending = [start]
    seen = {}
    calls = set()
    unresolved = []
    while pending and len(seen) < max_instructions:
        rva = pending.pop()
        if rva in seen:
            continue
        if rva < 0 or rva >= pe.OPTIONAL_HEADER.SizeOfImage or abs(rva - start) > 0x10000:
            unresolved.append({"targetRva": hex(rva), "reason": "outside bounded function exploration"})
            continue
        instruction = next(decoder.disasm(pe.get_data(rva, 16), base + rva, count=1), None)
        if instruction is None:
            unresolved.append({"targetRva": hex(rva), "reason": "cannot decode"})
            continue
        seen[rva] = f"0x{rva:08x} {instruction.bytes.hex():<20} {instruction.mnemonic} {instruction.op_str}"
        target = int(instruction.op_str, 16) - base if instruction.op_str.startswith("0x") else None
        if instruction.mnemonic == "call" and target is not None:
            calls.add(hex(target))
        if instruction.mnemonic.startswith("ret") or instruction.mnemonic == "int3":
            continue
        if instruction.mnemonic.startswith("j"):
            if target is not None:
                pending.append(target)
            else:
                unresolved.append({"atRva": hex(rva), "reason": "indirect branch", "operand": instruction.op_str})
            if instruction.mnemonic == "jmp":
                continue
        pending.append(rva + instruction.size)
    return {"instructionCount": len(seen), "budgetExhausted": bool(pending),
            "directCallTargets": sorted(calls), "unresolvedEdges": unresolved,
            "disassembly": [seen[key] for key in sorted(seen)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--follow-direct-calls", action="store_true",
                        help="Bounded second-level static analysis, not semantic validation")
    parser.add_argument("--extra-rva", type=lambda value: int(value, 0), action="append", default=[],
                        help="Explicit observed caller/helper start, bounded static flow")
    args = parser.parse_args()
    sys.path.insert(0, str(args.vendor.resolve()))
    import pefile
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    pe = pefile.PE(str(args.dll))
    if pe.FILE_HEADER.Machine != 0x14C:
        parser.error("Observed target functions require the x86 MLib DLL")
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    targets = inventory["files"][0]["converterDispatchTargets"]
    if any(target["ownerModule"].lower() != args.dll.name.lower() for target in targets):
        parser.error("Inventory conversion targets belong to another DLL")
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    report = {"dll": str(args.dll.resolve()), "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
              "inventorySha256": hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
              "readOnly": True, "staticDisassemblyIsNotSemanticValidation": True, "targets": []}
    offsets = sorted(int(target["targetRva"], 16) for target in targets)
    for target in targets:
        rva = int(target["targetRva"], 16)
        following = next((value for value in offsets if value > rva), rva + 0x1000)
        window = min(following - rva, 0x1000)
        lines = []
        calls = set()
        for instruction in decoder.disasm(pe.get_data(rva, window), base + rva):
            lines.append(f"0x{instruction.address - base:08x} {instruction.bytes.hex():<20} {instruction.mnemonic} {instruction.op_str}")
            if instruction.mnemonic == "call" and instruction.op_str.startswith("0x"):
                address = int(instruction.op_str, 16)
                if base <= address < base + pe.OPTIONAL_HEADER.SizeOfImage:
                    calls.add(f"0x{address - base:08x}")
        report["targets"].append({"dispatchSlotRva": target["slotRva"], "targetRva": target["targetRva"],
                                  "windowBytes": window, "windowIsNotProvenFunctionBoundary": True,
                                  "windowCallTargetsNotFunctionCalls": sorted(calls), "disassembly": lines,
                                  "reachableFlow": reachable_instructions(pe, decoder, rva)})
    # 1b670's reachable wrapper forwards directly to this internal converter.
    report["observedWrapperCallee"] = {"targetRva": "0x196a0",
                                      "reachableFlow": reachable_instructions(pe, decoder, 0x196A0)}
    report["extraObservedFunctions"] = [{"targetRva": hex(rva),
        "reachableFlow": reachable_instructions(pe, decoder, rva)} for rva in args.extra_rva]
    if args.follow_direct_calls:
        roots = [target["reachableFlow"] for target in report["targets"]]
        roots.append(report["observedWrapperCallee"]["reachableFlow"])
        callees = sorted({int(value, 16) for root in roots for value in root["directCallTargets"]})
        report["directCallees"] = [{"targetRva": hex(rva),
            "reachableFlow": reachable_instructions(pe, decoder, rva, max_instructions=5000)}
            for rva in callees[:32]]
        report["calleeLimit"] = 32
    flows = [target["reachableFlow"] for target in report["targets"]]
    flows.append(report["observedWrapperCallee"]["reachableFlow"])
    flows.extend(item["reachableFlow"] for item in report.get("directCallees", []))
    addresses = sorted({int(match, 16) for flow in flows for line in flow["disassembly"]
                        for match in re.findall(r"qword ptr \[(0x[0-9a-f]+)\]", line)})
    constants = []
    for address in addresses:
        rva = address - base
        section = pe.get_section_by_rva(rva)
        if section is None or section.Characteristics & 0x20000000:
            continue
        raw = pe.get_data(rva, 8)
        if len(raw) == 8:
            constants.append({"rva": hex(rva), "rawHex": raw.hex(),
                              "candidateFloat64": repr(struct.unpack("<d", raw)[0])})
    report["referencedNonExecutableQwordCandidates"] = constants
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"targets": len(report["targets"]), "dllSha256": report["dllSha256"],
                      "instructions": sum(len(target["disassembly"]) for target in report["targets"])}))


if __name__ == "__main__":
    main()
