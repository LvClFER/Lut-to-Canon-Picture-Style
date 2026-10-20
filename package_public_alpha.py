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

from canon_runtime import BUILD_ID, PUBLIC_VERSION, BASIC_PF3_SHA256


HERE=Path(__file__).resolve().parent
PACKAGE_NAME=f"CanonStyleStudio_{PUBLIC_VERSION}_Source"
FILES=(
    "canon_style_studio.py","canon_engine.py","canon_dpp_worker.py","dpp_client.py","sample_images.py","sample_browser.py","nikon_np3.py",
    "project_state.py","render_geometry.py","canon_runtime.py","creative_controls.py","test_report.py",
    "bootstrap.py","launch_guard.py","START_CANON_STYLE_STUDIO.bat","requirements.txt",
    "build_macos.py","build_standalone.py","MACOS_PORT_STATUS.md","assets/canon-logo.png","assets/step-up.svg","assets/step-down.svg",
    "SELF_TEST.py","REGRESSION_TESTS.py","PUBLIC_ALPHA_REGRESSION.py",
    "README.md","TESTING_GUIDE.md","PUBLIC_ALPHA_RELEASE_NOTES.md","ARCHITECTURE_STATUS.md","CAMERA_COMPATIBILITY.md",
    "camera_install/__init__.py","camera_install/rp_assets.py","camera_install/rp_payload.py",
    "camera_install/eos_hook.py","camera_install/ui.py",
    "camera_install/dynamic_camera_agent.js","PF3_UI_EXPORT_TEST.py",
    "camera_install/identity_pf3_bootstrap_reference.py","camera_install/pf3_source_reference.py",
    "camera_install/camera_families_reference.py","camera_install/family_registration_reference.py",
    "camera_install/legacy_dense9_carrier_reference.py","camera_install/legacy_dense9_reference.py",
    "camera_install/packed9_reference.py",
    "research/PF3_REFERENCE_BANK_CALLBACKS_20261018.md",
    "camera_install/cipher_stream_reference.py","camera_install/cipher_known_plaintext_reference.py",
    'camera_install/accepted_modern_reference.py',
    'camera_install/axis_composition_reference.py',
    'camera_install/cached_curve_reference.py',
    'camera_install/canon_event_receive_reference.py',
    'camera_install/canon_events.py',
    'camera_install/color_math_reference.py',
    'camera_install/compact_branch_reference.py',
    'camera_install/compact_cache_reference.py',
    'camera_install/compact_carrier_reference.py',
    'camera_install/compact_grid_reference.py',
    'camera_install/compact_header_reference.py',
    'camera_install/compact_legacy_grid_reference.py',
    'camera_install/compact_pixel_reference.py',
    'camera_install/compiler_input_events_reference.py',
    'camera_install/control_section_reference.py',
    'camera_install/curve_bspline_research.py',
    'camera_install/curve_finalization_research.py',
    'camera_install/curve_normalization_research.py',
    'camera_install/d170_decode_reference.py',
    'camera_install/default_axis_reference.py',
    'camera_install/dense17_reference.py',
    'camera_install/descriptor_capability_reference.py',
    'camera_install/descriptor_import_reference.py',
    'camera_install/event_mode_plan_reference.py',
    'camera_install/family_preflight_reference.py',
    'camera_install/float_lab_reference.py',
    'camera_install/full33_packing_reference.py',
    'camera_install/gamut_policy_reference.py',
    'camera_install/independent_registration_reference.py',
    'camera_install/independent_session_diagnostic.py',
    'camera_install/integer_tetrahedral_reference.py',
    'camera_install/lab_math_reference.py',
    'camera_install/legacy_axis_geometry_reference.py',
    'camera_install/legacy_axis_reference.py',
    'camera_install/legacy_grid_reference.py',
    'camera_install/legacy_sector_reference.py',
    'camera_install/legacy_six_axis_reference.py',
    'camera_install/modern_composition_reference.py',
    'camera_install/modern_grid_reference.py',
    'camera_install/modern_header_reference.py',
    'camera_install/mtp_read_reference.py',
    'camera_install/mtp_write_reference.py',
    'camera_install/offline_registration_reference.py',
    'camera_install/packed10_reference.py',
    'camera_install/packed17_reference.py',
    'camera_install/polynomial_color_reference.py',
    'camera_install/ptp_device_info_reference.py',
    'camera_install/ptp_wire.py',
    'camera_install/macos_discovery.py',
    'camera_install/macos_ptp.py',
    'camera_install/connection_profile.py',
    'camera_install/registration_encode_reference.py',
    'camera_install/registration_sequence_reference.py',
    'camera_install/remote_session_reference.py',
    'camera_install/rp_preflight_reference.py',
    'camera_install/session_inputs_reference.py',
    'camera_install/state_send_plan_reference.py',
    'camera_install/style_confirmation_reference.py',
    'camera_install/style_readback_reference.py',
    'camera_install/style_send_plan_reference.py',
    'camera_install/tail_settings_reference.py',
    'camera_install/typed_record_reference.py',
    'camera_install/windows_wpd_probe.py',
    'camera_install/wpd_command_sender.py',
    'camera_install/wpd_connection.py',
    'camera_install/wpd_data_phase_reference.py',
    'independent_camera_diagnostic.py',
)
EXAMPLES=("example_luts/hald_identity_8.png","example_luts/Lightroom_Hald_Template_512_64cube_sRGB_16bit.tif")
BASIC_FILES=tuple('basic_pf3/'+name for name in BASIC_PF3_SHA256)
FORBIDDEN_SUFFIXES={".bin",".dll",".exe",".icc",".icm",".pf3",".cr2",".cr3",".crw",".dmp",".log",".pyc"}
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
        approved=rel.as_posix() in BASIC_FILES and sha(path)==BASIC_PF3_SHA256[path.name]
        if path.suffix.lower() in FORBIDDEN_SUFFIXES and not approved:problems.append(f"forbidden extension: {rel}")
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
    for name in (*FILES,*EXAMPLES,*BASIC_FILES):
        source=HERE/name
        if not source.is_file():raise FileNotFoundError(f"Required public file missing: {name}")
        target=package/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);copied.append(target)
    manifest={"name":PACKAGE_NAME,"version":PUBLIC_VERSION,"build_id":BUILD_ID,"created_utc":datetime.now(timezone.utc).isoformat(),
              "legal":"Includes six authorized application-generated basic PF3 files; no Canon DLL, executable, ICC/ICM, RAW, descriptor or captured payload.",
              "camera_install":{"workflow":"optional Canon-native fallback","physically_tested_bodies":["EOS RP","EOS R8"],"external_support_assets_required":False,"support_assets_bundled":False,"unvalidated_write_blocked_before_original_call":True,"validation":"live target PF3 plus exact compiler-to-EDSDK buffer comparison"},
              "independent_camera_install":{"canon_runtime_required":False,"serializer_families":10,"catalogued_model_ids":77,"physically_tested_bodies":["EOS RP"],"other_bodies_physically_validated":False,"validation":"live advertised operations, descriptor, slot format and exact requested-content readback; see CAMERA_COMPATIBILITY.md"},
              "portable_storage":{"settings":"app_data","camera_exports":"Documents/Canon Style Studio PF3","camera_logs":"app_data/logs/camera_install","style_format":"single .canonstyleproject archive"},
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
        bad=[n for n in archive.namelist() if Path(n).name.lower() in FORBIDDEN_NAMES or (Path(n).suffix.lower() in FORBIDDEN_SUFFIXES and '/'.join(Path(n).parts[1:]) not in BASIC_FILES) or any(part.lower() in FORBIDDEN_PARTS for part in Path(n).parts)]
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
