"""Locate static native-carrier property call sites in a Canon x86 executable."""
import argparse
import hashlib
import json
from pathlib import Path


def scan(path):
    import pefile
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM

    raw = path.read_bytes()
    pe = pefile.PE(data=raw)
    if pe.FILE_HEADER.Machine != 0x14c:
        raise ValueError('This bounded scanner currently supports x86 only')
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    base = pe.OPTIONAL_HEADER.ImageBase
    imports = {entry.address: module.dll.decode() + '!' +
               (entry.name.decode() if entry.name else str(entry.ordinal))
               for module in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]) for entry in module.imports}
    def call_name(instruction):
        if instruction.mnemonic not in ('call','jmp'):
            return None
        operand = instruction.operands[0]
        if operand.type == CS_OP_MEM:
            return imports.get(operand.mem.disp & 0xffffffff)
        if operand.type == CS_OP_IMM:
            thunk = list(decoder.disasm(pe.get_data(operand.imm-base,6),operand.imm,count=1))
            if thunk and thunk[0].mnemonic=='jmp' and thunk[0].operands[0].type==CS_OP_MEM:
                return imports.get(thunk[0].operands[0].mem.disp & 0xffffffff)
        return None
    rows = []
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        data = section.get_data()
        position = 0
        while True:
            position = data.find(bytes.fromhex('03020001'),position)
            if position < 0:
                break
            candidates = []
            for prefix_size in range(1,12):
                start = position-prefix_size
                if start < 0:
                    continue
                decoded = list(decoder.disasm(data[start:position+4],base+section.VirtualAddress+start,count=1))
                if decoded and decoded[0].size==prefix_size+4 and any(
                        op.type==CS_OP_IMM and op.imm==0x01000203 for op in decoded[0].operands):
                    candidates.append(start)
            if not candidates:
                position += 4
                continue
            start = min(candidates)
            address = base + section.VirtualAddress + start
            context = []
            for instruction in decoder.disasm(data[start:start+200],address,count=45):
                row = dict(rva=hex(instruction.address-base),text=f'{instruction.mnemonic} {instruction.op_str}')
                name = call_name(instruction)
                if name:
                    row['import'] = name
                context.append(row)
                if instruction.mnemonic.startswith('ret'):
                    break
            rows.append(dict(rva=hex(address-base),context=context))
            position += 4
    return dict(moduleSha256=hashlib.sha256(raw).hexdigest(),modulePath=str(path.resolve()),
                moduleModified=False,cameraAccess=False,
                scope='Static immediate candidates; instruction boundaries need control-flow validation',
                carrierProperty='0x01000203',references=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    report = scan(args.module)
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(report,output,indent=2)
    print('Carrier-property candidate sites:',len(report['references']))
    for row in report['references']:
        print(row['rva'],[v['import'] for v in row['context'] if v.get('import')])


if __name__=='__main__':
    main()
