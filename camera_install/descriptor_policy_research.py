"""Read-only extraction of Canon's observed compact descriptor policy."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from .compiler_regression import cipher_tables
from .virtual_compatibility import load_models


DIRECT_SMALL={0x80000287,0x80000236,0x80000213,0x80000169,
              0x03740000,0x03840000,0x80000176,0x80000190,
              0x80000393,0x80000432,0x80000404,0x80000422,0xc0000250}


def read_rva(data, address, size):
    pe=struct.unpack_from('<I',data,0x3c)[0]
    if data[pe:pe+4]!=b'PE\0\0':
        raise ValueError('Invalid PE signature')
    sections=struct.unpack_from('<H',data,pe+6)[0]
    optional=struct.unpack_from('<H',data,pe+20)[0]
    for index in range(sections):
        header=pe+24+optional+index*40
        _,rva,raw_size,raw_offset=struct.unpack_from('<4I',data,header+8)
        if rva<=address and address+size<=rva+raw_size:
            offset=raw_offset+address-rva
            result=data[offset:offset+size]
            if len(result)!=size: raise ValueError('Truncated file-backed section')
            return result
    raise ValueError('RVA is not within a file-backed section')


def policy_ids(raw, reader):
    small=set(DIRECT_SMALL)
    for first,count,index_rva,jump_rva in (
        (0x80000215,32,0x4c4a4,0x4c49c),
        (0x80000250,55,0x4c4cc,0x4c4c4),
        (0x80000288,253,0x4c50c,0x4c504)):
        indices=reader(raw,index_rva,count)
        targets=struct.unpack('<2I',reader(raw,jump_rva,8))
        if set(targets)!={0x1004c488,0x1004c491} or any(index>1 for index in indices):
            raise ValueError('Unexpected compact policy jump table')
        small.update(first+i for i,index in enumerate(indices) if targets[index]==0x1004c491)
    return small


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('dll','matrix','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    cipher_tables(args.dll)  # exact DLL revision gate before RVA interpretation
    raw=args.dll.read_bytes()
    small=policy_ids(raw,read_rva)
    matrix=json.loads(args.matrix.read_text(encoding='utf-8'))
    if isinstance(matrix,dict) and 'routes' in matrix:
        models=[dict(model,observedPayloadSize=route['payloadSize'])
                for route in matrix['routes'] for model in route['models']]
        models.extend(dict(model,observedCompileError=model['error']) for model in matrix.get('failures',[]))
        if len({model['cameraId'] for model in models})!=len(models):
            raise ValueError('Duplicate model IDs in route evidence')
    else:
        models=load_models(args.matrix)
    rows=[dict(model,
               descriptorPrefixBytes=0x1d44 if model['cameraId'] in small else 0x39cc,
               contextPolicy=0 if model['cameraId'] in small else 1)
          for model in models]
    report=dict(cameraAccess=False,readOnly=True,cameraCompatibility='not-tested',
                dllSha256=hashlib.sha256(raw).hexdigest(),functionRva='0x4c3b0',
                scope='Compact builder descriptor prefix selection only; not all camera compiler routes',rows=rows)
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(report,output,indent=2)
    print(json.dumps({'routes':len(rows),'smallDescriptorPrefix':sum(row['contextPolicy']==0 for row in rows)}))


if __name__=='__main__': main()
