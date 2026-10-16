"""Exercise the production Canon compiler agent without EDSDK or a camera.

Use recorded descriptors as test inputs. Results establish compiler behavior
for those inputs, never physical acceptance by the named camera.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path


LOAD_COMPILER = """
rpc.exports = { load: function(path) {
    const module = Module.load(path);
    return {path: module.path, size: module.size};
} };
"""


def load_models(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif "descriptors" in data:
        rows = next(iter(data["descriptors"].values()))["models"]
    else:
        rows = data["rows"]
    models = {}
    for row in rows:
        if row.get("scope", "EOS") != "EOS":
            continue
        value = row.get("cameraIdHex", row.get("cameraId"))
        camera_id = int(value, 0) if isinstance(value, str) else int(value)
        if not 0 <= camera_id <= 0xFFFFFFFF:
            raise ValueError("Camera ID is outside the unsigned 32-bit range")
        models[camera_id] = {"cameraId": camera_id, "model": row["model"]}
    if not models:
        raise ValueError("No EOS models in the supplied matrix")
    return list(models.values())


def compile_vector(device, host: Path, dll: Path, agent_source: str,
                   pf3: Path, model: dict, descriptor: bytes) -> dict:
    pid = None
    session = None
    scripts = []
    try:
        pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle",
                            "Hidden", "-NoExit", "-Command", "-"])
        session = device.attach(pid)
        loader = session.create_script(LOAD_COMPILER)
        scripts.append(loader)
        loader.load()
        device.resume(pid)
        loader.exports_sync.load(str(dll))
        agent = session.create_script(agent_source)
        scripts.append(agent)
        agent.load()
        metadata, payload = agent.exports_sync.testnativecompile(
            str(pf3), "COMPATIBILITY TEST",
            model["cameraId"].to_bytes(4, "little").hex(), descriptor.hex(),
        )
        payload = bytes(payload)
        acceptance = metadata.get("acceptanceHook") or {}
        return {
            "compiled": bool(metadata.get("ok")),
            "validated": bool(metadata.get("ok") and acceptance.get("ok") and payload),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest() if payload else None,
            "compiler": metadata,
        }
    except Exception as exc:
        return {"compiled": False, "validated": False, "error": str(exc)}
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
        if pid is not None:
            try:
                device.kill(pid)
            except Exception:
                pass


def classify(vectors: dict[str, dict]) -> str:
    if not all(item.get("validated") for item in vectors.values()):
        return "blocked"
    if len({item.get("size") for item in vectors.values()}) != 1:
        return "inconsistent-output-size"
    if vectors["identity"].get("sha256") == vectors["look"].get("sha256"):
        return "look-ignored"
    return "compiler-validated"


def summarize(rows: list[dict]) -> dict:
    by_model = {}
    by_descriptor = {}
    for row in rows:
        by_model.setdefault(row["cameraId"], []).append(row)
        by_descriptor.setdefault(row["descriptorSha256"], []).append(row)
    passing = [items for items in by_model.values()
               if any(row["classification"] == "compiler-validated" for row in items)]
    blocked = [items[0]["model"] for items in by_model.values()
               if all(row["classification"] != "compiler-validated" for row in items)]
    return {
        "testedModels": len(by_model),
        "testedCases": len(rows),
        "modelsPassingAtLeastOneProxyDescriptor": len(passing),
        "modelsBlockedWithAllTestedDescriptors": blocked,
        "descriptorResults": [
            {"descriptor": items[0]["descriptor"], "sha256": key,
             "classifications": dict(Counter(row["classification"] for row in items))}
            for key, items in by_descriptor.items()
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True, help="Model list or an archived compiler matrix")
    parser.add_argument("--descriptor", type=Path, action="append", required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--look", type=Path, required=True)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    host = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    agent = Path(__file__).with_name("dynamic_camera_agent.js")
    for path in [args.models, args.identity, args.look, args.dll, host, agent, *args.descriptor]:
        if not path.is_file():
            parser.error(f"Required file missing: {path}")
    import frida
    models = load_models(args.models)
    source = agent.read_text(encoding="utf-8")
    device = frida.get_local_device()
    report = {
        "format": "CanonStyleStudio.VirtualCompatibility.v1",
        "physicalCameraAcceptanceTested": False,
        "registrationCommandsSent": False,
        "agentSha256": hashlib.sha256(source.encode()).hexdigest(),
        "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
        "vectors": {name: {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    for name, path in (("identity", args.identity), ("look", args.look))},
        "rows": [],
    }
    for descriptor_path in args.descriptor:
        descriptor = descriptor_path.read_bytes()
        for model in models:
            vectors = {
                name: compile_vector(device, host, args.dll.resolve(), source,
                                     path.resolve(), model, descriptor)
                for name, path in (("identity", args.identity), ("look", args.look))
            }
            row = {
                **model, "descriptor": descriptor_path.name,
                "descriptorSha256": hashlib.sha256(descriptor).hexdigest(),
                "vectors": vectors, "classification": classify(vectors),
            }
            report["rows"].append(row)
            report["summary"] = summarize(report["rows"])
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + ".tmp")
            temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
            temporary.replace(args.output)
            print(f"{model['model']} / {descriptor_path.name}: {row['classification']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
