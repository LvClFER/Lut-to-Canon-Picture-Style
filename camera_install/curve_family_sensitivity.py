"""Compare complete native hashes for paired private1019 curve sources."""
import json
from pathlib import Path

SOURCES=('01_IDENTITY.pf3',)+tuple(f'CURVE_1019_CHANNEL{i}_END230.pf3' for i in range(3))


def summarize(report):
    if any(report.get(key) is not False for key in ('cameraAccess','compilerPatched','sourceFilesModified')):
        raise ValueError('Require unchanged offline evidence')
    groups={}
    for row in report['rows']:
        if row['mutation']!='control' or row['sourceName'] not in SOURCES:
            raise ValueError('Unexpected source or runtime mutation')
        group=groups.setdefault(row['cameraId'],{})
        if row['sourceName'] in group:raise ValueError('Duplicate source/model cell')
        group[row['sourceName']]=row
    result=[]
    for identifier,group in groups.items():
        if set(group)!=set(SOURCES):raise ValueError('Incomplete paired-source coverage')
        baseline=group[SOURCES[0]];valid=all(row['compiled'] for row in group.values())
        item=dict(model=baseline['model'],cameraId=identifier,allFourCompile=valid,
                  physicalCompatibility='not-tested',channelEqualsBaseline=None)
        lookup=baseline.get('recordLookups')
        item['observedCompileLookup1019Count']=(lookup.get('1019',{}).get('count',0)
                                               if lookup is not None else None)
        if valid:
            for row in group.values():
                if any(row.get(key)!=0 for key in ('rcCreate','rcId','rcDescriptor','rcSize','rcGet')):
                    raise ValueError('Compiled flag contradicts native API gates')
            item['channelEqualsBaseline']=[group[source]['payloadSize']==baseline['payloadSize'] and
                group[source]['payloadSha256']==baseline['payloadSha256'] for source in SOURCES[1:]]
            item['payloadSize']=baseline['payloadSize']
        else:
            item['failedSources']=[source for source,row in group.items() if not row['compiled']]
        result.append(item)
    if not result:raise ValueError('Empty coverage')
    return dict(cameraAccess=False,compilerPatched=False,
                scope='Complete native output hash sensitivity; not physical appearance or every descriptor',rows=result)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=summarize(json.loads(args.report.read_text(encoding='utf-8')))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
