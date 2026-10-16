"""Extract the hash-verified compiler's model-dependent record initialization gate."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .pf3_schema_research import DLL_HASH


def base_context_prepares_legacy_aliases(family_class):
    """Replay only known-revision base setter53d00 gate, not PF3 override/support.

    After successful ID storage and record-list initialization,53f05/11/1d
    skip494d0 for classifier values8/9/10. Other values reach the call.
    """
    if type(family_class) is not int or not 0 <= family_class <= 0xffffffff:
        raise ValueError('Expected uint32 native family classification')
    return family_class not in (8, 9, 10)


def pf3_context_converts_dense(family_class):
    """Replay572d0 class gate: destination4cd00, not legacy preparation494d0.

    Conversion success does not establish that legacy aliases are populated.
    """
    return base_context_prepares_legacy_aliases(family_class)


def classify(identifier,rules):
    if type(identifier) is not int or not 0<=identifier<=0xffffffff:
        raise ValueError('Expected uint32 model ID')
    if identifier in rules['explicitSkipIds']:
        return 'skip-record-initialization'
    offset=identifier-rules['switchBase']
    branch=rules['switchSelectors'][offset] if 0<=offset<len(rules['switchSelectors']) else 2
    if type(branch) is not int or branch not in (0,1,2):
        raise ValueError('Unknown observed initialization branch')
    return ['skip-record-initialization','legacy-record-list','common-record-list'][branch]


def extract(dll, context='base'):
    if context not in ('base','pf3'):
        raise ValueError('Unknown observed initialization context')
    import pefile
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
    data=dll.read_bytes()
    if hashlib.sha256(data).hexdigest()!=DLL_HASH:
        raise ValueError('Unknown compiler revision')
    pe=pefile.PE(data=data)
    base=pe.OPTIONAL_HEADER.ImageBase
    entry, table, selector_rva, targets, lists = (
        (0x53b40,0x53c44,0x53c50,(0x53c09,0x53c10,0x53b75),(0xcf838,0xcf860))
        if context=='base' else
        (0x57110,0x57214,0x57220,(0x571d9,0x571e0,0x57145),(0xcf878,0xcf8a0)))
    branches=struct.unpack('<3I',pe.get_data(table,12))
    if tuple(v-base for v in branches)!=targets:
        raise ValueError('Unexpected model gate jump targets')
    decoder=Cs(CS_ARCH_X86,CS_MODE_32);decoder.detail=True
    instructions=list(decoder.disasm(pe.get_data(entry,0xab),base+entry))
    skipped=[]
    for instruction in instructions:
        if instruction.mnemonic=='cmp' and instruction.op_str.startswith('eax,'):
            operand=instruction.operands[1]
            if operand.type==CS_OP_IMM:
                skipped.append(operand.imm & 0xffffffff)
    selectors=list(pe.get_data(selector_rva,0xaf))
    if len(skipped)!=8 or any(v not in (0,1,2) for v in selectors):
        raise ValueError('Unexpected initialization gate data')
    def records(rva):
        values=[]
        for index in range(32):
            value=struct.unpack('<I',pe.get_data(rva+index*4,4))[0]
            if not value:return values
            values.append(hex(value))
        raise ValueError('Unterminated record list')
    return dict(dllSha256=DLL_HASH,functionRva=hex(entry),cameraAccess=False,dllModified=False,
                explicitSkipIds=skipped,switchBase=0x80000188,switchSelectors=selectors,
                legacyRecordList=records(lists[0]),commonRecordList=records(lists[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll',type=Path)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    rules=extract(args.dll)
    baseline=json.loads(args.baseline.read_text())
    rows=[]
    for group in baseline['routes']:
        rows.extend(dict(model=r['model'],cameraId=r['cameraId'],compiled=True) for r in group['models'])
    rows.extend(dict(model=r['model'],cameraId=r['cameraId'],compiled=False) for r in baseline['failures'])
    for row in rows:
        row['initializationRoute']=classify(row['cameraId'],rules)
        row['baselineConsistent']=row['compiled']==(row['initializationRoute']=='common-record-list')
    report=dict(rules=rules,rows=rows,baselineCases=len(rows),
                consistentCases=sum(r['baselineConsistent'] for r in rows),
                scope='Explains this recorded baseline; not a universal compatibility predictor')
    with args.output.open('x',encoding='utf-8') as output:json.dump(report,output,indent=2)
    print('Baseline consistency:',report['consistentCases'],'/',report['baselineCases'])
    print('Legacy records:',rules['legacyRecordList'])
    print('Common records:',rules['commonRecordList'])
    for row in rows:
        if not row['compiled']:print(row['model'],row['initializationRoute'])


if __name__=='__main__':main()
