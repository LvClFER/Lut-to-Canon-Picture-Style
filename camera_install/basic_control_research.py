"""Private read-only comparison of scalar controls across native compiler routes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from .base_style_research import native_blocks


def changed_ranges(before, after):
    if len(before) != len(after):
        raise ValueError('Native payload size changed; comparison requires identical geometry')
    result = []
    start = None
    for index, (a, b) in enumerate(zip(before, after)):
        if a != b and start is None:
            start = index
        elif a == b and start is not None:
            result.append([start, index])
            start = None
    if start is not None:
        result.append([start, len(before)])
    return result


def packed_outputs(row):
    return [(capture['functionRva'], hashlib.sha256(bytes.fromhex(capture['nativePackedHex'])).hexdigest())
            for capture in row.get('mlibCalls', {}).get('captures', [])
            if capture.get('nativePackedHex')]


def read_payload(row):
    payload = Path(row['privateResearchPayload']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != row['payloadSha256']:
        raise ValueError('Private payload hash differs from native trace')
    if len(payload) != row['payloadSize']:
        raise ValueError('Private payload size differs from native trace')
    return payload


def compare(trace, auxiliary=False):
    routes = {}
    for row in trace['files']:
        if row.get('error') or row.get('rcGet') != 0:
            raise ValueError('Unsuccessful native compilation in trace')
        if hashlib.sha256(Path(row['source']).read_bytes()).hexdigest() != row['sourceSha256']:
            raise ValueError('Source fixture hash differs from native trace')
        routes.setdefault(row['cameraId'], []).append(row)
    checks = []
    for camera_id, rows in routes.items():
        baselines = [r for r in rows if Path(r['source']).stem == '01_IDENTITY']
        if len(baselines) != 1:
            raise ValueError('Exactly one identity baseline required per route')
        baseline = baselines[0]
        before = read_payload(baseline)
        packs = packed_outputs(baseline)
        for row in rows:
            stem = Path(row['source']).stem
            if row is baseline:
                continue
            allowed = ({'AUX_FLAG_100C_VALUE0','AUX_FLAG_1011_VALUE1','AUX_FLAG_1012_VALUE1','AUX_FLAG_1080_VALUE1'}
                       if auxiliary else {f'BASIC_4000103{i}' for i in range(6)})
            if stem not in allowed:
                raise ValueError('Unexpected control fixture; registration state is not in scope')
            after = read_payload(row)
            changes = changed_ranges(before, after)
            current = packed_outputs(row)
            checks.append(dict(cameraId=camera_id, model=row['model'], source=stem,
                               payloadSize=len(after), changedBytes=sum(end-start for start,end in changes),
                               changedRanges=changes, observedPackers=len(current),
                               packerOutputsEqual=(current == packs) if packs and current else None,
                               payloadSha256=row['payloadSha256']))
    return dict(cameraAccess=False, compilerPatched=False, physicalCompatibilityEstablished=False,
                rangeConvention='zero-based start inclusive, end exclusive', checks=checks)


def verify_editor_exports(trace, baseline_trace):
    baselines = {(r['cameraId'],Path(r['source']).stem):r for r in baseline_trace['files']}
    checks = []
    for row in trace['files']:
        if row.get('error') or row.get('rcGet') != 0:
            raise ValueError('Unsuccessful native editor export compilation')
        source = Path(row['source'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sourceSha256']:
            raise ValueError('Editor source hash mismatch')
        name = source.stem
        if not name.endswith('_EDITOR_EXPORT'):
            raise ValueError('Not a verified editor-mapping fixture')
        baseline = baselines[(row['cameraId'],name.removesuffix('_EDITOR_EXPORT'))]
        before, after = read_payload(baseline), read_payload(row)
        if len(after) == 16752:
            offset = 76
        elif len(after) in (78980,83076,431616):
            offset = 80
        else:
            raise ValueError('Editor verification requires an observed Basic header layout')
        words = struct.unpack_from('<8i',after,offset)
        expected = (-2,5,2,-1,2,3)
        actual = words[:4]+words[6:]
        same_tables = native_blocks(before) == native_blocks(after)
        allowed = set(range(offset,offset+16)) | set(range(offset+24,offset+32))
        changed = {i for i,(a,b) in enumerate(zip(before,after)) if a != b}
        ok = actual == expected and same_tables and changed <= allowed
        checks.append(dict(cameraId=row['cameraId'],source=name,payloadSize=len(after),
                           actualControls=list(actual),expectedControls=list(expected),
                           nativeColorBlocksUnchanged=same_tables,
                           onlyIntendedHeaderFieldsChanged=changed <= allowed,ok=ok))
    return dict(cameraAccess=False,compilerPatched=False,physicalCompatibilityEstablished=False,
                checks=checks,passed=sum(row['ok'] for row in checks),cases=len(checks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-trace', type=Path, help='Verify corrected editor exports against the earlier five-base native trace')
    parser.add_argument('--auxiliary-flags', action='store_true', help='Compare the four bounded auxiliary flag fixtures instead of Basic scalar fixtures')
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    result = (verify_editor_exports(trace,json.loads(args.baseline_trace.read_text(encoding='utf-8')))
              if args.baseline_trace else compare(trace,args.auxiliary_flags))
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if args.baseline_trace:
        print(result['passed'], '/', result['cases'], 'native editor Basic mappings verified')
        if not result['cases'] or result['passed'] != result['cases']:
            raise SystemExit(1)
        return
    for row in result['checks']:
        print(row['model'], row['source'], row['changedBytes'], 'bytes changed;',
              'packer equality:', row['packerOutputsEqual'], row['changedRanges'][:12])


if __name__ == '__main__':
    main()
