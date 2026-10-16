"""Private Canon-serialized derived-record seeds: no camera access or DLL patches."""
import argparse
import hashlib
import json
from pathlib import Path
from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records, probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    original = args.source.read_bytes()
    records, tail = parse_records(decode(original[12:],keys,12))
    if tail or not records or records[-1]['id'] != '0xffff':
        raise ValueError('Incomplete source')
    fields = {int(record['id'],16):(record['type'],record['data']) for record in records}
    if 0x1022 in fields or 0x102a in fields:
        raise ValueError('Experiment requires absent derived source records')
    properties = [0x40000000|identifier for identifier in fields if identifier < 0xfffe]
    args.output.mkdir(parents=True,exist_ok=True)
    import frida
    device = frida.get_local_device()
    report = dict(cameraAccess=False, compilerPatched=False,
                  purpose='Test node materialization, not proposed camera payload',rows=[])
    for value in (0,255):
        target = (args.output/f'SEED_{value:02X}.pf3').resolve()
        if target.exists():
            raise ValueError('Refusing to overwrite scratch output')
        seed = bytes([value])*4096
        probe(device,args.dll.resolve(),args.source.resolve(),[0x40001022,0x4000102a],
              dict(path=target,properties=properties,property=0x40001022,data=seed,
                   additionalMutations=[dict(property=0x4000102a,dataHex=seed.hex())]))
        added, tail = parse_records(decode(target.read_bytes()[12:],keys,12))
        present = {int(record['id'],16):(record['type'],record['data']) for record in added}
        changed = [identifier for identifier,item in fields.items()
                   if identifier < 0xfffe and present.get(identifier) != item]
        new = set(present)-set(fields)
        if tail or changed or new not in (set(), {0x1022,0x102a}):
            raise ValueError('Seed serialization changed unrelated records')
        if any(present[identifier] != (4,seed) for identifier in new):
            raise ValueError('Seed bytes/type differ from request')
        report['rows'].append(dict(sourceSha256=hashlib.sha256(original).hexdigest(),
            scratch=str(target),scratchSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            seedByte=value,unrelatedRecordsPreserved=True,
            derivedRecordsRetained=bool(new),
            classification='seed-retained' if new else 'Canon-serializer-omits-derived-records'))
    if args.source.read_bytes() != original:
        raise ValueError('Original fixture changed')
    with (args.output/'SEED_SERIALIZATION.json').open('x',encoding='utf-8') as output:
        json.dump(report,output,indent=2)
    print('Two Canon-serialized scratch seeds verified; no camera compatibility claimed')


if __name__ == '__main__':
    main()
