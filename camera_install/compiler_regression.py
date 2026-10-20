"""Offline table and transport regression using the production Frida agent."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

from .virtual_compatibility import LOAD_COMPILER
from .cipher_stream_reference import decode
from .full33_packing_reference import full33_planar


VECTORS = ("01_IDENTITY", "02_R_GAIN_075", "03_G_GAIN_075",
           "07_NODE_CENTER_R_MINUS", "12_AEROCHROME_REAL")


def summarize(rows):
    return {"cases": len(rows), "passed": sum(item["ok"] for item in rows),
            "failed": sum(not item["ok"] for item in rows),
            "transportPassed": sum(bool(item.get("transport", {}).get("stale", {}).get("staleBlocked")) for item in rows),
            "namePassed": sum(item.get("namePreserved", False) for item in rows),
            "numericSecondGridUnresolved": sum(item.get("tables", {}).get("allNumericTablesChecked") is False for item in rows)}


def recheck_historical_reference(report, reference):
    """Compare recorded compiler-output digests; never turn missing data into a pass."""
    for row in report["rows"]:
        tables = row.get("tables", {})
        if tables.get("method") != "independent-compact-grid-reference":
            continue
        checks = tables.get("exactTables", [])
        expected_hash = reference.get(row["vector"], {}).get("sha256")
        match = bool(expected_hash) and row.get("sha256") == expected_hash
        order = [1, 2] if match else None
        capture_path = row.get("privateResearchPayload")
        if capture_path and expected_hash:
            payload = Path(capture_path).read_bytes()
            if hashlib.sha256(payload).hexdigest() != row.get("sha256"):
                raise ValueError("Private research capture differs from recorded compiler output")
            order = ten_node_reference_order(payload, expected_hash)
        tables.update(allNumericTablesChecked=bool(checks) and all(checks),
                      historicalCompilerOutputExact=match, historicalReferenceBlockOrder=order,
                      outgoingBufferReordered=False)
        tables["ok"] = bool(checks) and (all(checks) or (checks[0] and order is not None))
        row["ok"] = (tables["ok"] and row.get("namePreserved", False) and
                     bool(row.get("transport", {}).get("stale", {}).get("staleBlocked")))
    report["summary"] = summarize(report["rows"])
    return report


def merge_reference_proof(report, proof):
    for field in ("descriptorSha256", "dllSha256", "productionAgentSha256"):
        if not report.get(field) or report[field] != proof.get(field):
            raise ValueError(f"Reference proof has a different {field}")
    indexed = {(item["cameraId"], item["vector"]): item for item in proof["rows"]}
    for row in report["rows"]:
        candidate = indexed.get((row["cameraId"], row["vector"]))
        if not candidate or not candidate.get("ok"):
            continue
        if row.get("sha256") != candidate.get("sha256") or not row.get("sha256"):
            raise ValueError("Reference proof describes different compiled bytes")
        if row.get("sourcePf3Sha256") != candidate.get("sourcePf3Sha256") or not row.get("sourcePf3Sha256"):
            raise ValueError("Reference proof describes a different PF3 source")
        if candidate.get("tables", {}).get("independentResearchOutputExact") is True:
            row["tables"] = dict(candidate["tables"])
            row["ok"] = bool(row.get("namePreserved") and
                             row.get("transport", {}).get("stale", {}).get("staleBlocked"))
    report["summary"] = summarize(report["rows"])
    return report


def ten_node_reference_order(payload: bytes, expected_digest: str):
    """Test reference equivalence only; never alter the outgoing Canon buffer."""
    if len(payload) != 16752 or not expected_digest:
        return None
    if hashlib.sha256(payload).hexdigest() == expected_digest:
        return [1, 2]
    alternate = payload[:368] + payload[8560:16752] + payload[368:8560]
    if hashlib.sha256(alternate).hexdigest() == expected_digest:
        return [2, 1]
    return None


def cipher_tables(dll: Path) -> tuple[bytes, bytes]:
    # Research-only decoder for the independently recorded x86 3.20.20.0
    # fixtures. It is never used to generate a camera payload.
    data = dll.read_bytes()
    if hashlib.sha256(data).hexdigest() != "7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0":
        raise ValueError("Research decoder supports only the recorded Canon 3.20.20.0 DLL; production signatures are separate")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Invalid PE DLL")
    sections, optional_size = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    for index in range(sections):
        offset = pe + 24 + optional_size + index * 40
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<4I", data, offset + 8)
        if rva <= 0xCE000 and 0xCE000 + 1025 <= rva + min(virtual_size, raw_size):
            start = raw_offset + 0xCE000 - rva
            return data[start:start + 512], data[start + 512:start + 1025]
    raise ValueError("Known research cipher tables are absent; do not assume this DLL layout")


def table_check(payload: bytes, metadata: dict, tables: dict, vector: str,
                fixtures: Path, keys: tuple[bytes, bytes]) -> dict:
    path = metadata["acceptanceHook"]["compilerPath"]
    size = len(payload)
    if path == "canon-full33-direct":
        expected = [full33_planar(bytes.fromhex(tables[prop])) for prop in ("table70", "table71")]
        exact = [payload[372 + i * len(block):372 + (i + 1) * len(block)] == block
                 for i, block in enumerate(expected)]
        return {"method": "independent-python-full33-planar", "exactTables": exact, "ok": all(exact)}
    if path == "canon-17-node":
        reference = (fixtures / f"R8_CANON_NATIVE_FIVE_BLOCK_{vector}_83076.bin").read_bytes()
        checks = []
        for index, offset in enumerate((372, 20024, 39676, 59328)):
            seed = 0xB8ED if index % 2 == 0 else 0x33137
            actual = decode(payload[offset:offset + 19652], keys, seed)
            expected = decode(reference[offset:offset + 19652], keys, seed)
            checks.append(actual == expected)
        if size == 83076:
            checks.append(decode(payload[78980:83076], keys) == decode(reference[78980:83076], keys))
        return {"method": "independent-archived-canon-grid-reference", "exactTables": checks, "ok": all(checks)}
    if path.startswith("validated-legacy-direct-"):
        aliases = {8528: "1D_Mark_III_8528", 16720: "450D_16720",
                   16744: "1300D_reference", 16752: "7D_Mark_II_direct_16752"}
        names = {"01_IDENTITY": "identity", "02_R_GAIN_075": "r_gain",
                 "03_G_GAIN_075": "g_gain", "07_NODE_CENTER_R_MINUS": "node",
                 "12_AEROCHROME_REAL": "aerochrome"}
        reference = (fixtures / "blocked_family_outputs" / f"{aliases[size]}_{names[vector]}_{size}.bin").read_bytes()
        count = 1 if size == 8528 else 2
        actual = payload[-count * 8192:]
        expected = reference[-count * 8192:]
        checks = [actual[i * 8192:(i + 1) * 8192] == expected[i * 8192:(i + 1) * 8192] for i in range(count)]
        return {"method": "independent-archived-legacy-table-reference", "exactTables": checks, "ok": all(checks)}
    if path == "canon-10-node":
        # Check each compact input independently. Locate it rather than assume
        # that a model uses the same ordering for its base and transformed grids.
        compact = [(fixtures / f"GRID33_{vector}_{prop}_{index}_4096.bin").read_bytes()
                   for prop, index in (("00001022", 0), ("0000102a", 1))]
        decoded = [decode(payload[start:start + 8192], keys, seed)
                   for start in (368, 8560) for seed in (0xB8ED, 0x33137)]
        found = [[block.find(expected) for block in decoded] for expected in compact]
        checks = [any(offset >= 0 for offset in row) for row in found]
        # The historical 10-node probe independently compiled both grids. Its
        # complete output digest is a stronger encoded-byte regression oracle
        # than assuming the R8 compact-property layout is also the second
        # 10-node grid. Keep that numerical limitation explicit in the report.
        historical = json.loads((fixtures / "RP_LEGACY_GATE_12_VECTOR_VALIDATION.json").read_text(encoding="utf-8"))
        reference_order = ten_node_reference_order(payload, historical[vector]["sha256"])
        historical_match = reference_order == [1, 2]
        return {"method": "independent-compact-grid-reference", "locations": found,
                "exactTables": checks, "allNumericTablesChecked": all(checks),
                "historicalCompilerOutputExact": historical_match,
                "historicalReferenceBlockOrder": reference_order,
                "outgoingBufferReordered": False,
                "ok": all(checks) or (checks[0] and reference_order is not None)}
    return {"method": "unmapped", "ok": False}


def run_case(device, host, dll, source, pf3, model, descriptor, slot, title=None, named_path=None):
    pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Sleep -Seconds 3600"])
    session = None
    scripts = []
    try:
        session = device.attach(pid)
        loader = session.create_script(LOAD_COMPILER)
        scripts.append(loader)
        loader.load()
        device.resume(pid)
        loader.exports_sync.load(str(dll))
        script = session.create_script(source)
        scripts.append(script)
        script_errors = []
        def on_message(message, data):
            if message.get("type") == "error":
                script_errors.append(message.get("stack", str(message)))
            elif message.get("payload", {}).get("type") == "test_stage":
                script_errors[:] = [message["payload"]["stage"]]
        script.on("message", on_message)
        script.load()
        if script_errors:
            raise RuntimeError("Test script initialization failed: " + "\n".join(script_errors))
        if title is not None:
            from canon_engine import PROPERTY_ORDER
            script.exports_sync.createnamedfixture(str(pf3), str(named_path), title, PROPERTY_ORDER)
            pf3 = named_path
        stage = "read serialized tables"
        try:
            stage = "transport interception"
            metadata, payload = script.exports_sync.testtransport(
                str(pf3), model.to_bytes(4, "little").hex(), descriptor.hex(), slot,
            )
            stage = "read serialized tables"
            tables = script.exports_sync.readtesttables(str(pf3), title is None and len(payload) == 431616)
            stage = "stale output rejection"
            stale = script.exports_sync.teststale(str(pf3), model.to_bytes(4, "little").hex(), descriptor.hex())
        except Exception as exc:
            raise RuntimeError(f"{stage}: {exc}; {'; '.join(script_errors)}") from exc
        metadata["stale"] = stale
        return dict(metadata), bytes(payload), dict(tables)
    finally:
        for script in reversed(scripts):
            try:
                script.unload()
            except Exception:
                pass
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
        try:
            device.kill(pid)
        except Exception:
            pass


def legacy_reference(device, host, dll, agent_path, pf3, model, descriptor):
    """Pre-existing independent research implementation, isolated from production hooks."""
    pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden",
                        "-Command", "Start-Sleep -Seconds 3600"])
    session = None
    script = None
    try:
        session = device.attach(pid)
        script = session.create_script(agent_path.read_text(encoding="utf-8"))
        script.load()
        device.resume(pid)
        script.exports_sync.loadcompiler(str(dll))
        result = script.exports_sync.compilelegacygate(str(pf3), model.to_bytes(4, "little").hex(),
                                                      descriptor.hex(), "replace-10-dense")
        if result.get("rcGet") != 0 or not result.get("outputHex"):
            raise ValueError("Independent research compiler did not produce a valid reference")
        return bytes.fromhex(result["outputHex"])
    finally:
        if script is not None:
            try:
                script.unload()
            except Exception:
                pass
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
        try:
            device.kill(pid)
        except Exception:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("matrix", "vectors", "fixtures", "descriptor", "dll", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--vector-limit", type=int)
    parser.add_argument("--title", help="Test Canon-serialized ASCII style name (max 31 characters)")
    parser.add_argument("--camera-id", type=int, action="append")
    parser.add_argument("--recheck-from", type=Path,
                        help="Re-evaluate recorded output hashes against historical independent 10-node compiler results")
    parser.add_argument("--capture-payloads", action="store_true",
                        help="Keep private research payloads beside the report; never bundle these in a public release")
    parser.add_argument("--legacy-probe", type=Path,
                        help="Pre-existing independent research agent for unresolved 10-node table references")
    parser.add_argument("--proof-report", type=Path, action="append",
                        help="Merge exact independently checked bytes only when model, source and compiler context match")
    args = parser.parse_args(argv)
    if args.recheck_from:
        report = json.loads(args.recheck_from.read_text(encoding="utf-8"))
        historical_path = args.fixtures / "RP_LEGACY_GATE_12_VECTOR_VALIDATION.json"
        reference = json.loads(historical_path.read_text(encoding="utf-8"))
        report = recheck_historical_reference(report, reference)
        for proof_path in args.proof_report or []:
            report = merge_reference_proof(report, json.loads(proof_path.read_text(encoding="utf-8")))
            report.setdefault("independentProofReports", []).append({
                "path": str(proof_path.resolve()), "sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest()})
        report["historicalReferenceSha256"] = hashlib.sha256(historical_path.read_bytes()).hexdigest()
        report["recheckedFromSha256"] = hashlib.sha256(args.recheck_from.read_bytes()).hexdigest()
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report["summary"]))
        return int(report["summary"]["failed"] > 0)
    if args.limit is not None and args.limit < 1 or args.vector_limit is not None and args.vector_limit < 1:
        parser.error("Case limits must be positive")
    if args.title is not None and (not args.title or len(args.title) > 31 or not args.title.isascii()):
        parser.error("Title must be non-empty ASCII, at most 31 characters")
    prior = json.loads(args.matrix.read_text(encoding="utf-8"))
    descriptor = args.descriptor.read_bytes()
    descriptor_hash = hashlib.sha256(descriptor).hexdigest()
    models = {row["cameraId"]: row["model"] for row in prior["rows"]
              if row["classification"] == "compiler-validated" and row["descriptorSha256"] == descriptor_hash}
    if not models:
        parser.error("No previously validated models for this exact descriptor")
    if args.camera_id:
        models = {key: value for key, value in models.items() if key in args.camera_id}
        if not models:
            parser.error("Requested camera IDs were not validated in this matrix")
    import frida
    device = frida.get_local_device()
    host = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    here = Path(__file__).resolve().parent
    production = (here / "dynamic_camera_agent.js").read_text(encoding="utf-8")
    # Frida's Process API is read-only. Redirect module lookup only in this
    # ephemeral test copy; the production file remains unchanged.
    test_agent = production.replace("Process.getModuleByName(", "testGetModuleByName(")
    source = "\n".join(((here / "transport_test_bootstrap.js").read_text(encoding="utf-8"),
                        test_agent, (here / "transport_test_checks.js").read_text(encoding="utf-8")))
    keys = cipher_tables(args.dll)
    report = {"physicalAcceptanceTested": False, "realEdsdkLoaded": False,
              "descriptorSha256": descriptor_hash, "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
              "productionAgentSha256": hashlib.sha256((here / "dynamic_camera_agent.js").read_bytes()).hexdigest(), "rows": []}
    for index, (model_id, model_name) in enumerate(list(models.items())[:args.limit]):
        for vector_index, vector in enumerate(VECTORS[:args.vector_limit]):
            row = {"cameraId": model_id, "model": model_name, "vector": vector,
                   "sourcePf3Sha256": hashlib.sha256((args.vectors / f"{vector}.pf3").read_bytes()).hexdigest()}
            try:
                metadata, payload, tables = run_case(device, host, args.dll.resolve(), source,
                    (args.vectors / f"{vector}.pf3").resolve(), model_id, descriptor, 1 + vector_index % 3,
                    args.title, args.output.with_name(f"NAME_TEST_{model_id}_{vector_index}.pf3").resolve())
                check = (table_check(payload, metadata["compiler"], tables, vector, args.fixtures, keys)
                         if args.title is None else {"method": "name-and-transport-only", "ok": True})
                if not check["ok"] and args.legacy_probe and check["method"] == "independent-compact-grid-reference":
                    expected = legacy_reference(device, host, args.dll.resolve(), args.legacy_probe,
                                                (args.vectors / f"{vector}.pf3").resolve(), model_id, descriptor)
                    check["independentResearchOutputExact"] = payload == expected
                    check["independentResearchAgentSha256"] = hashlib.sha256(args.legacy_probe.read_bytes()).hexdigest()
                    check["independentResearchOutputSha256"] = hashlib.sha256(expected).hexdigest()
                    check["ok"] = payload == expected
                name_bytes = bytes.fromhex(tables["nameHex"])
                name = name_bytes.split(b"\0", 1)[0]
                name_offset = payload[:372].find(name) if name else -1
                name_ok = (name_offset == 8 and payload[8:40] == name_bytes and
                           (args.title is None or name == args.title.encode("ascii")))
                if args.capture_payloads:
                    capture = args.output.with_name(f"{args.output.stem}_{model_id}_{vector}.bin")
                    capture.write_bytes(payload)
                    row["privateResearchPayload"] = str(capture.resolve())
                row.update(transport=metadata, tables=check, nameOffset=name_offset,
                           namePreserved=name_ok, nameBytesExact=payload[8:40] == name_bytes,
                           expectedName=args.title, size=len(payload),
                           sha256=hashlib.sha256(payload).hexdigest(), ok=check["ok"] and name_ok)
            except Exception as exc:
                row.update(ok=False, error=str(exc))
            report["rows"].append(row)
            report["summary"] = summarize(report["rows"])
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(".tmp")
            temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
            temporary.replace(args.output)
            print(f"{index + 1}/{len(models)} {model_name} {vector}: {'PASS' if row['ok'] else 'FAIL'}", flush=True)
    print(json.dumps(report["summary"]))
    return int(report["summary"]["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
