"""Summarize observed Basic reads without inferring camera support."""
from collections import Counter
import json
from pathlib import Path


def summarize(report):
    for key in ('cameraAccess','compilerPatched','sourceFilesModified'):
        if report.get(key) is not False:
            raise ValueError('Require unchanged offline evidence')
    rows=[];seen=set()
    for row in report['rows']:
        source=row.get('source',row.get('sourceName'))
        if not source:raise ValueError('Missing source identity')
        identity=(row['cameraId'],source,row['mutation'])
        if identity in seen:raise ValueError('Duplicate compilation cell')
        seen.add(identity)
        if row['mutation']!='control':raise ValueError('Require unmodified source compilation')
        reads=row.get('basicReads')
        if reads is None:
            status='observer-missing';fields=[];failed=[]
        else:
            if len(reads)>=64:raise ValueError('Bounded observer may have truncated evidence')
            selected=[item for item in reads if item['stage']=='compile']
            fields=sorted({item['property'] for item in selected})
            if any(int(field,16) not in range(0x1030,0x1036) for field in fields):
                raise ValueError('Unexpected observed field')
            failed=[item['property'] for item in selected if item['rc']!=0]
            status='observed' if fields else 'no-reads-at-observed-getter'
        rows.append(dict(model=row['model'],cameraId=row['cameraId'],compiled=row['compiled'],
                         observation=status,readFields=fields,failedReadFields=failed,
                         physicalCompatibility='not-tested'))
    return dict(cameraAccess=False,compilerPatched=False,
                scope='Observed 4ef20 reads only; not proof of every accessor or camera support',
                counts=dict(Counter(row['observation'] for row in rows)),rows=rows)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=summarize(json.loads(args.report.read_text(encoding='utf-8')))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(result['counts'])
