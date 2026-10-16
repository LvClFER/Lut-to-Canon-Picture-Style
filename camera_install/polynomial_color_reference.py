"""Independent 19-term cubic color basis observed in MLib, research only."""
import argparse
import json
import math
import struct
from pathlib import Path

EXPONENTS = ((1,0,0),(0,1,0),(0,0,1),(2,0,0),(1,1,0),(1,0,1),
             (0,2,0),(0,1,1),(0,0,2),(3,0,0),(2,1,0),(2,0,1),
             (1,2,0),(1,1,1),(1,0,2),(0,3,0),(0,2,1),(0,1,2),(0,0,3))


def basis(rgb):
    if len(rgb) != 3 or not all(math.isfinite(value) for value in rgb):
        raise ValueError('Expected three finite components')
    # The native basis multiplies factors left-to-right. Python pow (and
    # grouping R*(B*B)) can differ by one ULP, changing later integer truncation.
    return [math.prod(value for value, exponent in zip(rgb, powers)
                      for _ in range(exponent)) for powers in EXPONENTS]


def transform(rgb, coefficients):
    if len(coefficients) != 57 or not all(math.isfinite(value) for value in coefficients):
        raise ValueError('Expected 3 x 19 finite polynomial coefficients')
    terms = basis(rgb)
    # Canon accumulates sequentially; retain order rather than using a BLAS dot.
    outputs = []
    for row in range(3):
        result = 0.0
        for index, term in enumerate(terms): result += coefficients[row*19+index] * term
        outputs.append(result)
    return outputs


def disk_coefficients(data):
    if len(data) != 240: raise ValueError('Expected 240-byte coefficient record')
    words = struct.unpack('>60i', data)
    return [words[row*20+column] / 65536 for row in range(3) for column in range(19)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--basis-probe', type=Path, required=True)
    parser.add_argument('--trace', type=Path)
    parser.add_argument('--dll', type=Path, help='Verify coefficients against each captured PF3 source')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    for row in json.loads(args.basis_probe.read_text(encoding='utf-8'))['rows']:
        expected=basis(row['rgb'])
        error = max(abs(a-b) for a,b in zip(expected, row['values']))
        exact=expected==row['values']
        checks.append({'kind': 'basis', 'maxError': error, 'exact':exact,'passed':exact})
    if args.trace:
        for row in json.loads(args.trace.read_text(encoding='utf-8'))['files']:
            records = {}
            if args.dll:
                from .compiler_regression import cipher_tables, decode
                from .pf3_research import parse_records
                raw = Path(row['source']).read_bytes()
                import hashlib
                if hashlib.sha256(raw).hexdigest() != row['sourceSha256']: raise ValueError('Source hash differs')
                parsed, tail = parse_records(decode(raw[12:], cipher_tables(args.dll), 12))
                if tail: raise ValueError('Unexpected PF3 tail')
                records = {record['id']: disk_coefficients(record['data']) for record in parsed
                           if record['id'] in ('0x1021','0x1029')}
            for item in row['mlibCalls']['captures']:
                if item['functionRva'] != '0x1d380': continue
                if not item.get('output'): raise ValueError('Incomplete observed polynomial output')
                coefficients = struct.unpack('<57d', bytes.fromhex(item['coefficientsFloat64Hex']))
                if records:
                    candidates = {identifier + ':16.16': expected for identifier, expected in records.items()}
                    candidates.update({identifier + ':16.16-trunc1e6': [math.trunc(value*1e6)/1e6 for value in expected]
                                       for identifier, expected in records.items()})
                    matches = [identifier for identifier, expected in candidates.items() if tuple(expected) == coefficients]
                    identity_scale = coefficients[0]
                    is_identity = identity_scale in (1.0, .999984) and all(value == (identity_scale if index % 19 == index // 19 else 0)
                                                                         for index, value in enumerate(coefficients))
                    checks.append({'kind': 'disk-coefficients', 'model': row['model'], 'phase': item.get('phase'),
                                   'matchingRecords': matches, 'synthesizedIdentity': not matches and is_identity,
                                   'classification': 'source-record' if matches else ('identity-intermediate' if is_identity else 'unmapped'),
                                   'maxError': 0 if matches or is_identity else min(max(abs(a-b) for a,b in zip(coefficients, values)) for values in candidates.values()),
                                   'passed': bool(matches) or is_identity})
                error = max(abs(a-b) for a,b in zip(transform(item['input'], coefficients), item['output']))
                checks.append({'kind': 'compiler', 'model': row['model'], 'callIndex': item['callIndex'],
                               'maxError': error, 'passed': error <= 1e-12 and item['result'] == 0})
    report = {'cameraAccess': False, 'checks': checks, 'passed': sum(check['passed'] for check in checks)}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(checks), 'passed': report['passed'], 'maxError': max(check['maxError'] for check in checks)}))


if __name__ == '__main__': main()
