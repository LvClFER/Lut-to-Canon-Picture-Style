from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from canon_runtime import BUILD_ID, PUBLIC_VERSION


HERE=Path(__file__).resolve().parent
PACKAGE_NAME=f"CanonStyleStudio_Public_Alpha_{PUBLIC_VERSION}"
FILES=(
    "canon_style_studio.py","canon_engine.py","canon_dpp_worker.py","dpp_client.py",
    "project_state.py","render_geometry.py","canon_runtime.py","creative_controls.py","test_report.py",
    "bootstrap.py","launch_guard.py","START_CANON_STYLE_STUDIO.bat","requirements.txt",
    "SELF_TEST.py","REGRESSION_TESTS.py","PUBLIC_ALPHA_REGRESSION.py",
    "README.md","TESTING_GUIDE.md","PUBLIC_ALPHA_RELEASE_NOTES.md","ARCHITECTURE_STATUS.md",
    "camera_install/__init__.py","camera_install/rp_assets.py","camera_install/rp_payload.py",
    "camera_install/eos_hook.py","camera_install/ui.py","camera_install/rp_loader_agent.js",
)
EXAMPLES=("example_luts/hald_identity_8.png","example_luts/Lightroom_Hald_Template_512_64cube_sRGB_16bit.tif")
FORBIDDEN_SUFFIXES={".dll",".exe",".icc",".icm",".pf3",".cr2",".cr3",".crw",".dmp",".log",".pyc"}
FORBIDDEN_NAMES={"superia_expected_block_8192.bin","rp_superia_template_16752.bin","1300d_camera_id.bin","1300d_descriptor_7772.bin"}
FORBIDDEN_PARTS={"__pycache__","bases","canon_resources","native_probe_results","test_files","samples","app_data","camera_support","exported_styles"}
TEXT_SUFFIXES={".py",".js",".md",".txt",".bat",".json",".toml",".ini",".cfg"}
SECRET_PATTERNS=(re.compile(r"C:\\Users\\",re.I),re.compile(r"/Users/[^/]+",re.I),
                 re.compile(r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+",re.I))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_tree(root: Path):
    problems=[]
    for path in root.rglob("*"):
        rel=path.relative_to(root)
        if any(part.lower() in FORBIDDEN_PARTS for part in rel.parts):problems.append(f"forbidden path: {rel}")
        if not path.is_file():continue
        if path.name.lower() in FORBIDDEN_NAMES:problems.append(f"forbidden research fixture: {rel}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:problems.append(f"forbidden extension: {rel}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text=path.read_text(encoding="utf-8",errors="replace")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):problems.append(f"private path/secret pattern: {rel} ({pattern.pattern})")
    return sorted(set(problems))


def build(output_root: Path):
    output_root=output_root.resolve();output_root.mkdir(parents=True,exist_ok=True)
    package=(output_root/PACKAGE_NAME).resolve()
    if package.parent!=output_root:raise ValueError("Unsafe package output path")
    if package.exists():shutil.rmtree(package)
    package.mkdir()
    copied=[]
    for name in (*FILES,*EXAMPLES):
        source=HERE/name
        if not source.is_file():raise FileNotFoundError(f"Required public file missing: {name}")
        target=package/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);copied.append(target)
    manifest={"name":PACKAGE_NAME,"version":PUBLIC_VERSION,"build_id":BUILD_ID,"created_utc":datetime.now(timezone.utc).isoformat(),
              "legal":"No Canon DLL, executable, ICC/ICM, PF3, RAW or internal resource is distributed.",
              "camera_install":{"validated_bodies":["EOS RP"],"external_support_assets_required":True,"support_assets_bundled":False},
              "portable_storage":{"settings":"app_data","support":"camera_support","camera_exports":"exported_styles"},
              "files":[{"path":str(p.relative_to(package)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha(p)} for p in copied]}
    manifest_path=package/"PUBLIC_PACKAGE_MANIFEST.json";manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    problems=audit_tree(package)
    if problems:raise RuntimeError("Public package audit failed:\n"+"\n".join(problems))
    with tempfile.TemporaryDirectory() as compile_dir:
        for index,path in enumerate(package.rglob("*.py")):
            py_compile.compile(str(path),doraise=True,cfile=str(Path(compile_dir)/(f"{index}_{path.stem}.pyc")))
    zip_path=output_root/f"{PACKAGE_NAME}.zip"
    temp=zip_path.with_suffix(".zip.tmp")
    if temp.exists():temp.unlink()
    with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(p for p in package.rglob("*") if p.is_file()):archive.write(path,f"{PACKAGE_NAME}/{path.relative_to(package).as_posix()}")
    temp.replace(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        bad=[n for n in archive.namelist() if Path(n).name.lower() in FORBIDDEN_NAMES or Path(n).suffix.lower() in FORBIDDEN_SUFFIXES or any(part.lower() in FORBIDDEN_PARTS for part in Path(n).parts)]
        if bad:raise RuntimeError(f"ZIP audit failed: {bad}")
        corrupt=archive.testzip()
        if corrupt:raise RuntimeError(f"ZIP CRC failed: {corrupt}")
    return package,zip_path,manifest


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--output-root",type=Path,default=HERE.parent/"PUBLIC_ALPHA_RELEASE")
    args=parser.parse_args(argv);package,zip_path,manifest=build(args.output_root)
    print(f"[PASS] Clean folder: {package}")
    print(f"[PASS] ZIP: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print(f"[PASS] {len(manifest['files'])+1} files; recursive proprietary/privacy scan clean")
    return 0


if __name__=="__main__":raise SystemExit(main())
