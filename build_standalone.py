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
PUBLIC_RELEASE_NAME=f"CanonStyleStudio_Public_Alpha_{PUBLIC_VERSION}_Windows_x64"
PRIVATE_RELEASE_NAME=f"CanonStyleStudio_{PUBLIC_VERSION}_PRIVATE_MULTI_CAMERA_TEST"
CANON_FORBIDDEN_NAMES=(
    "dppcore.dll","edscfparse.dll","pseditor.exe","dppviewer.exe",
    "superia_selftest.pf3","superia_expected_block_8192.bin",
    "rp_superia_template_16752.bin","1300d_camera_id.bin","1300d_descriptor_7772.bin",
)
FORBIDDEN_SUFFIXES={".icc",".icm",".pf3",".cr2",".cr3",".crw",".dmp",".log",".py",".pyc"}
INCOMPATIBLE_COLLECTED_QT_DLLS=("icuuc.dll","icudt78.dll")


def run(command):
    print("[BUILD]"," ".join(str(x) for x in command),flush=True)
    subprocess.check_call([str(x) for x in command],cwd=HERE)


def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def audit(root, allow_private_support=False):
    problems=[]
    for path in root.rglob("*"):
        if not path.is_file():continue
        if allow_private_support:
            try:
                if path.is_relative_to(root/"camera_support"):continue
            except ValueError:
                pass
        lower=path.name.lower()
        if lower in CANON_FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:problems.append(str(path.relative_to(root)))
        if any(part.lower()=="__pycache__" for part in path.parts):problems.append(str(path.relative_to(root)))
    return sorted(set(problems))


def build(output_root, private_multi_camera=False):
    output_root=output_root.resolve();output_root.mkdir(parents=True,exist_ok=True)
    release_name=PRIVATE_RELEASE_NAME if private_multi_camera else PUBLIC_RELEASE_NAME
    release=output_root/release_name
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
             "--add-data",f"{HERE/'camera_install'/'dynamic_camera_agent.js'}{separator}camera_install",
             HERE/"canon_style_studio.py"])
        built=main_dist/"CanonStyleStudio"
        if not (built/"CanonStyleStudio.exe").is_file():raise RuntimeError("Standalone application was not generated")
        # Qt6Core on the supported Windows versions uses the Windows ICU
        # forwarding DLLs.  PyInstaller can accidentally resolve icuuc.dll to
        # an unrelated ICU 78 binary on the build machine and copy it beside
        # the executable.  That binary lacks Qt's required unversioned exports
        # and makes ``from PySide6 import QtCore`` fail with WinError 127.
        for dll_name in INCOMPATIBLE_COLLECTED_QT_DLLS:
            collected=built/"runtime"/dll_name
            if collected.is_file():collected.unlink()
        shutil.copytree(built,release)
    for name in ("README.md","TESTING_GUIDE.md","PUBLIC_ALPHA_RELEASE_NOTES.md","ARCHITECTURE_STATUS.md"):
        shutil.copy2(HERE/name,release/name)
    (release/"START_CANON_STYLE_STUDIO.bat").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\nstart "" "CanonStyleStudio.exe"\r\n',encoding="ascii")
    if private_multi_camera:
        support=HERE/"camera_support"
        if not support.is_dir():raise RuntimeError("Private camera support folder is unavailable")
        shutil.copytree(support,release/"camera_support")
        (release/"PRIVATE_TEST_PACKAGE.txt").write_text(
            "Private multi-camera compatibility build. Canon/Manual Loader research fixtures are included.\n"
            "Do not publish or redistribute this folder publicly.\n",encoding="utf-8")
    manifest={"name":release_name,"version":PUBLIC_VERSION,"build_id":BUILD_ID,
              "created_utc":datetime.now(timezone.utc).isoformat(),"architecture":"Windows x64",
              "python_required":False,"pse_required_for_canon_raw":True,
              "canon_resources_bundled":bool(private_multi_camera),"entrypoint":"CanonStyleStudio.exe",
              "distribution":"private compatibility testing only; do not publish" if private_multi_camera else "public",
              "camera_install":{"method":"target-PF3-scoped EdsCFParse acceptance correction; EOS Utility compiles and sends its original camera-native payload unchanged","model_specific_builders":False,"edsdk_payload_replaced":False,"edsdk_arguments_modified":False,"compiler_symbol_resolution":"semantic signatures","offline_validated_transactions":["EOS 1300D / 16744","EOS RP / 16752","EOS R8 / 83076"],"physical_revalidation_required":True,"external_selftest_assets_required":not private_multi_camera,"support_assets_bundled":bool(private_multi_camera)},
              "portable_storage":{"settings":"app_data","support":"camera_support","camera_exports":"exported_styles"}}
    (release/"STANDALONE_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    problems=audit(release,allow_private_support=private_multi_camera)
    if problems:raise RuntimeError("Standalone audit found forbidden files:\n"+"\n".join(problems))
    if private_multi_camera:
        print(f"[PASS] {release}")
        print("[PASS] Private folder only; no ZIP generated")
        return release,None
    zip_path=output_root/f"{release_name}.zip";temp_zip=zip_path.with_suffix(".zip.tmp")
    if temp_zip.exists():temp_zip.unlink()
    with zipfile.ZipFile(temp_zip,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as archive:
        for path in sorted(p for p in release.rglob("*") if p.is_file()):archive.write(path,f"{release_name}/{path.relative_to(release).as_posix()}")
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
    parser.add_argument("--private-multi-camera",action="store_true")
    args=parser.parse_args(argv);build(args.output_root,private_multi_camera=args.private_multi_camera);return 0


if __name__=="__main__":raise SystemExit(main())
