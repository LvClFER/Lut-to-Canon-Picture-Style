"""Compare observed internal dense samples with decoded PF3 table words."""
import argparse
import json
import struct
from itertools import permutations
from pathlib import Path
from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records


def validate(trace, tables):
    checks = []
    for row in trace['files']:
        items = [item for item in row['mlibCalls']['captures'] if item['functionRva'] == '0x196a0']
        for table_id, item in zip(('0x1070', '0x1071'), items):
            words = struct.unpack('>' + 'H' * (len(tables[table_id]) // 2), tables[table_id])
            # Decoded disk records are BE; the Canon API representation is separate.
            if words[:3] != (12, 3, 33):
                raise ValueError('Unexpected dense table header')
            if item.get('sourceDenseFloat64Hex'):
                raw = bytes.fromhex(item['sourceDenseFloat64Hex'])
                if len(raw) != 33 ** 3 * 3 * 8:
                    raise ValueError('Unexpected initialized dense byte count')
                values = struct.unpack('<107811d', raw)
                error = max(abs(a - b / 4095) for a, b in zip(values, words[3:]))
                checks.append({'model': row['model'], 'table': table_id, 'offset': 12,
                               'completeTable': True, 'valueCount': len(values),
                               'maxError': error, 'passed': error <= 1e-14})
                if item.get('outputDenseFloat64Hex') and not item.get('optionalCurves300Hex'):
                    import numpy as np
                    from .compact_grid_reference import compact_flag1, compact_flag2
                    header = bytes.fromhex(item['outputHeader24Hex'])
                    flag = struct.unpack_from('<I', header, 12)[0]
                    if flag in (1, 2):
                        source = np.array(values).reshape(33,33,33,3)
                        expected = compact_flag1(source) if flag == 1 else compact_flag2(source)
                        actual = np.frombuffer(bytes.fromhex(item['outputDenseFloat64Hex']), dtype='<f8').reshape(3,10,10,10)
                        error = float(np.max(np.abs(actual - expected)))
                        checks.append({'model': row['model'], 'table': table_id, 'flag': flag,
                                       'completeCompactOutput': True, 'valueCount': actual.size,
                                       'maxError': error, 'passed': error <= 1e-10})
            for layout in item['sourceGrid']['candidateLayouts']:
                candidates = []
                for axes in permutations(range(3)):
                    for order in permutations(range(3)):
                        errors = []
                        for sample in layout['samples']:
                            index = sample['index']
                            xyz = (index // 1089, index // 33 % 33, index % 33)
                            mapped = xyz[axes[0]] * 1089 + xyz[axes[1]] * 33 + xyz[axes[2]]
                            start = 3 + mapped * 3
                            expected = [words[start + channel] / 4095 for channel in order]
                            errors.extend(abs(a - b) for a, b in zip(expected, sample['rgb']))
                        candidates.append((max(errors), axes, order))
                error, axes, order = min(candidates)
                checks.append({'model': row['model'], 'table': table_id,
                               'diskAxisOrder': axes,
                               'offset': layout['offset'], 'diskChannelOrder': order, 'maxError': error,
                               'passed': error <= 1e-14})
    return {'cameraAccess': False, 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('trace', 'source', 'dll', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--per-file-source', action='store_true', help='Compare each trace row with its captured source path/hash')
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    result = {'cameraAccess': False, 'checks': []}
    for row in trace['files']:
        source = Path(row['source']) if args.per_file_source else args.source
        raw = source.read_bytes()
        if args.per_file_source:
            import hashlib
            if hashlib.sha256(raw).hexdigest() != row['sourceSha256']:
                raise ValueError('Trace source changed since capture')
        records, tail = parse_records(decode(raw[12:], keys, 12))
        if tail:
            raise ValueError('Unexpected undecoded tail')
        checks = validate({'files': [row]}, {record['id']: record['data'] for record in records})['checks']
        for check in checks:
            check['source'] = str(source)
        result['checks'].extend(checks)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    full = [check for check in result['checks'] if check.get('completeTable')]
    compact = [check for check in result['checks'] if check.get('completeCompactOutput')]
    print(json.dumps({'fullTables': len(full), 'passedFullTables': sum(check['passed'] for check in full),
                      'fullTableValues': sum(check['valueCount'] for check in full),
                      'maxFullTableError': max((check['maxError'] for check in full), default=None),
                      'compactOutputs': len(compact), 'passedCompactOutputs': sum(check['passed'] for check in compact),
                      'maxCompactError': max((check['maxError'] for check in compact), default=None)}))


if __name__ == '__main__':
    main()
