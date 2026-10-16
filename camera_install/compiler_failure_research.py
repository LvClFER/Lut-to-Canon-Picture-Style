"""Summarize failed offline compilations without claiming camera incompatibility."""
import argparse
import json
from pathlib import Path


def summarize(report):
    if report.get('cameraAccess') is not False or report.get('compilerPatched') is not False:
        raise ValueError('Requires an explicitly offline, unpatched compiler report')
    rows = []
    for case in report.get('files', []):
        api_errors={key:case[key] for key in ('rcCreate','rcId','rcDescriptor','rcSize','rcGet')
                    if case.get(key) not in (None,0)}
        failed = bool(api_errors) or bool(case.get('error'))
        reads = [capture for capture in case.get('mlibCalls', {}).get('captures', [])
                 if capture.get('functionRva') == '0x4ef20Raw' and capture.get('rc') not in (None, 0)]
        missing = sorted({(item['property'], item['size']) for item in reads})
        if not failed:
            category = 'no-failure-observed'
        elif 'rcId' in api_errors:
            category = 'camera-id-setup-rejected'
        elif any(key in api_errors for key in ('rcCreate','rcDescriptor','rcSize')):
            category = 'upstream-compiler-api-failure'
        elif any(prop == '0x1007' and size == 1460 for prop, size in missing):
            category = 'legacy-metadata-read-failed'
        elif any(prop in ('0x1022', '0x102a') and size == 4096 for prop, size in missing):
            category = 'derived-4096-table-read-failed'
        else:
            category = 'unclassified-compiler-failure'
        rows.append({'model': case.get('model'), 'cameraId': case.get('cameraId'),
                     'source': case.get('source'), 'rcGet': case.get('rcGet'),
                     'apiErrors':api_errors,
                     'category': category, 'failedReads': [dict(property=p, size=s) for p, s in missing],
                     'cameraCompatibility': 'not-tested'})
    return {'cameraAccess': False, 'compilerPatched': False,
            'dllSha256': report.get('dllSha256'), 'descriptorSha256': report.get('descriptorSha256'),
            'cases': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.trace.read_text(encoding='utf-8')))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
    for case in result['cases']:
        print(case['model'], case['category'], case['failedReads'])


if __name__ == '__main__':
    main()
