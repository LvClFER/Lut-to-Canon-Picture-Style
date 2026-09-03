from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from canon_runtime import BUILD_ID, PUBLIC_VERSION


HERE=Path(__file__).resolve().parent
RELEASE_NAME=f"CanonStyleStudio_Public_Alpha_{PUBLIC_VERSION}_Windows_x64"
CANON_FORBIDDEN_NAMES=(
    "dppcore.dll","edscfparse.dll","pseditor.exe","dppviewer.exe",
    "superia_selftest.pf3","superia_expected_block_8192.bin",
    "rp_superia_template_16752.bin","1300d_camera_id.bin","1300d_descriptor_7772.bin",
)
FORBIDDEN_SUFFIXES={".icc",".icm",".pf3",".cr2",".cr3",".crw",".dmp",".log",".py",".pyc"}


def run(command):
    print("[BUILD]"," ".join(str(x) for x in command),flush=True)
    subprocess.check_call([str(x) for x in command],cwd=HERE)


def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def audit(root):
    problems=[]
    for path in root.rglob("*"):
        if not path.is_file():continue
        lower=path.name.lower()
        if lower in CANON_FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:problems.append(str(path.relative_to(root)))
        if any(part.lower()=="__pycache__" for part in path.parts):problems.append(str(path.relative_to(root)))
    return sorted(set(problems))


def build(output_root):
    output_root=output_root.resolve();output_root.mkdir(parents=True,exist_ok=True)
    release=output_root/RELEASE_NAME
    if release.exists():shutil.rmtree(release)
    with tempfile.TemporaryDirectory(prefix="canon_style_build_",dir=output_root) as temp_name:
        temp=Path(temp_name);worker_dist=temp/"worker_dist";main_dist=temp/"main_dist"
        run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onefile","--console",
             "--name","canon_dpp_worker","--distpath",worker_dist,"--workpath",temp/"worker_work",
             "--specpath",temp, HERE/"canon_dpp_worker.py"])
        worker=worker_dist/"canon_dpp_worker.exe"
        if not worker.is_file():raise RuntimeError("Standalone Canon worker was not generated")
        separator=";" if os.name=="nt" else ":"
        run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onedir","--windowed",
             "--name","CanonStyleStudio","--contents-directory","runtime",
             "--distpath",main_dist,"--workpath",temp/"main_work","--specpath",temp,
             "--add-binary",f"{worker}{separator}.",
             "--add-data",f"{HERE/'example_luts'/'hald_identity_8.png'}{separator}example_luts",
             "--add-data",f"{HERE/'example_luts'/'Lightroom_Hald_Template_512_64cube_sRGB_16bit.tif'}{separator}example_luts",
             "--add-data",f"{HERE/'camera_install'/'rp_loader_agent.js'}{separator}camera_install",
             HERE/"canon_style_studio.py"])
        built=main_dist/"CanonStyleStudio"
        if not (built/"CanonStyleStudio.exe").is_file():raise RuntimeError("Standalone application was not generated")
        shutil.copytree(built,release)
    for name in ("README.md","TESTING_GUIDE.md","PUBLIC_ALPHA_RELEASE_NOTES.md","ARCHITECTURE_STATUS.md"):
        shutil.copy2(HERE/name,release/name)
    (release/"START_CANON_STYLE_STUDIO.bat").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\nstart "" "CanonStyleStudio.exe"\r\n',encoding="ascii")
    manifest={"name":RELEASE_NAME,"version":PUBLIC_VERSION,"build_id":BUILD_ID,
              "created_utc":datetime.now(timezone.utc).isoformat(),"architecture":"Windows x64",
              "python_required":False,"pse_required_for_canon_raw":True,
              "canon_resources_bundled":False,"entrypoint":"CanonStyleStudio.exe",
              "camera_install":{"validated_bodies":["EOS RP"],"external_support_assets_required":True,"support_assets_bundled":False},
              "portable_storage":{"settings":"app_data","support":"camera_support","camera_exports":"exported_styles"}}
    (release/"STANDALONE_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    problems=audit(release)
    if problems:raise RuntimeError("Standalone audit found forbidden files:\n"+"\n".join(problems))
    zip_path=output_root/f"{RELEASE_NAME}.zip";temp_zip=zip_path.with_suffix(".zip.tmp")
    if temp_zip.exists():temp_zip.unlink()
    with zipfile.ZipFile(temp_zip,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as archive:
        for path in sorted(p for p in release.rglob("*") if p.is_file()):archive.write(path,f"{RELEASE_NAME}/{path.relative_to(release).as_posix()}")
    temp_zip.replace(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError(f"ZIP CRC failure: {bad}")
    print(f"[PASS] {release}")
    print(f"[PASS] {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print(f"[PASS] SHA-256 {sha256(zip_path)}")
    return release,zip_path


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--output-root",type=Path,default=HERE.parent/"PUBLIC_ALPHA_STANDALONE")
    args=parser.parse_args(argv);build(args.output_root);return 0


if __name__=="__main__":raise SystemExit(main())
