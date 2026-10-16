"""Identify observed native curve argument slots from single-field reports."""
import json
from pathlib import Path

CURVE_KEYS=('preCurvesHex','postCurvesHex','thirdCurvesHex')


def captures(row):
    result=[c['initializedArguments'] for c in row['mlibCalls']['captures'] if c['functionRva']=='0x11220']
    if not result:raise ValueError('Missing native initialized-argument capture')
    for arguments in result:
        if any(len(bytes.fromhex(arguments[key]))!=300 for key in CURVE_KEYS):
            raise ValueError('Unexpected curve argument size')
    return result


def identify(report):
    if any(report.get(key) is not False for key in ('cameraAccess','compilerPatched','writesOriginals')):
        raise ValueError('Require unmodified offline compiler evidence')
    baseline=captures(report['baseline']);rows=[]
    for experiment in report['experiments']:
        if any(experiment.get(key)!=0 for key in ('rcCreate','rcId','rcDescriptor','rcSize','rcGet')):
            raise ValueError('Native compile failed')
        prop=int(experiment['mutationProperty'],16)
        if prop not in (0x40001018,0x40001019,0x40001065):raise ValueError('Unexpected curve property')
        if not experiment['serializedMutationExact'] or experiment['changedSerializedFields']!=[f'0x{prop & 0xffff:04x}']:
            raise ValueError('Single-field serialization not proven')
        observed=captures(experiment)
        if len(observed)!=len(baseline):raise ValueError('Native capture coverage differs')
        slots=[]
        for before,after in zip(baseline,observed):
            changed=[key for key in CURVE_KEYS if before[key]!=after[key]]
            if len(changed)!=1:raise ValueError('Expected one changed native curve group')
            slots.append(changed[0])
        if len(set(slots))!=1:raise ValueError('Inconsistent argument placement')
        rows.append(dict(name=experiment['name'],sourceProperty=hex(prop),nativeArgument=slots[0],
                         observedBranches=len(slots),changedOutputBytes=experiment['changedByteCount']))
    if not rows:raise ValueError('Empty experiment report')
    return dict(cameraAccess=False,physicalValidation=False,rows=rows)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=identify(json.loads(args.report.read_text(encoding='utf-8')))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
