"""Extract the observed record schema from one hash-verified Canon DLL, read-only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

DLL_HASH = '7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0'
SCHEMA_RVA = 0xcf5e0
SCHEMA_BYTES = 0x258


def parse_schema(data):
    if len(data) != SCHEMA_BYTES:
        raise ValueError('Expected the observed 50-record schema')
    rows = []
    seen = set()
    for offset in range(0, len(data), 12):
        identifier, kind, size = struct.unpack_from('<3I', data, offset)
        if identifier in seen or kind not in (2, 3, 4, 0xffff):
            raise ValueError('Unexpected schema record')
        seen.add(identifier)
        width = {3: 2, 4: 4}.get(kind)
        if width and size % width:
            raise ValueError('Misaligned fixed-size record')
        policy = 'variable' if size == 0 else ('bounded' if kind == 2 else 'exact')
        rows.append(dict(property=hex(identifier), storedType=kind,
                         sizeConstraint=size, inputSizePolicy=policy,
                         semanticMeaning='not-established-by-schema'))
    return rows


def extract(dll):
    data = dll.read_bytes()
    if hashlib.sha256(data).hexdigest() != DLL_HASH:
        raise ValueError('Unknown DLL; fixed schema RVA must not be assumed')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE signature')
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    optional = struct.unpack_from('<H', data, pe + 20)[0]
    start = pe + 24 + optional
    for index in range(sections):
        header = start + index * 40
        _, rva, raw_size, raw_offset = struct.unpack_from('<4I', data, header + 8)
        if rva <= SCHEMA_RVA and SCHEMA_RVA + SCHEMA_BYTES <= rva + raw_size:
            offset = raw_offset + SCHEMA_RVA - rva
            rows = parse_schema(data[offset:offset + SCHEMA_BYTES])
            return dict(dllSha256=DLL_HASH, cameraAccess=False, dllModified=False,
                        schemaRva=hex(SCHEMA_RVA), records=rows)
    raise ValueError('Schema is not within a file-backed section')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = extract(args.dll)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print('Observed record definitions:', len(report['records']))


if __name__ == '__main__':
    main()
