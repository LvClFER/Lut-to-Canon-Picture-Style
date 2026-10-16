"""Verify private scalar transport evidence, not preview or camera support."""
import hashlib
import json
from pathlib import Path


def verify(report):
    if any(report.get(key) is not False for key in ('cameraAccess','compilerPatched','writesOriginals')):
        raise ValueError('Require isolated unpatched evidence')
    baseline = report['baseline']
    if any(baseline.get(key) != 0 for key in ('rcCreate','rcId','rcDescriptor','rcSize','rcGet')):
        raise ValueError('Baseline native API failure')
    rows = report['experiments']
    if len(rows) != 7:
        raise ValueError('Require complete zero-baseline sweep 1..7')
    identifiers = {int(row['mutationProperty'],16) for row in rows}
    if len(identifiers) != 1 or not identifiers <= {0x40001034,0x40001035}:
        raise ValueError('Mixed or unsupported scalar fields')
    identifier = identifiers.pop()
    values = [int(row['name'].rsplit('VALUE',1)[1]) for row in rows]
    if sorted(values) != list(range(1,8)):
        raise ValueError('Missing or duplicate scalar values')
    offset = None
    for row,value in zip(rows,values):
        if not row.get('serializedMutationExact') or row['changedSerializedFields'] != [f'0x{identifier & 0xffff:04x}']:
            raise ValueError('Unverified single-field serialization')
        if any(row.get(key) != 0 for key in ('rcCreate','rcId','rcDescriptor','rcSize','rcGet')):
            raise ValueError('Native API failure')
        data = Path(row['privateResearchPayload']).read_bytes()
        if len(data) != baseline['payloadSize'] or hashlib.sha256(data).hexdigest() != row['payloadSha256']:
            raise ValueError('Payload size/hash mismatch')
        if value == 1:
            if row['changedByteCount'] != 0 or row['payloadSha256'] != baseline['payloadSha256']:
                raise ValueError('Zero-to-one equivalence not proven')
        else:
            if row['changedByteCount'] != 1 or len(row['changedOffsets']) != 1:
                raise ValueError('Unexpected non-scalar changes')
            current = row['changedOffsets'][0]
            if offset is not None and offset != current:
                raise ValueError('Inconsistent output offset')
            offset = current
            if data[offset] != min(value,5):
                raise ValueError('Clamp hypothesis contradicted')
    # Independently compare all bytes, not only the report's difference claims.
    base = Path(rows[values.index(1)]['privateResearchPayload']).read_bytes()
    for row,value in zip(rows,values):
        data = Path(row['privateResearchPayload']).read_bytes()
        expected = bytearray(base)
        expected[offset] = min(value,5)
        if data != expected:
            raise ValueError('Opaque bytes were changed')
    return dict(property=hex(identifier),cameraId=report['cameraId'],payloadSize=len(base),
                scalarOffset=offset,clampMinimum=1,clampMaximum=5,allSevenExact=True,
                physicalValidation=False,previewValidation=False)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(json.loads(args.report.read_text(encoding='utf-8'))),indent=2))
