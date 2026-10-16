"""Trace existing scratch curves through unmodified Canon compilation."""
import argparse
import hashlib
import json
from pathlib import Path
from .compiler_regression import cipher_tables
from .pf3_field_experiments import compile_stock
from .virtual_compatibility import load_models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dll", "source", "scratch-folder", "agent", "descriptor", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--camera-id", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--matrix", type=Path, help="Trace baseline for every model ID instead of scratch mutations")
    parser.add_argument("--matrix-curves", action="store_true", help="Also trace each existing curve scratch for every matrix model")
    parser.add_argument("--scratch-glob", default="CURVE_*.pf3")
    parser.add_argument("--observe-color", action="store_true")
    parser.add_argument("--observe-dense", action="store_true", help="Capture complete initialized source grid, private research only")
    parser.add_argument("--private-payload-folder", type=Path, help="Retain stock compiler bytes for offline packing research; never overwrites")
    parser.add_argument("--packing-only", action="store_true", help="Observe final packers only, avoiding costly per-node math hooks")
    args = parser.parse_args()
    cipher_tables(args.dll)
    import frida
    device = frida.get_local_device()
    descriptor = args.descriptor.read_bytes()
    report = {"cameraAccess": False, "compilerPatched": False,
              "dllSha256": hashlib.sha256(args.dll.read_bytes()).hexdigest(),
              "descriptorSha256": hashlib.sha256(descriptor).hexdigest(),
              "cameraId": args.camera_id, "files": []}
    cases = [(args.source, model["cameraId"], model["model"]) for model in load_models(args.matrix)] if args.matrix else [
        (path, args.camera_id, "single-model") for path in [args.source] + sorted(args.scratch_folder.glob(args.scratch_glob))]
    if args.matrix and args.matrix_curves:
        cases = [(path, model["cameraId"], model["model"]) for model in load_models(args.matrix)
                 for path in [args.source] + sorted(args.scratch_folder.glob(args.scratch_glob))]
    cases = list({(path.resolve(),camera_id,model):(path,camera_id,model)
                  for path,camera_id,model in cases}.values())
    for path, camera_id, model in cases:
        try:
            result, payload = compile_stock(device, args.dll.resolve(), args.agent, path.resolve(),
                                      camera_id, descriptor, observe=True, observe_color=args.observe_color,
                                      observe_dense=args.observe_dense or args.packing_only, packing_only=args.packing_only)
            if args.private_payload_folder:
                args.private_payload_folder.mkdir(parents=True,exist_ok=True)
                target = args.private_payload_folder / f'{camera_id:08x}_{path.stem}.bin'
                with target.open('xb') as capture: capture.write(payload)
                result['privateResearchPayload'] = str(target.resolve())
        except Exception as error:
            result = dict(getattr(error,'native_report',{}))
            result.update(error=str(error),classification='failed-not-validated')
        result.update(cameraId=camera_id, model=model)
        result.update(source=str(path.resolve()), sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest())
        report["files"].append(result)
        status = 'FAILED' if result.get('error') else 'COMPILED'
        print(status, model, path.name, result.get("mlibCalls", {}).get("counts", result.get("error")), flush=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
