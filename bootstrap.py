from __future__ import annotations
import importlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# rawpy remains useful as fallback, but the UI should not fail to start merely
# because the optional fallback cannot be installed. Core UI deps are separate.
CORE = [
    ("PySide6", "PySide6"),
    ("PIL", "Pillow"),
    ("numpy", "numpy"),
    ("tifffile", "tifffile"),
    ("imageio", "imageio"),
]
OPTIONAL = [
    ("rawpy", "rawpy"),
]

def missing(items):
    out=[]
    for mod,pkg in items:
        try:
            importlib.import_module(mod)
        except Exception:
            out.append((mod,pkg))
    return out

def pip_install(pkgs):
    if not pkgs:
        return True
    cmd=[sys.executable,"-m","pip","install","--disable-pip-version-check","--upgrade",*pkgs]
    print("[BOOTSTRAP]", " ".join(cmd), flush=True)
    try:
        subprocess.check_call(cmd)
        return True
    except Exception as e:
        print("[BOOTSTRAP] pip failed:", repr(e), flush=True)
        return False

def main():
    print("[BOOTSTRAP] Python:", sys.executable, flush=True)
    print("[BOOTSTRAP] Version:", sys.version.replace("\\n"," "), flush=True)

    core_missing=missing(CORE)
    if core_missing:
        print("[BOOTSTRAP] Core dependencies missing:", ", ".join(p for _,p in core_missing), flush=True)
        if not pip_install([p for _,p in core_missing]):
            return 20

    core_missing=missing(CORE)
    if core_missing:
        print("[BOOTSTRAP] Still missing:", core_missing, flush=True)
        return 21

    opt_missing=missing(OPTIONAL)
    if opt_missing:
        print("[BOOTSTRAP] Optional LibRaw fallback missing; trying to install rawpy.", flush=True)
        pip_install([p for _,p in opt_missing])

    print("[BOOTSTRAP] Core dependencies OK.", flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
