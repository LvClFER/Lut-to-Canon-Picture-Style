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

from canon_runtime import BUILD_ID, PUBLIC_VERSION, BASIC_PF3_SHA256, basic_pf3_resource


HERE=Path(__file__).resolve().parent
PUBLIC_RELEASE_NAME=f"CanonStyleStudio_{PUBLIC_VERSION}_Windows_x64"
CANON_FORBIDDEN_NAMES=(
    "dppcore.dll","edscfparse.dll","pseditor.exe","dppviewer.exe",
    "superia_selftest.pf3","superia_expected_block_8192.bin",
    "rp_superia_template_16752.bin","1300d_camera_id.bin","1300d_descriptor_7772.bin",
)
FORBIDDEN_SUFFIXES={".bin",".icc",".icm",".pf3",".cr2",".cr3",".crw",".dmp",".log",".py",".pyc"}
INCOMPATIBLE_COLLECTED_QT_DLLS=("icuuc.dll","icudt78.dll")
RESEARCH_ONLY_MODULES=('camera_install.compiler_regression',
                      'camera_install.virtual_compatibility','camera_install.pf3_research')


def run(command):
    print("[BUILD]"," ".join(str(x) for x in command),flush=True)
    subprocess.check_call([str(x) for x in command],cwd=HERE)


def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()


def require_raw_decoder():
    try:
        import rawpy
    except Exception as error:
        raise RuntimeError('A distributable build requires a working rawpy/LibRaw decoder.') from error
    return dict(rawpy=rawpy.__version__,libraw=list(rawpy.libraw_version))


def qt_webengine_snapshot(path):
    if path.name!='v8_context_snapshot.bin':return False
    from PySide6.QtCore import QLibraryInfo
    sources=(Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath))/'resources'/path.name,
        Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath))/'QtWebEngineCore.framework/Resources'/path.name)
    return any(source.is_file() and sha256(path)==sha256(source) for source in sources)


def audit(root):
    problems=[]
    for path in root.rglob("*"):
        if not path.is_file():continue
        if any(part.lower()=="camera_support" for part in path.relative_to(root).parts):
            problems.append(str(path.relative_to(root)))
        lower=path.name.lower()
        approved=((path.parent.name=='basic_pf3' and path.name in BASIC_PF3_SHA256
            and sha256(path)==BASIC_PF3_SHA256[path.name]) or qt_webengine_snapshot(path))
        if lower in CANON_FORBIDDEN_NAMES or (path.suffix.lower() in FORBIDDEN_SUFFIXES and not approved):problems.append(str(path.relative_to(root)))
        if any(part.lower()=="__pycache__" for part in path.parts):problems.append(str(path.relative_to(root)))
    return sorted(set(problems))


def audit_modules(executable):
    from PyInstaller.archive.readers import CArchiveReader
    modules=CArchiveReader(str(executable)).open_embedded_archive('PYZ.pyz').toc
    unexpected=[name for name in modules if name in RESEARCH_ONLY_MODULES]
    if unexpected:raise RuntimeError(f'Research modules in application: {unexpected}')
    required={'sample_images','sample_browser','rawpy','camera_install.family_registration_reference','camera_install.camera_families_reference',
              'camera_install.independent_registration_reference','camera_install.legacy_dense9_carrier_reference'}
    if not required.issubset(modules):
        raise RuntimeError(f'Missing independent runtime modules: {sorted(required.difference(modules))}')


