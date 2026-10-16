"""Canon-serialized private omission experiment for the Basic aggregate defaults."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records, probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--bases', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-editor-mapping', action='store_true', help='Use the editor Basic writer and verify Canon serialized records in scratch exports')
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    import frida
    device = frida.get_local_device()
    args.output.mkdir(parents=True, exist_ok=True)
    report = dict(cameraAccess=False, compilerPatched=False, writesOriginals=False, rows=[])
    for source in sorted(args.bases.glob('BASE_*_RP.pf3')):
        raw = source.read_bytes()
        records, tail = parse_records(decode(raw[12:], keys, 12))
        if tail or not records or records[-1]['id'] != '0xffff':
            raise ValueError('Incomplete source PF3')
        fields = {int(record['id'], 16):record['data'] for record in records}
        properties = [0x40000000 | identifier for identifier in fields
                      if identifier < 0xfffe and (args.verify_editor_mapping or identifier not in range(0x1030,0x1036))]
        suffix = '_EDITOR_EXPORT' if args.verify_editor_mapping else '_OMIT_BASIC'
        output = (args.output / (source.stem+suffix+'.pf3')).resolve()
        if output.exists() or output == source.resolve():
            raise ValueError('Refusing to overwrite a research fixture')
        mutation_id, mutation_data = 0x40001002, fields[0x1002]
        if args.verify_editor_mapping:
            from canon_engine import modify_basic_0115
            mutation_id = 0x115
            mutation_data = modify_basic_0115(bytes(32), -2, 2, -1, True, 5, 2, 3)
        result = probe(device, args.dll.resolve(), source.resolve(), [0x115],
                       dict(path=output, properties=properties, property=mutation_id, data=mutation_data))
        response = result['properties']['0x00000115']
        if response.get('rcGet') != 0 or response.get('length') != 32:
            raise ValueError('Basic aggregate default read failed')
        omitted, tail = parse_records(decode(output.read_bytes()[12:], keys, 12))
        present = {int(r['id'],16):r['data'] for r in omitted}
        changed = [identifier for identifier in fields if identifier < 0xfffe
                   and identifier not in range(0x1030,0x1036)
                   and present.get(identifier) != fields[identifier]]
        if tail or changed:
            raise ValueError('Omission serialization did not preserve all unrelated fields')
        if args.verify_editor_mapping:
            expected = {0x1030:5,0x1031:-2,0x1032:2,0x1033:-1,0x1034:2,0x1035:3}
            actual = {identifier:struct.unpack('>i',present[identifier])[0] for identifier in expected}
            if actual != expected or bytes.fromhex(response['dataHex']) != mutation_data:
                raise ValueError('Editor controls did not serialize to the verified Canon field mapping')
        elif any(identifier in present for identifier in range(0x1030,0x1036)):
            raise ValueError('Omitted scalar record remains present')
        row = dict(source=str(source.resolve()), sourceSha256=hashlib.sha256(raw).hexdigest(),
                   baseSelector=fields[0x1009].hex(), unrelatedFieldsPreserved=True,
                   scalarRecordsAbsent=not args.verify_editor_mapping,
                   editorMappingVerified=args.verify_editor_mapping,
                   scratchExport=str(output),
                   aggregateSignedWords=list(struct.unpack('<8i',bytes.fromhex(response['dataHex']))))
        report['rows'].append(row)
        (args.output/'BASIC_DEFAULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(source.stem,row['aggregateSignedWords'],flush=True)


if __name__ == '__main__':
    main()
