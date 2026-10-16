"""Read-only map of the observed base-style88 ID-set rejection gate."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .compiler_regression import cipher_tables
from .descriptor_policy_research import DIRECT_SMALL, read_rva, policy_ids


def require_base88(row):
    base = row.get('before', {}).get('114', {})
    if base.get('rcGet') != 0 or base.get('length') != 4 or base.get('prefixHex') != '88000000':
        raise ValueError('Require observed base-style88 before ID setting')


def rejection_ids(raw, reader=read_rva):
    rejected = set(DIRECT_SMALL)
    for first, count, index_rva, jump_rva in (
        (0x80000215, 32, 0x574f0, 0x574e8),
        (0x80000250, 55, 0x57518, 0x57510),
        (0x80000288, 253, 0x57558, 0x57550)):
        indices = reader(raw, index_rva, count)
        targets = struct.unpack('<2I', reader(raw, jump_rva, 8))
        if set(targets) != {0x100574c4, 0x100574c9} or any(index > 1 for index in indices):
            raise ValueError('Unknown Fine Detail rejection switch geometry')
        rejected.update(first + i for i, index in enumerate(indices) if targets[index] == 0x100574c4)
    return rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cipher_tables(args.dll)
    rejected = rejection_ids(args.dll.read_bytes())
    source = json.loads(args.matrix.read_text(encoding='utf-8'))
    if any(source.get(key) is not False for key in ('cameraAccess', 'compilerPatched', 'sourceFilesModified')):
        raise ValueError('Require unchanged offline evidence')
    rows = []
    for row in source['rows']:
        require_base88(row)
        expected = 7 if row['cameraId'] in rejected else 0
        rows.append(dict(model=row['model'], cameraId=row['cameraId'], mutation=row['mutation'],
                         predictedRcId=expected, observedRcId=row.get('rcId'),
                         agrees=row.get('rcId') == expected))
    report = dict(cameraAccess=False, dllModified=False, cameraCompatibility='not-tested',
                  scope='Base style88 ID-set gate only; no format or installation validation',
                  rejectedIds=sorted(rejected), rows=rows,
                  compactPrefixPolicyIdsEqual=(rejected == policy_ids(args.dll.read_bytes(), read_rva)),
                  dllSha256=hashlib.sha256(args.dll.read_bytes()).hexdigest())
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print('ID gate agreements:', sum(row['agrees'] for row in rows), '/', len(rows))


if __name__ == '__main__':
    main()
