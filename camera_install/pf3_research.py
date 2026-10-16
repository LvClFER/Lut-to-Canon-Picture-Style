"""Read-only PF3 property inventory and observed DLL decoding, never a serializer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import zlib
from pathlib import Path

from .compiler_regression import cipher_tables, decode
from .virtual_compatibility import LOAD_COMPILER


def parse_records(plaintext: bytes, allow_high_bit_records=False):
    """Observed big-endian ID/type/length records; preserve any unexplained tail."""
    records = []
    offset = 0
    while offset + 8 <= len(plaintext):
        identifier, kind, size = struct.unpack_from(">HHI", plaintext, offset)
        if (not (0x1000 <= identifier <= 0x10FF or
                 allow_high_bit_records and 0x9000 <= identifier <= 0x90FF or
                 identifier in (0xFFFE, 0xFFFF)) or
                size > len(plaintext) - offset - 8):
            break
        data = plaintext[offset + 8:offset + 8 + size]
        record = {"id": f"0x{identifier:04x}", "type": kind, "size": size,
                  "decodedHeaderOffset": offset, "decodedDataOffset": offset + 8,
                  "fileHeaderOffset": offset + 12, "fileDataOffset": offset + 20,
                  "data": data}
        records.append(record)
        offset += 8 + size
        if identifier == 0xFFFF:
            break
    return records, plaintext[offset:]


def checksum_observations(plaintext, records):
    checksum = next((record for record in records if record["id"] == "0xfffe" and record["size"] == 4), None)
    if checksum is None:
        return {"present": False}
    stored = struct.unpack(">I", checksum["data"])[0]
    prefix = plaintext[:checksum["decodedHeaderOffset"]]
    properties_only = b"".join(record["data"] for record in records if int(record["id"], 16) < 0xFFFE)
    candidates = {"sum_bytes_before_checksum_record": sum(prefix) & 0xFFFFFFFF,
                  "sum_property_data_bytes": sum(properties_only) & 0xFFFFFFFF,
                  "crc32_before_checksum_record": zlib.crc32(prefix),
                  "adler32_before_checksum_record": zlib.adler32(prefix)}
    return {"present": True, "storedBigEndian": stored, "candidateValues": candidates,
            "matchingCandidates": [name for name, value in candidates.items() if value == stored]}


def byte_representations(data: bytes):
    yield "identical", data
    for width in (2, 4):
        if len(data) % width == 0:
            yield f"swap{width * 8}", b"".join(data[i:i + width][::-1] for i in range(0, len(data), width))


def describe(data: bytes):
    item = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "prefixHex": data[:32].hex()}
    if len(data) <= 64:
        item["rawHex"] = data.hex()
    if len(data) == 215628 and struct.unpack_from("<3H", data) == (12, 3, 33):
        values = struct.unpack_from("<107811H", data, 6)
        item["denseGrid"] = {"bits": 12, "channels": 3, "nodesPerAxis": 33,
                             "samples": len(values), "min": min(values), "max": max(values),
                             "within12Bit": max(values) <= 4095}
    return item


def probe(device, dll, path, properties, clone=None):
    host = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Sleep -Seconds 3600"])
    session = None
    scripts = []
    try:
        session = device.attach(pid)
        loader = session.create_script(LOAD_COMPILER); scripts.append(loader); loader.load()
        device.resume(pid); loader.exports_sync.load(str(dll))
        script = session.create_script(Path(__file__).with_name("pf3_research_agent.js").read_text(encoding="utf-8"))
        scripts.append(script); script.load()
        if clone is not None:
            script.exports_sync.clone(str(path), str(clone["path"]), clone["properties"],
                                      clone["property"], clone["data"].hex(), clone.get('additionalMutations', []))
            path = clone["path"]
        return script.exports_sync.inspect(str(path), properties, 0x2DB0)
    finally:
        for script in reversed(scripts):
            try: script.unload()
            except Exception: pass
        if session is not None:
            try: session.detach()
            except Exception: pass
        try: device.kill(pid)
        except Exception: pass


def inspect_result(result, raw, keys, output, stem):
    captures = []
    plaintexts = []
    parsed = []
    for index, call in enumerate(result["cipherCalls"]):
        before, after = bytes.fromhex(call["beforeHex"]), bytes.fromhex(call["afterHex"])
        exact = decode(before, keys, call["seed"]) == after
        if not exact:
            raise ValueError("Observed Canon cipher differs from independent decoder")
        capture_path = output / f"{stem}_DECODED_{index}.bin"
        capture_path.write_bytes(after)
        plaintexts.append(after)
        records, tail = parse_records(after)
        checksum = checksum_observations(after, records)
        if raw.find(before) == 12:
            parsed = records
        captures.append({"seed": call["seed"], "size": len(after), "independentDecodeExact": exact,
                         "independentReencodeExact": decode(after, keys, call["seed"]) == before,
                         "encodedFileOffset": raw.find(before), "decodedSha256": hashlib.sha256(after).hexdigest(),
                         "privateResearchCapture": str(capture_path.resolve()),
                         "parsedRecordCount": len(records), "unparsedTailSize": len(tail),
                         "unparsedTailHex": tail[:64].hex(), "checksumAnalysis": checksum})
    properties = {}
    for prop, response in result["properties"].items():
        item = {key: value for key, value in response.items() if key != "dataHex"}
        if "dataHex" in response:
            data = bytes.fromhex(response["dataHex"])
            item.update(describe(data))
            item["decodedOccurrences"] = [{"capture": index, "offset": block.find(data)}
                for index, block in enumerate(plaintexts) if len(data) >= 8 and block.find(data) >= 0]
        properties[prop] = item
    file_records = []
    for record in parsed:
        data = record.pop("data")
        record.update(describe(data))
        property_key = f"0x{0x40000000 | int(record['id'], 16):08x}"
        response = result["properties"].get(property_key, {})
        if "dataHex" in response:
            api_data = bytes.fromhex(response["dataHex"])
            record["directPropertyApi"] = property_key
            record["apiByteRepresentationMatches"] = [label for label, candidate in byte_representations(data)
                                                        if candidate == api_data]
        file_records.append(record)
    return {"fileSize": len(raw), "fileSha256": hashlib.sha256(raw).hexdigest(),
            "declaredBodySizeBigEndian": struct.unpack_from(">I", raw, 8)[0] if len(raw) >= 12 else None,
            "declaredBodySizeMatches": len(raw) >= 12 and struct.unpack_from(">I", raw, 8)[0] == len(raw) - 12,
            "headerHex": raw[:12].hex(), "cipherCalls": captures, "properties": properties,
            "fileRecords": file_records, "converterDispatchTargets": result.get("converterDispatchTargets", []),
            "referenceDispatchTargets": result.get('referenceDispatchTargets', []),
            "parserDispatchTargets":result.get('parserDispatchTargets', []),
            "contentDispatchTargets":result.get('contentDispatchTargets', [])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--basic-experiments", action="store_true",
                        help="Create private scratch PF3s to test six scalar controls and the PF3-only 0x115 aggregate")
    args = parser.parse_args()
    keys = cipher_tables(args.dll)  # Fails closed for an unknown DLL before fixed-RVA observation.
    import frida
    device = frida.get_local_device()
    properties = [0x114, 0x115] + list(range(0x40001000, 0x40001081))
    properties += list(range(0x1000, 0x1081)) + list(range(0x1F00, 0x1F05))
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"readOnly": True, "cameraAccess": False, "compilerPatched": False,
              "writesOriginals": False, "writesScratch": args.basic_experiments,
              "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(), "files": []}
    files = sorted(args.vectors.glob("*.pf3"))[:args.limit]
    if not files: parser.error("No PF3 vectors found")
    for path in files:
        result = probe(device, args.dll.resolve(), path.resolve(), properties)
        item = inspect_result(result, path.read_bytes(), keys, args.output, path.stem)
        item["source"] = str(path.resolve()); report["files"].append(item)
        available = sum(prop.get("rcGet") == 0 for prop in item["properties"].values())
        print(f"{path.name}: {available} readable properties; {len(item['cipherCalls'])} decoding calls", flush=True)
        (args.output / "PF3_INVENTORY.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.basic_experiments:
        baseline = report["files"][0]
        copy_properties = [0x40000000 | int(record["id"], 16) for record in baseline["fileRecords"]
                           if int(record["id"], 16) < 0xFFFE]
        experiments = [(0x40001030, struct.pack("<i", -2)), (0x40001031, struct.pack("<i", 3)),
                       (0x40001032, struct.pack("<i", 2)), (0x40001033, struct.pack("<i", -1)),
                       (0x40001034, struct.pack("<i", 2)), (0x40001035, struct.pack("<i", 3)),
                       (0x115, struct.pack("<8i", 3, -2, 2, -1, 0, 0, 2, 3))]
        report["basicControlExperiments"] = []
        for prop, data in experiments:
            output_path = (args.output / f"BASIC_{prop:08X}.pf3").resolve()
            result = probe(device, args.dll.resolve(), files[0].resolve(), properties,
                           {"path": output_path, "properties": copy_properties, "property": prop, "data": data})
            item = inspect_result(result, output_path.read_bytes(), keys, args.output, output_path.stem)
            item.update(source=str(output_path), mutationProperty=f"0x{prop:08x}", mutationHex=data.hex())
            item["aggregateSignedValues"] = list(struct.unpack("<8i", bytes.fromhex(item["properties"]["0x00000115"]["rawHex"])))
            item["scalarSignedValues"] = {record["id"]: struct.unpack(">i", bytes.fromhex(record["rawHex"]))[0]
                for record in item["fileRecords"] if int(record["id"], 16) in range(0x1030, 0x1036)}
            report["basicControlExperiments"].append(item)
            print(f"Scratch {prop:08X}: {item['aggregateSignedValues']}", flush=True)
            (args.output / "PF3_INVENTORY.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
