"""Check two old carrier fields against independently decoded PF2 records."""
import argparse
import hashlib
import json
from pathlib import Path
from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records


def swap32(data):
    if len(data) % 4:
        raise ValueError('Unaligned numeric record')
    return b''.join(data[index:index+4][::-1] for index in range(0,len(data),4))


def check_aliases(payload, fields, keys):
    if len(payload) not in (8164,8168):
        raise ValueError('Only the observed diagnostic old layouts are permitted')
    offset = 0x600 if len(payload) == 8164 else 0x700
    curve = payload[offset:offset+300]
    coefficients = decode(payload[offset+300:offset+540],keys,0x3f194)
    if len(fields[0x1018]) != 300 or len(fields[0x1029]) != 240:
        raise ValueError('Unexpected source field geometry')
    return dict(legacy1004EqualsSource1018=curve == swap32(fields[0x1018]),
                legacy1005EqualsSource1029=coefficients == swap32(fields[0x1029]),
                curveOffset=offset,coefficientOffset=offset+300,
                coefficientCipherSeed=0x3f194)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','source','trace','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    source = args.source.read_bytes()
    records,tail = parse_records(decode(source[12:],keys,12))
    if tail or not records or records[-1]['id'] != '0xffff':
        raise ValueError('Incomplete source records')
    fields = {int(record['id'],16):record['data'] for record in records}
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    if trace.get('cameraAccess') is not False or trace.get('compilerPatched') is not False or trace.get('sourceSha256') != hashlib.sha256(source).hexdigest():
        raise ValueError('Trace does not identify the same offline source')
    report = dict(cameraAccess=False,compilerPatched=False,diagnosticPayloadsNotInstallable=True,rows=[])
    for case in trace['rows']:
        if case.get('rcGet') != 0 or case.get('error'):
            continue
        payload = Path(case['privatePayload']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != case.get('payloadSha256'):
            raise ValueError('Payload hash differs from trace')
        row = check_aliases(payload,fields,keys)
        row.update(model=case['model'],seedByte=case['seedByte'])
        report['rows'].append(row)
    if not report['rows']:
        raise ValueError('No successful diagnostic outputs to inspect')
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(report,output,indent=2)
    print(len(report['rows']),'outputs;',sum(row['legacy1004EqualsSource1018'] and row['legacy1005EqualsSource1029'] for row in report['rows']),'exact alias pairs')


if __name__ == '__main__':
    main()
