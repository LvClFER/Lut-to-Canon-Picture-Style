"""Read-only private base-style field and native block comparisons."""
import argparse
import hashlib
import json
from pathlib import Path
from .compiler_regression import cipher_tables,decode
from .pf3_research import parse_records


def compare_records(records,baseline):
    if records.keys()!=baseline.keys():raise ValueError('Base styles have different record sets')
    return [{'id':identifier,'size':len(value),'baselineSize':len(baseline[identifier]),
             'sha256':hashlib.sha256(value).hexdigest()}
            for identifier,value in records.items() if value!=baseline[identifier]]


def native_blocks(payload):
    size=len(payload)
    if size==16752:return [payload[o:o+4096] for o in (368,4464,8560,12656)]
    if size in (78980,83076):
        result=[payload[o:o+19652] for o in (372,20024,39676,59328)]
        if size==83076:result.append(payload[78980:])
        return result
    if size==431616:return [payload[o:o+215622] for o in (372,215994)]
    raise ValueError('Unverified private base-style payload layout')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();trace=json.loads(args.trace.read_text(encoding='utf-8'));keys=cipher_tables(args.dll)
    sources={};native={};checks=[]
    for row in trace['files']:
        if row.get('error'):raise ValueError('Failed native compilation in trace')
        path=Path(row['source']);raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sourceSha256']:raise ValueError('Source fixture hash mismatch')
        records,tail=parse_records(decode(raw[12:],keys,12))
        if tail or not records or records[-1]['id']!='0xffff':raise ValueError('Incomplete private PF3 body')
        sources[path.stem]={r['id']:r['data'] for r in records}
        payload=Path(row['privateResearchPayload']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row['payloadSha256']:raise ValueError('Native payload hash mismatch')
        native.setdefault(row['cameraId'],{})[path.stem]=native_blocks(payload)
    baseline=sources['BASE_NEUTRAL_RP']
    for name,records in sources.items():
        checks.append(dict(source=name,changedRecords=compare_records(records,baseline),
                           baseSelectorHex=records['0x1009'].hex()))
    block_checks=[]
    for camera_id,styles in native.items():
        base=styles['BASE_NEUTRAL_RP']
        for name,blocks in styles.items():
            if len(blocks)!=len(base):raise ValueError('Native base-style block count changed')
            block_checks.append(dict(cameraId=camera_id,source=name,blocksEqualToNeutral=[a==b for a,b in zip(blocks,base)],
                                     storedBlockSha256=[hashlib.sha256(b).hexdigest() for b in blocks]))
    report=dict(cameraAccess=False,compilerPatched=False,physicalCompatibilityEstablished=False,
                fixtures='Private existing base styles; no redistribution assets',fields=checks,nativeBlocks=block_checks)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
