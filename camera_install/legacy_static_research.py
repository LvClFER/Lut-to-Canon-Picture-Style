"""Read-only x86 reference scan for the unresolved legacy Canon record 0x1007."""
import argparse
import hashlib
import json
from pathlib import Path

from .pf3_schema_research import DLL_HASH


def scan(dll, targets=(0x1007,0x40001007)):
    import pefile
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

    data = dll.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest not in (DLL_HASH,'a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a'):
        raise ValueError('Unknown DLL revision; refusing fixed-address interpretation')
    pe = pefile.PE(data=data)
    if pe.FILE_HEADER.Machine != 0x14c:
        raise ValueError('Expected the observed x86 compiler')
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    decoder.skipdata = True
    base = pe.OPTIONAL_HEADER.ImageBase
    rows = []
    section_counts = []
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        instructions = list(decoder.disasm(section.get_data(), base + section.VirtualAddress))
        section_counts.append(dict(name=section.Name.rstrip(b'\0').decode('ascii'),
                                   instructions=len(instructions)))
        for index, instruction in enumerate(instructions):
            if instruction.id == 0:
                continue
            values = [operand.imm & 0xffffffff for operand in instruction.operands
                      if operand.type == CS_OP_IMM]
            if not set(values) & set(targets):
                continue
            window = instructions[max(0, index - 12):index + 14]
            rows.append(dict(rva=hex(instruction.address - base),
                             matchedValues=[hex(value) for value in values],
                             instruction=f'{instruction.mnemonic} {instruction.op_str}',
                             context=[dict(rva=hex(item.address - base), bytes=item.bytes.hex(),
                                           text=f'{item.mnemonic} {item.op_str}') for item in window]))
    return dict(dllSha256=digest, targetValues=[hex(v) for v in targets],cameraAccess=False, dllModified=False,
                scope='Static candidate references; instruction boundaries require control-flow confirmation',
                executableSections=section_counts, references=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--value',type=lambda v:int(v,0),action='append')
    args = parser.parse_args()
    report = scan(args.dll,args.value or (0x1007,0x40001007))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print('Static candidate references:', len(report['references']))
    for row in report['references']:
        print(row['rva'], row['instruction'])


if __name__ == '__main__':
    main()