def build(output_root, folder_only=False):
    decoder=require_raw_decoder()
    output_root=output_root.resolve();output_root.mkdir(parents=True,exist_ok=True)
    release_name=PUBLIC_RELEASE_NAME
    release=output_root/release_name
    if release.exists():shutil.rmtree(release)
    for name in BASIC_PF3_SHA256:
        if basic_pf3_resource(name[:-4].replace('_',' ')) is None:
            raise FileNotFoundError('Required basic PF3 missing: '+name)
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
             "--add-data",f"{HERE/'basic_pf3'}{separator}basic_pf3",
             "--add-data",f"{HERE/'assets'/'canon-logo.png'}{separator}assets",
             "--add-data",f"{HERE/'assets'/'step-up.svg'}{separator}assets",
             "--add-data",f"{HERE/'assets'/'step-down.svg'}{separator}assets",
             *[value for name in RESEARCH_ONLY_MODULES for value in ('--exclude-module',name)],
             HERE/"canon_style_studio.py"])
        built=main_dist/"CanonStyleStudio"
        if not (built/"CanonStyleStudio.exe").is_file():raise RuntimeError("Standalone application was not generated")
        for debug_resource in (built/'runtime/PySide6/resources').glob('*.debug.*'):
            debug_resource.unlink()
        # Qt6Core on the supported Windows versions uses the Windows ICU
        # forwarding DLLs.  PyInstaller can accidentally resolve icuuc.dll to
        # an unrelated ICU 78 binary on the build machine and copy it beside
        # the executable.  That binary lacks Qt's required unversioned exports
        # and makes ``from PySide6 import QtCore`` fail with WinError 127.
        for dll_name in INCOMPATIBLE_COLLECTED_QT_DLLS:
            collected=built/"runtime"/dll_name
            if collected.is_file():collected.unlink()
        shutil.copytree(built,release)
    for name in ("README.md","TESTING_GUIDE.md","PUBLIC_ALPHA_RELEASE_NOTES.md","ARCHITECTURE_STATUS.md","CAMERA_COMPATIBILITY.md"):
        shutil.copy2(HERE/name,release/name)
    (release/"START_CANON_STYLE_STUDIO.bat").write_text(
        '@echo off\r\ncd /d "%~dp0"\r\nstart "" "CanonStyleStudio.exe"\r\n',encoding="ascii")
    manifest={"name":release_name,"version":PUBLIC_VERSION,"build_id":BUILD_ID,
              "created_utc":datetime.now(timezone.utc).isoformat(),"architecture":"Windows x64",
              "python_required":False,"pse_required_for_canon_raw":True,
              "canon_resources_bundled":False,"entrypoint":"CanonStyleStudio.exe","distribution":"public",
              "camera_install":{"method":"target-PF3-scoped EdsCFParse acceptance correction; EOS Utility compiles and sends its original camera-native payload unchanged after live validation","model_specific_builders":False,"edsdk_payload_replaced":False,"edsdk_arguments_modified":False,"unvalidated_write_blocked_before_original_call":True,"compiler_symbol_resolution":"semantic signatures","validation":"live target PF3 plus exact compiler-to-EDSDK buffer comparison","offline_validated_transactions":["EOS 1300D / 16744","EOS RP / 16752","EOS R8 / 83076"],"physical_revalidation_required":True,"external_selftest_assets_required":False,"support_assets_bundled":False},
              "portable_storage":{"settings":"app_data","camera_exports":"Documents/Canon Style Studio PF3","camera_logs":"app_data/logs/camera_install","style_format":"single .canonstyleproject archive"}}
    manifest['independent_camera_install']={
        'method':'independent PF3 compiler and isolated Windows WPD session',
        'experimental':True,'physical_validation':['EOS RP / NC and Aerochrome / User Def. 3','EOS RP / Aerochrome / User Def. 2 / RC5 readback and user visual confirmation'],
        'scope':'reconstructed serializer families, live descriptor/slot grammar, matching Basic controls',
        'known_basic_updates_enabled_in_editor':False,
        'known_basic_updates_physically_validated':False,
        'canon_runtime_required':False,'clean_windows_machine_tested':False,
        'timeout_seconds':45,'automatic_retry':False,'canon_workflow_retained':True}
    from camera_install.camera_families_reference import CAMERA_FAMILIES,FAMILY_SIZES
    manifest['independent_camera_install'].update(
        known_compiler_identifiers=len(CAMERA_FAMILIES),serializer_families=len(FAMILY_SIZES),
        modern_format_negotiation=True,other_bodies_physically_validated=False)
    manifest['primary_camera_workflow']='independent USB; direct camera and User Def. 1–3 selection'
    manifest['bundled_basic_pf3']={'count':6,'first_run_reference_required':False,'sha256':BASIC_PF3_SHA256}
    manifest['independent_raw_decoder']=decoder
    manifest['optional_sample_images']='user-operated private Qt browser; source and author preserved'
    manifest['distribution']='local validation candidate; not approved for publication'
    (release/"STANDALONE_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    problems=audit(release)
    if problems:raise RuntimeError("Standalone audit found forbidden files:\n"+"\n".join(problems))
    audit_modules(release/'CanonStyleStudio.exe')
    if folder_only:
        print(f"[PASS] {release}")
        print("[PASS] Public folder only; no ZIP generated")
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
    parser.add_argument("--folder-only",action="store_true")
    args=parser.parse_args(argv);build(args.output_root,folder_only=args.folder_only);return 0


if __name__=="__main__":raise SystemExit(main())
