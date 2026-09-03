from __future__ import annotations
import faulthandler
import os
import subprocess
import sys
import traceback
from pathlib import Path

from canon_runtime import BUILD_ID, PUBLIC_NAME, PUBLIC_VERSION, logs_dir

HERE=Path(__file__).resolve().parent
LOG=logs_dir()/"startup.log"

def write_header(f):
    f.write("="*72+"\n")
    f.write(f"{PUBLIC_NAME} {PUBLIC_VERSION} STARTUP LOG\n")
    f.write(f"Build: {BUILD_ID}\n")
    f.write("Python: "+sys.executable+"\n")
    f.write("Version: "+sys.version.replace("\n"," ")+"\n")
    f.write("CWD: "+os.getcwd()+"\n")
    f.write("="*72+"\n")
    f.flush()

def main():
    with LOG.open("w",encoding="utf-8",errors="replace") as f:
        write_header(f)
        try:
            faulthandler.enable(file=f, all_threads=True)
        except Exception:
            pass

        # Import startup modules one by one so a missing/broken binary dependency
        # produces a useful line instead of a disappearing console.
        checks=[
            ("PySide6", "import PySide6"),
            ("QtCore", "from PySide6 import QtCore"),
            ("QtGui", "from PySide6 import QtGui"),
            ("QtWidgets", "from PySide6 import QtWidgets"),
            ("Pillow", "from PIL import Image"),
            ("NumPy", "import numpy"),
            ("canon_engine", "import canon_engine"),
            ("project_state", "import project_state"),
            ("dpp_client", "import dpp_client"),
            ("main module", "import canon_style_studio"),
        ]
        glb={}
        for label,code in checks:
            try:
                exec(code,glb,glb)
                msg=f"[OK] {label}"
                print(msg, flush=True);f.write(msg+"\n");f.flush()
            except BaseException:
                tb=traceback.format_exc()
                print(f"[FAIL] {label}\n{tb}", file=sys.stderr, flush=True)
                f.write(f"[FAIL] {label}\n{tb}\n");f.flush()
                return 30

        try:
            import canon_style_studio
            rc=canon_style_studio.main()
            f.write(f"\nApplication event loop returned: {rc}\n");f.flush()
            return int(rc or 0)
        except BaseException:
            tb=traceback.format_exc()
            print(tb,file=sys.stderr,flush=True)
            f.write("\nUNHANDLED STARTUP/APPLICATION ERROR\n"+tb+"\n");f.flush()
            return 31

if __name__=="__main__":
    raise SystemExit(main())
