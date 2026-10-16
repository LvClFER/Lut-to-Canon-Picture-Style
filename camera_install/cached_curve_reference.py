"""Independent MLib cached-curve evaluator, initialized samples only."""
import argparse
import json
import math
import struct
from pathlib import Path


def evaluate(values, position, *, allow_negative_subsample=False):
    if not 2 <= len(values) <= 512 or not all(math.isfinite(value) for value in values):
        raise ValueError('Expected 2..512 finite cached curve samples')
    if not math.isfinite(position):
        raise ValueError('Negative/non-finite input is outside the verified safe domain')
    scaled = position * (len(values)-1)
    # Native cached indices are unsigned. Negative positions are safe only
    # while truncation remains zero; retain the negative fraction there.
    if position<0 and (not allow_negative_subsample or math.trunc(scaled)<0):
        raise ValueError('Negative/non-finite input is outside the verified safe domain')
    fraction = scaled - math.trunc(scaled)
    first = min(math.trunc(scaled), len(values)-1)
    second = min(math.trunc(scaled+1), len(values)-1)
    return values[second] * fraction + values[first] * (1-fraction)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--negative-subsample',action='store_true',help='Explicitly allow only negative positions with zero truncated index')
    args = parser.parse_args()
    checks = []
    for row in json.loads(args.probe.read_text(encoding='utf-8'))['rows']:
        pairs = struct.unpack('<' + 'd' * (row['domainSize']*2), bytes.fromhex(row['pairsHex']))
        error = abs(evaluate(pairs[1::2], row['position'],allow_negative_subsample=args.negative_subsample) - row['value'])
        checks.append({'position': row['position'], 'domainSize': row['domainSize'],
                       'maxError': error, 'passed': error <= 1e-14})
    report = {'cameraAccess': False, 'checks': checks, 'passed': sum(check['passed'] for check in checks)}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(checks), 'passed': report['passed'], 'maxError': max(check['maxError'] for check in checks)}))
    if not checks or report['passed']!=len(checks):raise SystemExit(1)


if __name__ == '__main__': main()
