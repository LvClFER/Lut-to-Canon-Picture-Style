"""Bounded read-only-file experiment: PSE reference bank versus arbitrary dense grids."""
import argparse
import hashlib
import json
from itertools import zip_longest
from pathlib import Path

from .compiler_regression import cipher_tables
from .pf3_field_experiments import compile_stock


def compact_snapshots(result):
    for stage in ('before', 'afterMutation', 'afterInputs', 'afterCompile'):
        for item in result.get(stage, {}).values():
            data = bytes.fromhex(item.pop('dataHex', ''))
            if data:
                item['sha256'] = hashlib.sha256(data).hexdigest()
                item['prefixHex'] = data[:16].hex()
    for item in result.get('consumedRecords', []):
        data = bytes.fromhex(item.pop('dataHex', ''))
        if data:
            item['sha256'] = hashlib.sha256(data).hexdigest()
            item['prefixHex'] = data[:16].hex()


def byte_difference(reference, payload):
    changed = [i for i, (left, right) in enumerate(zip_longest(reference, payload)) if left != right]
    return dict(sameSize=len(reference) == len(payload), changedByteCount=len(changed),
                firstChangedOffset=changed[0] if changed else None,
                lastChangedOffset=changed[-1] if changed else None,
                identical=reference == payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append', required=True)
    parser.add_argument('--donor', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bank-controls', action='store_true', help='Active saturation positive control versus reference-bank saturation')
    parser.add_argument('--trace-selection', action='store_true', help='Observe known-revision record lookups and table builders, no override')
    parser.add_argument('--family-matrix', type=Path, help='Native-verified family report; trace one representative per internal class')
    parser.add_argument('--region-proof', action='store_true', help='Compare independently decoded payload regions with observed raw records')
    parser.add_argument('--family-class', type=int, choices=range(1, 11), action='append', help='Limit family matrix to specific internal classes')
    parser.add_argument('--all-models', action='store_true', help='Use every recorded native-verified ID instead of one representative per class')
    parser.add_argument('--camera-id', type=lambda value:int(value,0), action='append',
                        help='Select exact IDs already present in the native-verified family matrix')
    parser.add_argument('--control-only', action='store_true', help='Observe source compilation without scratch property mutations')
    parser.add_argument('--math-trace', action='store_true', help='Retain PRIVATE MLib numeric trace and payload for independent math comparison')
    args = parser.parse_args()
    if (args.family_class or args.all_models or args.camera_id) and not args.family_matrix:
        parser.error('--family-class/--all-models require --family-matrix')
    keys = cipher_tables(args.dll)
    originals = {p.resolve(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in args.source + [args.donor, args.descriptor, args.dll]}
    args.output.mkdir(parents=True, exist_ok=False)
    import frida
    device = frida.get_local_device()
    template = Path(__file__).with_name('high_bank_probe.js').read_text(encoding='utf-8')
    report = dict(cameraAccess=False, compilerPatched=False, sourceFilesModified=False,
                  inputHashes={str(p): h for p, h in originals.items()}, rows=[])
    math_trace = dict(cameraAccess=False, compilerPatched=False, files=[])
    models = [('M50', 1042), ('R8', 0x80000487)]
    if args.family_matrix:
        matrix = json.loads(args.family_matrix.read_text(encoding='utf-8'))
        if matrix['rules']['dllSha256'] != originals[args.dll.resolve()] or not all(row.get('nativeAgrees') for row in matrix['rows']):
            raise ValueError('Family matrix must agree with this exact native compiler')
        selected = {}
        for row in matrix['rows']:
            selected.setdefault(row['internalFamilyClass'], row)
        candidates = matrix['rows'] if args.all_models or args.camera_id else [row for _, row in sorted(selected.items())]
        if args.camera_id:
            known = {row['cameraId'] for row in matrix['rows']}
            if not set(args.camera_id) <= known:
                raise ValueError('Requested camera IDs missing from native-verified matrix')
            candidates = [row for row in candidates if row['cameraId'] in args.camera_id]
        models = [(row['model'], row['cameraId']) for row in candidates
                  if not args.family_class or row['internalFamilyClass'] in args.family_class]
        if not models:
            raise ValueError('No native-verified models match the requested selectors')
        if len({identifier for _, identifier in models}) != len(models):
            raise ValueError('Duplicate model IDs in native-verified matrix')
        report['familyMatrixSha256'] = hashlib.sha256(args.family_matrix.read_bytes()).hexdigest()
    try:
        for source in args.source:
            for model, camera_id in models:
                baseline = None
                mutations = (('control',) if args.control_only else ('control', 'grid1070') if args.family_matrix else ('control',) if args.trace_selection else
                             ('control', 'bank9032two', 'active1032two', 'active1011one')
                             if args.bank_controls else
                             ('control', 'grid1070', 'grid1071', 'bank9011zero', 'bank9011one'))
                for mutation in mutations:
                    configuration = dict(mutation=mutation, donor=str(args.donor.resolve()), traceSelection=args.trace_selection or bool(args.family_matrix) or args.region_proof)
                    agent = args.output / 'configured_agent.js'
                    agent.write_text('const EXPERIMENT=' + json.dumps(configuration) + ';\n' + template,
                                     encoding='utf-8')
                    try:
                        result, payload = compile_stock(device, args.dll.resolve(), agent,
                                                        source.resolve(), camera_id,
                                                        args.descriptor.read_bytes(), observe=args.math_trace,
                                                        observe_dense=args.math_trace)
                        result['compiled'] = True
                        if args.math_trace:
                            payload_path = args.output / ('private_numeric_' + str(len(math_trace['files'])) + '.bin')
                            with payload_path.open('xb') as private:
                                private.write(payload)
                            math_trace['files'].append(dict(source=str(source.resolve()), model=hex(camera_id),
                                mutation=mutation, privateResearchPayload=str(payload_path.resolve()),
                                payloadSha256=hashlib.sha256(payload).hexdigest(), mlibCalls=result['mlibCalls']))
                            (args.output / 'PRIVATE_MATH_TRACE.json').write_text(json.dumps(math_trace, indent=2), encoding='utf-8')
                        if args.region_proof:
                            from .payload_region_research import prove_regions
                            result['regionProof'] = prove_regions(payload, result.get('consumedRecords', []), keys)
                        if mutation == 'control':
                            baseline = payload
                        if baseline is not None:
                            result['differenceFromControl'] = byte_difference(baseline, payload)
                    except Exception as error:
                        result = dict(getattr(error, 'native_report', {}))
                        result.update(compiled=False, error=str(error))
                    compact_snapshots(result)
                    result.update(sourceName=source.name, model=model, cameraId=camera_id, mutation=mutation)
                    report['rows'].append(result)
                    (args.output / 'HIGH_BANK_RESULTS.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                    print(source.name, model, mutation, result['compiled'],
                          result.get('differenceFromControl', {}), flush=True)
    finally:
        changed = [str(p) for p, digest in originals.items() if hashlib.sha256(p.read_bytes()).hexdigest() != digest]
        report['sourceFilesModified'] = bool(changed)
        report['changedInputs'] = changed
        (args.output / 'HIGH_BANK_RESULTS.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        if changed:
            raise RuntimeError('Read-only input changed: ' + repr(changed))


if __name__ == '__main__':
    main()
