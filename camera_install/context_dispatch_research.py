"""Summarize observed PF2/PF3 context selection; never predict camera support."""
import argparse
import json
from pathlib import Path


def summarize(report):
    for field in ('cameraAccess', 'compilerPatched', 'sourceFilesModified'):
        if report.get(field) is not False:
            raise ValueError('Require unmodified offline compiler evidence')
    seen = set()
    rows = []
    for row in report['rows']:
        key = (row['sourceName'], row['cameraId'], row['mutation'])
        if key in seen:
            raise ValueError('Duplicate source/model/mutation cell')
        seen.add(key)
        events = row.get('contextDispatch', [])
        contexts = {event['name'] for event in events
                    if event['stage'] == 'compile' and event['name'] in ('baseOutput', 'pf3Output')}
        if len(contexts) > 1:
            raise ValueError('Mixed output contexts need separate call attribution')
        rows.append(dict(source=row['sourceName'], model=row['model'], cameraId=row['cameraId'],
                         mutation=row['mutation'], compiled=row['compiled'],
                         observedContext=next(iter(contexts), None),
                         outputSize=row.get('outputSize'),
                         changedBytes=row.get('differenceFromControl', {}).get('changedByteCount'),
                         observedBuilders=sorted({event['name'] for event in events
                                                  if event['stage'] == 'compile' and 'Builder' in event['name']})))
    return dict(cameraAccess=False, cameraCompatibility='not-tested',
                scope='Observed context selection only; absent hooks do not prove unreachable code',
                rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.source.read_text(encoding='utf-8')))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
    print('Observed cells:', len(result['rows']))


if __name__ == '__main__':
    main()
