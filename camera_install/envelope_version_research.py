"""Private header-only diagnostics; not a PF2/PF3 format conversion."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .compiler_regression import cipher_tables
from .legacy_source_inventory import inspect_source


def header_variant(raw: bytes, version: int) -> bytes:
    if len(raw) < 12 or raw[4:8] != b'PSP\0':
        raise ValueError('Require observed PSP envelope')
    if type(version) is not int or version not in (0x2000, 0x2001, 0x3000, 0x4000):
        raise ValueError('Only bounded observed version diagnostics')
    return struct.pack('>I', version) + raw[4:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', type=lambda value: int(value, 0), action='append', required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    info = inspect_source(raw, cipher_tables(args.dll))
    if not info['validated']:
        raise ValueError('Require structurally decoded, checksum-verified source')
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for version in args.version:
        variant = header_variant(raw, version)
        path = args.output / f'DIAGNOSTIC_HEADER_{version:04x}.pf3'
        with path.open('xb') as output:
            output.write(variant)
        rows.append(dict(path=str(path.resolve()), version=hex(version),
                         sha256=hashlib.sha256(variant).hexdigest(),
                         bodyUnchanged=variant[4:] == raw[4:]))
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Original source changed')
    report = dict(cameraAccess=False, sourceFilesModified=False, sourceSha256=digest,
                  scope='Header-only diagnostics, never installable format conversion', rows=rows)
    with (args.output / 'DIAGNOSTIC_MANIFEST.json').open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)


if __name__ == '__main__':
    main()
