"""Trace source-to-packer-to-payload evidence, without camera validation."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records
from .packed10_reference import decoded_payload_blocks


def compare_dense(source_words, captured_hex):
    if len(source_words) != 107814 or source_words[:3] != (12, 3, 33):
        raise ValueError('Require a complete 33-cubed disk table')
    raw = bytes.fromhex(captured_hex)
    if len(raw) != 107811 * 8:
        raise ValueError('Require bounded complete float64 capture')
    values = struct.unpack('<107811d', raw)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Non-finite dense source capture')
    error = max(abs(a-b/4095) for a,b in zip(values,source_words[3:]))
    return dict(valueCount=len(values),maxError=error,passed=error <= 1e-14)


def audit(report, source, keys):
    if report.get('cameraAccess') is not False or report.get('compilerPatched') is not False:
        raise ValueError('Requires private unpatched offline evidence')
    if hashlib.sha256(source).hexdigest() != report['sourceSha256']:
        raise ValueError('Source differs from captured fixture')
    records,tail = parse_records(decode(source[12:],keys,12))
    if tail:
        raise ValueError('Incomplete decoded source')
    tables = {item['id']:item['data'] for item in records}
    rows=[]
    for row in report['rows']:
        if row.get('error'):
            rows.append(dict(model=row['model'],classification='failed-not-validated'))
            continue
        payload=Path(row['privatePayload']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row['payloadSha256']:
            raise ValueError('Retained payload differs from trace')
        captures=row['mlibCalls']['captures']
        dense=[]
        for item in captures:
            if item.get('functionRva')=='0x196a0' and item.get('sourceDenseFloat64Hex'):
                table='0x1070' if item['converterOption']==1 else '0x1071'
                check=compare_dense(struct.unpack('>107814H',tables[table]),item['sourceDenseFloat64Hex'])
                dense.append(dict(table=table,**check))
        blocks=decoded_payload_blocks(payload,keys)
        packed=[]
        for item in captures:
            if item.get('functionRva') not in ('0x4b760','0x49e00') or not item.get('nativePackedHex'):
                continue
            data=bytes.fromhex(item['nativePackedHex'])
            locations=[dict(offset=offset,seed=seed) for offset,seed,block in blocks if data==block]
            packed.append(dict(functionRva=item['functionRva'],sha256=hashlib.sha256(data).hexdigest(),
                               finalPayloadLocations=locations))
        rows.append(dict(model=row['model'],seedByte=row['seedByte'],sourceChecks=dense,packerChecks=packed))
    return dict(cameraAccess=False,compilerPatched=False,cameraCompatibility='not-tested',
                scope='Intermediate conversion is distinct from final arbitrary-LUT acceptance',rows=rows)


def compare_final_tables(first, second, keys):
    """Exclude header/name differences; require exact matching route and seed."""
    for report in (first,second):
        if report.get('cameraAccess') is not False or report.get('compilerPatched') is not False:
            raise ValueError('Requires private unpatched offline evidence')
    if first['sourceSha256']==second['sourceSha256']:
        raise ValueError('Require distinct source vectors')
    for field in ('dllSha256','descriptorSha256','researchAgentSha256'):
        if not first.get(field) or first[field]!=second.get(field):
            raise ValueError('Mismatched or missing comparison provenance: '+field)
    for field in ('seedMode','explicitDenseConversion'):
        if first.get(field)!=second.get(field):
            raise ValueError('Different experimental preconditioning: '+field)
    def index(report):
        result={}
        for row in report['rows']:
            key=(row['cameraId'],row['seedByte'])
            if key in result:
                raise ValueError('Duplicate route/seed')
            result[key]=row
        return result
    left,right=index(first),index(second)
    if set(left)!=set(right):
        raise ValueError('Route/seed coverage differs')
    rows=[]
    for key,a in left.items():
        b=right[key]
        if a.get('error') or b.get('error'):
            rows.append(dict(model=a['model'],seedByte=key[1],classification='failed-not-validated'))
            continue
        payloads=[]
        for row in (a,b):
            data=Path(row['privatePayload']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=row['payloadSha256']:
                raise ValueError('Retained payload differs from trace')
            payloads.append(data)
        if len(payloads[0])!=len(payloads[1]):
            raise ValueError('Native layouts differ')
        blocks=[final_color_regions(data) for data in payloads]
        if [(o,len(data)) for o,data in blocks[0]]!=[(o,len(data)) for o,data in blocks[1]]:
            raise ValueError('Unmapped or mismatched native table layout')
        # Canon's equal-position XOR cancels in pairwise comparisons. Do not
        # imply that these regions' image semantics have been validated.
        checks=[dict(offset=offset,length=len(x),changedBytes=sum(p!=q for p,q in zip(x,y)))
                for (offset,x),(_,y) in zip(*blocks)]
        rows.append(dict(model=a['model'],cameraId=key[0],seedByte=key[1],tables=checks,
                         colorTablesDiffer=any(item['changedBytes'] for item in checks)))
    return dict(cameraAccess=False,cameraCompatibility='not-tested',
                scope='Distinct final table bytes, not physical image validation',rows=rows)


def final_color_regions(payload):
    size=len(payload)
    compact={8528:(336,2),16720:(336,4),16744:(360,4),16752:(368,4)}
    if size in compact:
        start,count=compact[size]
        regions=[(start+index*4096,4096) for index in range(count)]
    elif size in (78980,83076):
        regions=[(372+index*19652,19652) for index in range(4)]
        if size==83076: regions.append((78980,4096))
    elif size==431616:
        regions=[(372,215622),(215994,215622)]
    else:
        raise ValueError('Unmapped native color region layout')
    if regions[-1][0]+regions[-1][1]!=size:
        raise ValueError('Incomplete native region coverage')
    return [(offset,payload[offset:offset+length]) for offset,length in regions]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','source','dll','output'):
        parser.add_argument('--'+key,type=Path,required=key!='source')
    parser.add_argument('--compare-trace',type=Path)
    args=parser.parse_args()
    trace=json.loads(args.trace.read_text(encoding='utf-8'))
    keys=cipher_tables(args.dll)
    if args.compare_trace:
        result=compare_final_tables(trace,json.loads(args.compare_trace.read_text(encoding='utf-8')),keys)
    else:
        if not args.source: parser.error('Source is required for the dense source audit')
        result=audit(trace,args.source.read_bytes(),keys)
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(result,output,indent=2)
    if args.compare_trace:
        print(json.dumps({'rows':len(result['rows']),
            'routesWithChangedColorTables':sum(row.get('colorTablesDiffer',False) for row in result['rows'])}))
    else:
        print(json.dumps({'rows':len(result['rows']),
            'sourceChecks':sum(len(row.get('sourceChecks',[])) for row in result['rows']),
            'packersInFinalPayload':sum(bool(check['finalPayloadLocations']) for row in result['rows'] for check in row.get('packerChecks',[]))}))


if __name__=='__main__': main()
