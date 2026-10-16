"""Canon-only scratch serialization of alternate PF3 banks; no camera transport."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .compiler_regression import cipher_tables, decode
from .high_bank_research import byte_difference
from .legacy_source_inventory import inspect_source
from .pf3_field_experiments import compile_stock
from .pf3_research import parse_records, probe


def record_fingerprints(raw, keys):
    size = struct.unpack_from('>I', raw, 8)[0]
    records, tail = parse_records(decode(raw[12:12 + size], keys, 12), allow_high_bit_records=True)
    if tail or not records or records[-1]['id'] != '0xffff':
        raise ValueError('Incomplete serialized record list')
    return {row['id']: dict(size=row['size'], type=row['type'],
                           sha256=hashlib.sha256(row['data']).hexdigest())
            for row in records if int(row['id'], 16) < 0xfffe}, records


def compare_records(before, after):
    return dict(removed=sorted(before.keys() - after.keys()),
                added=sorted(after.keys() - before.keys()),
                changed=sorted(key for key in before.keys() & after.keys() if before[key] != after[key]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append', required=True)
    parser.add_argument('--agent', type=Path, required=True, help='Existing stock compiler laboratory agent')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--donor', type=Path, help='Compare serialized single-grid replacement instead of bank variants')
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    inputs = {p.resolve(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in args.source + [args.dll, args.descriptor, args.agent] + ([args.donor] if args.donor else [])}
    args.output.mkdir(exist_ok=False, parents=True)
    import frida
    device = frida.get_local_device()
    descriptor = args.descriptor.read_bytes()
    report = dict(cameraAccess=False, compilerPatched=False, writesScratchOnly=True,
                  inputHashes={str(p): h for p, h in inputs.items()}, rows=[])
    try:
        donor_grids = {}
        if args.donor:
            donor_probe = probe(device, args.dll.resolve(), args.donor.resolve(), [0x40001070, 0x40001071])
            for identifier in (0x40001070, 0x40001071):
                value = bytes.fromhex(donor_probe['properties'][f'0x{identifier:08x}']['dataHex'])
                if len(value) != 215628 or struct.unpack_from('<3H', value) != (12, 3, 33):
                    raise ValueError('Unexpected donor grid')
                donor_grids[identifier] = value
        for source in args.source:
            raw = source.read_bytes()
            source_inventory = inspect_source(raw, keys)
            if not source_inventory['validated']:
                raise ValueError('Require checksum-verified source')
            before, records = record_fingerprints(raw, keys)
            if not source_inventory['highBitRecords']:
                raise ValueError('Require source with alternate bank')
            all_properties = [0x40000000 | int(row['id'], 16) for row in records
                              if int(row['id'], 16) < 0xfffe and row['size'] > 0]
            source_probe = probe(device, args.dll.resolve(), source.resolve(), [0x40001032, 0x40009032])
            saturation = bytes.fromhex(source_probe['properties']['0x40001032']['dataHex'])
            baselines = {}
            for model, identifier in [('M50', 1042), ('R8', 0x80000487)]:
                result, payload = compile_stock(device, args.dll.resolve(), args.agent.resolve(),
                                                source.resolve(), identifier, descriptor)
                baselines[model] = payload
            variants = ('copy_all', 'grid1070', 'grid1071') if args.donor else ('copy_all', 'omit_high_bank', 'mutate_high_saturation')
            for variant in variants:
                row = dict(sourceName=source.name, variant=variant, sourceIntegrity=source_inventory)
                target = args.output / (source.stem + '_' + variant + '.pf3')
                properties = all_properties if variant != 'omit_high_bank' else [p for p in all_properties if not p & 0x8000]
                mutation = 0x40009032 if variant == 'mutate_high_saturation' else 0x40001032
                data = struct.pack('<I', 2) if variant == 'mutate_high_saturation' else saturation
                if variant in ('grid1070', 'grid1071'):
                    mutation = 0x40001070 if variant == 'grid1070' else 0x40001071
                    data = donor_grids[mutation]
                try:
                    result = probe(device, args.dll.resolve(), source.resolve(), [0x40001032, 0x40009032],
                                   clone=dict(path=target.resolve(), properties=properties, property=mutation, data=data))
                    output_raw = target.read_bytes()
                    after, _ = record_fingerprints(output_raw, keys)
                    row.update(serialized=True, targetIntegrity=inspect_source(output_raw, keys),
                               recordComparison=compare_records(before, after), targetRecords=after,
                               sourceRecords=before, outputSha256=hashlib.sha256(output_raw).hexdigest(), compiles=[])
                    for model, identifier in [('M50', 1042), ('R8', 0x80000487)]:
                        compiled, payload = compile_stock(device, args.dll.resolve(), args.agent.resolve(),
                                                          target.resolve(), identifier, descriptor)
                        row['compiles'].append(dict(model=model, native=compiled,
                                                     differenceFromSource=byte_difference(baselines[model], payload)))
                except Exception as error:
                    row.update(error=str(error))
                report['rows'].append(row)
                (args.output / 'ROUNDTRIP_RESULTS.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                print(source.name, variant, row.get('recordComparison'), row.get('error'), flush=True)
    finally:
        changed = [str(p) for p, h in inputs.items() if hashlib.sha256(p.read_bytes()).hexdigest() != h]
        report['changedInputs'] = changed
        (args.output / 'ROUNDTRIP_RESULTS.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        if changed:
            raise RuntimeError('Original input changed')


if __name__ == '__main__':
    main()
