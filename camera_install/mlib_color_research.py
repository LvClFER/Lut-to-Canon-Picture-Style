"""Probe isolated MLib forward/inverse color math, never camera commands."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from .compiler_regression import cipher_tables
from .virtual_compatibility import LOAD_COMPILER


def vectors():
    rows = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.], [1., 1., 1.]]
    rows += [[value] * 3 for value in (-.1, -.04045, -.02, .02, .04045, .1, .5, 1.2)]
    rows += [[.2, .4, .8], [.8, .2, .4], [.4, .8, .2]]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--float-lab", action="store_true", help="Probe floating XYZ/Lab helpers instead of RGB/XYZ")
    args = parser.parse_args()
    cipher_tables(args.dll)
    dll = args.dll.resolve()
    mlib = dll.parent / "MLib.dll"
    if hashlib.sha256(mlib.read_bytes()).hexdigest() != "a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a":
        raise ValueError("Unknown MLib revision")
    import frida
    device = frida.get_local_device()
    host = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    pid = device.spawn([str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Sleep -Seconds 3600"])
    session, scripts = None, []
    try:
        session = device.attach(pid)
        loader = session.create_script(LOAD_COMPILER); scripts.append(loader); loader.load()
        device.resume(pid); loader.exports_sync.load(str(dll))
        source = Path(__file__).with_name("mlib_color_probe.js").read_text(encoding="utf-8")
        probe = session.create_script(source); scripts.append(probe); probe.load()
        result = probe.exports_sync.run(vectors(), list(range(16)), args.float_lab)
        if Path(result["mlibPath"]).resolve() != mlib:
            raise ValueError("Loaded MLib differs from verified path")
        result.update(cameraAccess=False, compilerPatched=False, dllSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                      mlibSha256=hashlib.sha256(mlib.read_bytes()).hexdigest(), probeSha256=hashlib.sha256(source.encode()).hexdigest())
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"cases": len(result["rows"]), "forwardFailures": sum(row["rcForward"] != 0 for row in result["rows"])}))
    finally:
        for script in reversed(scripts):
            try: script.unload()
            except Exception: pass
        if session is not None:
            try: session.detach()
            except Exception: pass
        try: device.kill(pid)
        except Exception: pass


if __name__ == "__main__":
    main()
