"""Compare private decoded PF3 fixtures; never write or compile a PF3."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from .pf3_research import parse_records


def nested_records(data):
    """Bounded structural hypothesis: arbitrary IDs, same BE TLV envelope."""
    result, offset = [], 0
    while offset + 8 <= len(data):
        identifier, kind, length = struct.unpack_from(">HHI", data, offset)
        if length > len(data) - offset - 8:
            break
        payload = data[offset + 8:offset + 8 + length]
        item = {"id": hex(identifier), "type": kind, "size": length,
                "offset": offset, "sha256": hashlib.sha256(payload).hexdigest()}
        if kind == 4 and length % 4 == 0:
            item["unsigned32BigEndian"] = list(struct.unpack(f">{length // 4}I", payload))
            values = item["unsigned32BigEndian"]
            # Observed layout only: two header words followed by six 18-word groups.
            if identifier == 0x10 and len(values) == 110 and values[:2] == [6, 6]:
                groups = [values[2 + i * 18:2 + (i + 1) * 18] for i in range(6)]
                def signed(value):
                    return value if value < 0x80000000 else value - 0x100000000
                item["sixGroupHypothesis"] = {"groupWords": 18, "groups": groups,
                    "candidateSigned16_16Fields": [[signed(value) / 65536
                        for value in group[3:11]] for group in groups],
                    "fieldMeaningValidated": False}
        result.append(item)
        offset += 8 + length
        if identifier == 0xffff:
            break
    return {"records": result, "tailSize": len(data) - offset,
            "completeTerminatedStructure": bool(result) and result[-1]["id"] == "0xffff"
                and result[-1]["size"] == 0 and offset == len(data),
            "semanticsValidated": False}


def compare_files(paths):
    files, by_id = [], {}
    for path in paths:
        data = path.read_bytes()
        records, tail = parse_records(data)
        if tail or not records or records[-1]["id"] != "0xffff":
            raise ValueError(f"Not a complete decoded PF3 body: {path}")
        files.append({"source": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()})
        for record in records:
            by_id.setdefault(record["id"], []).append(record["data"])
    summaries = {}
    for identifier, values in by_id.items():
        item = {"observations": len(values), "uniquePayloads": len(set(values)),
                "sizes": sorted({len(value) for value in values}),
                "sha256": sorted({hashlib.sha256(value).hexdigest() for value in values})}
        if identifier == "0x1008":
            item["nestedStructureHypothesis"] = nested_records(values[0])
        if len(values[0]) <= 512 and len(values[0]) % 4 == 0:
            item["baselineUnsigned32BigEndian"] = list(struct.unpack(f">{len(values[0]) // 4}I", values[0]))
        summaries[identifier] = item
    return {"cameraAccess": False, "writesPf3": False, "files": files, "records": summaries,
            "warning": "Constancy across these LUT vectors does not establish a field's mathematical role."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decoded-folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.decoded_folder.glob("*_DECODED_0.bin"))
    if not paths:
        parser.error("No decoded fixtures found")
    report = compare_files(paths)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(paths), "varyingRecords":
        [key for key, value in report["records"].items() if value["uniquePayloads"] > 1]}))


if __name__ == "__main__":
    main()
