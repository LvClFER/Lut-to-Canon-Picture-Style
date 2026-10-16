"""Inventory serialized legacy records across private PF2/PF3 fixtures, read-only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .compiler_regression import cipher_tables, decode
from .pf3_research import parse_records, checksum_observations


def inspect_source(raw, keys):
    if len(raw) < 12 or raw[4:8] != b'PSP\0':
        return dict(validated=False, reason='unrecognized-envelope')
    body_size = struct.unpack_from('>I', raw, 8)[0]
    trailer_size=len(raw)-12-body_size
    observed_trailer=raw[:4]==bytes.fromhex('00002001') and trailer_size==4
    if trailer_size!=0 and not observed_trailer:
        return dict(validated=False, reason='body-size-mismatch')
    decoded=decode(raw[12:],keys,12)
    trailer=decoded[body_size:]
    if observed_trailer and trailer!=bytes(4):
        return dict(validated=False,reason='unrecognized-pf2-2001-trailer')
    plaintext=decoded[:body_size]
    records, tail = parse_records(plaintext,allow_high_bit_records=True)
    checksum = checksum_observations(plaintext, records)
    terminated = bool(records and records[-1]['id'] == '0xffff' and not tail)
    checksum_valid = 'sum_bytes_before_checksum_record' in checksum.get('matchingCandidates', [])
    by_id = {r['id']: r for r in records}
    pairs = []
    for record in records:
        value = int(record['id'], 16)
        if not 0x9000 <= value <= 0x90ff:
            continue
        counterpart = by_id.get(hex(value & ~0x8000))
        pairs.append(dict(id=record['id'], counterpartId=hex(value & ~0x8000),
                          counterpartPresent=counterpart is not None,
                          sameType=counterpart is not None and record['type']==counterpart['type'],
                          sameSize=counterpart is not None and record['size']==counterpart['size'],
                          sameData=counterpart is not None and record['data']==counterpart['data'],
                          prefixHex=record['data'][:16].hex(),
                          counterpartPrefixHex=counterpart['data'][:16].hex() if counterpart else None))
    return dict(validated=terminated and checksum_valid, structurallyDecoded=terminated,
                highBitCounterpartComparisons=pairs,
                envelopeVersionHex=raw[:4].hex(), terminated=terminated,
                envelopeTrailerSize=trailer_size,envelopeTrailerDecodedHex=trailer.hex(),
                checksumPresent=checksum.get('present',False),
                checksumValid=checksum_valid, tailSize=len(tail), recordCount=len(records),
                recordIds=[r['id'] for r in records],
                legacyRecords=[dict(id=r['id'], size=r['size'], type=r['type'],
                                    sha256=hashlib.sha256(r['data']).hexdigest(),
                                    prefixHex=r['data'][:16].hex())
                               for r in records if r['id'] in ('0x1004','0x1005','0x1007')],
                highBitRecords=[dict(id=r['id'],counterpartId=hex(int(r['id'],16)&~0x8000),
                                     size=r['size'],sha256=hashlib.sha256(r['data']).hexdigest())
                                for r in records if 0x9000<=int(r['id'],16)<=0x90ff])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('dll', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    keys = cipher_tables(args.dll)
    unique = {}
    total = 0
    for path in sorted(args.root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.pf2','.pf3'):
            continue
        total += 1
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in unique:
            unique[digest] = dict(sourceSha256=digest, size=len(raw),
                                  **inspect_source(raw, keys), paths=[])
        unique[digest]['paths'].append(str(path.resolve()))
    rows = list(unique.values())
    report = dict(cameraAccess=False, sourceFilesModified=False, fileCount=total,
                  uniqueCount=len(rows), checksumVerifiedCount=sum(r['validated'] for r in rows),
                  structurallyDecodedCount=sum(r.get('structurallyDecoded',False) for r in rows),
                  decodedWithoutChecksumCount=sum(r.get('structurallyDecoded',False) and
                                                   not r.get('checksumPresent',False) for r in rows),
                  sourcesWithSerialized1007=sum(any(p['id']=='0x1007' for p in r.get('legacyRecords',[]))
                                               for r in rows), rows=rows)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print({k:v for k,v in report.items() if k != 'rows'})
    for row in rows:
        if row.get('legacyRecords') or not row.get('structurallyDecoded',False):
            print(row['paths'][0], row.get('legacyRecords',[]), row.get('reason',''))


if __name__ == '__main__':
    main()
