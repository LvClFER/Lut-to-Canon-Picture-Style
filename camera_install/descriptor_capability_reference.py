"""Independent observed4b4f0 word test on normalized internal descriptors."""
import hashlib
import struct


def capability_word(normalized,modern,style_ordinal,index):
    size,stride=(0x39cc,0x9a0) if modern else (0x1d44,0x5d8)
    if len(normalized)!=size or not 0<=style_ordinal<=5 or index not in (0,1,2):
        raise ValueError('Unverified descriptor geometry or selector')
    offset=0x1ee+style_ordinal*stride+index*2
    word=struct.unpack_from('<H',normalized,offset)[0]
    return dict(offset=offset,word=word,enabled=word==1)


def verify(report,incoming):
    if any(report.get(key) is not False for key in ('cameraAccess','compilerPatched','sourceFilesModified')):
        raise ValueError('Require unchanged offline evidence')
    if hashlib.sha256(incoming).hexdigest() not in report.get('inputHashes',{}).values():
        raise ValueError('Incoming descriptor is not among the verified inputs')
    rows=[]
    for row in report['rows']:
        copies=row.get('descriptorCopies')
        if copies is None:raise ValueError('Missing bounded descriptor-copy observer')
        descriptions=[]
        for copy in copies:
            data=bytes.fromhex(copy['dataHex'])
            if len(data)!=copy['length'] or len(data) not in (0x1d44,0x39cc):raise ValueError('Copy length mismatch')
            descriptions.append(dict(length=len(data),sha256=hashlib.sha256(data).hexdigest(),
                equalsIncomingPrefix=data==incoming[:len(data)],
                changedBytesAgainstIncomingPrefix=(sum(a!=b for a,b in zip(data,incoming))
                    if len(incoming)>=len(data) else None)))
        checks=[]
        for gate in row['descriptorGates']:
            if not gate['descriptorCopySucceeded']:
                if gate['enabled']:raise ValueError('Failed descriptor copy reported enabled')
                checks.append(dict(index=gate['index'],copySucceeded=False,enabled=False,agrees=True))
                continue
            copy=copies[gate['descriptorCopyIndex']]
            expected=capability_word(bytes.fromhex(copy['dataHex']),gate['descriptorReaderRva']=='0x47290',
                                     gate['styleOrdinal'],gate['index'])
            if (expected['offset']!=gate['descriptorFlagOffset'] or expected['word']!=gate['descriptorFlagWord']
                    or expected['enabled']!=gate['enabled']):raise ValueError('Native flag hypothesis contradicted')
            checks.append(dict(expected,index=gate['index'],copySucceeded=True,agrees=True))
        rows.append(dict(model=row['model'],cameraId=row['cameraId'],copies=descriptions,checks=checks,
                         compiled=row['compiled'],physicalValidation=False))
    return dict(cameraAccess=False,scope='4b4f0 only; normalized internal copy, not raw descriptor offsets',rows=rows)


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('descriptor',type=Path)
    parser.add_argument('output',type=Path);args=parser.parse_args()
    result=verify(json.loads(args.report.read_text(encoding='utf-8')),args.descriptor.read_bytes())
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print('Verified descriptor gates:',sum(len(row['checks']) for row in result['rows']))
