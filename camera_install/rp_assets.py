from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from canon_runtime import application_root


class RpAssetError(RuntimeError):
    pass


# These hashes identify the physically validated Manual Loader v2.4 research
# fixtures without redistributing any of their bytes in Canon Style Studio.
# Public builds require the user to locate a compatible support folder.
ASSET_SPECS = {
    "selftest_pf3": (
        "SELFTEST/SUPERIA_SELFTEST.pf3", 434_511,
        "c1167362652535e9d591689fa82c53a6bf03e2fecad4dedb6c1dcf22fd26f860",
    ),
    "selftest_block": (
        "SELFTEST/SUPERIA_EXPECTED_BLOCK_8192.bin", 8_192,
        "803efd8609e43d7c1fd612513539ce26c5d2e00304a1a6429bf1003f01b9de1c",
    ),
    "rp_carrier": (
        "REFERENCE/RP_SUPERIA_TEMPLATE_16752.bin", 16_752,
        "68c971e8fd62b626eb3d97df889060018e546c282e20a53e6dfb028bbe51edc6",
    ),
    "camera_id": (
        "REFERENCE/1300D_CAMERA_ID.bin", 4,
        "898b7b827df342c282579b0cc635d75601af4fa5d6a78f7309b8e40a4051730c",
    ),
    "descriptor": (
        "REFERENCE/1300D_DESCRIPTOR_7772.bin", 7_772,
        "649693d61f816ddeda7b1b2ee2ba1421a92d593efe96ed2f9ba218f162b6b3f0",
    ),
}

BASE_PF3_FILES = (
    "SOURCE/BASE_STANDARD_RP.pf3",
    "SOURCE/BASE_PORTRAIT_RP.pf3",
    "SOURCE/BASE_LANDSCAPE_RP.pf3",
    "SOURCE/BASE_NEUTRAL_RP.pf3",
    "SOURCE/BASE_FAITHFUL_RP.pf3",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class RpAssetSet:
    root: Path
    selftest_pf3: Path
    selftest_block: Path
    rp_carrier: Path
    camera_id: Path
    descriptor: Path
    hashes: dict[str, str]

    def read_selftest_block(self) -> bytes:
        return self.selftest_block.read_bytes()

    def read_carrier(self) -> bytes:
        return self.rp_carrier.read_bytes()


def _candidate_roots(selected: Path):
    selected = selected.resolve()
    values = [selected]
    if selected.name.upper() in {"SELFTEST", "REFERENCE", "SOURCE", "TOOLS"}:
        values.append(selected.parent)
    values.extend((selected / "CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE",))
    seen = set()
    for value in values:
        key = str(value).lower()
        if key not in seen:
            seen.add(key)
            yield value


def validate_rp_asset_folder(folder) -> RpAssetSet:
    selected = Path(folder)
    if not selected.is_dir():
        raise RpAssetError("Select the Manual Loader v2.4 support folder.")

    errors = []
    for root in _candidate_roots(selected):
        paths = {}
        hashes = {}
        try:
            for key, (relative, expected_size, expected_hash) in ASSET_SPECS.items():
                path = root / Path(relative)
                if not path.is_file():
                    raise RpAssetError(f"Missing support fixture: {relative}")
                size = path.stat().st_size
                if size != expected_size:
                    raise RpAssetError(f"Invalid {relative}: {size} bytes, expected {expected_size}")
                digest = _sha256(path)
                if digest.lower() != expected_hash.lower():
                    raise RpAssetError(f"Hash mismatch for {relative}; camera installation is blocked")
                paths[key] = path
                hashes[key] = digest
            return RpAssetSet(root=root, hashes=hashes, **paths)
        except RpAssetError as exc:
            errors.append(str(exc))
    raise RpAssetError(errors[-1] if errors else "The EOS RP support fixtures were not found.")


def discover_rp_assets(configured=None, app_root=None) -> RpAssetSet | None:
    """Controlled discovery; never scans an entire user profile or drive."""
    if app_root is None:
        app_root = application_root()
    app_root = Path(app_root).resolve()
    package_name = "CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE"
    # An explicit environment override wins; otherwise the copy travelling with
    # the app wins over a remembered absolute path from another machine/folder.
    candidates = [os.environ.get("CANON_STYLE_STUDIO_RP_ASSETS")]
    portable = app_root / "camera_support"
    if portable.is_dir():
        candidates.append(portable)
        try:
            for child in sorted(portable.iterdir()):
                if child.is_dir():
                    candidates.extend((child, child / package_name))
        except OSError:
            pass
    candidates.append(configured)
    for root in (app_root, app_root.parent, Path.cwd().resolve()):
        candidates.extend((
            root / package_name,
            root / "_MANUAL_LOADER_V2_4_ANALYSIS" / package_name,
        ))
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        try:return validate_rp_asset_folder(candidate)
        except (RpAssetError, OSError):pass
    return None


def import_rp_support_folder(folder, destination_parent) -> RpAssetSet:
    """Copy the allow-listed support set into portable app storage without deleting its source."""
    source = validate_rp_asset_folder(folder)
    source_files = {relative: source.root / Path(relative) for relative, *_ in ASSET_SPECS.values()}
    source_files.update({relative: source.root / Path(relative) for relative in BASE_PF3_FILES})
    missing = [relative for relative, path in source_files.items() if not path.is_file()]
    if missing:
        raise RpAssetError("Manual Loader folder is incomplete; missing: " + ", ".join(missing))
    identity = hashlib.sha256()
    for relative, path in sorted(source_files.items()):
        identity.update(relative.encode("utf-8"))
        identity.update(bytes.fromhex(_sha256(path)))
    package_name = "CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE"
    root = Path(destination_parent).resolve() / identity.hexdigest()[:24] / package_name
    for relative, source_path in source_files.items():
        target = root / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.stat().st_size == source_path.stat().st_size and _sha256(target) == _sha256(source_path):
            continue
        temp = target.with_suffix(target.suffix + ".tmp")
        shutil.copyfile(source_path, temp)
        temp.replace(target)
    return validate_rp_asset_folder(root)


def import_rp_support_zip(zip_path, destination_parent) -> RpAssetSet:
    """Import only the allow-listed Manual Loader files from a user-owned ZIP.

    Canon Style Studio never distributes these captured/Canon-derived fixtures.
    This helper merely makes a local, hash-validated copy from a package the user
    already owns. No arbitrary archive path is extracted.
    """
    zip_path = Path(zip_path).resolve()
    if not zip_path.is_file() or zip_path.suffix.lower() != ".zip":
        raise RpAssetError("Select CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE.zip")
    archive_digest = _sha256(zip_path)
    destination_parent = Path(destination_parent).resolve()
    root = destination_parent / archive_digest[:24] / "CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE"
    required = [value[0] for value in ASSET_SPECS.values()]
    wanted = tuple(required) + BASE_PF3_FILES
    with zipfile.ZipFile(zip_path, "r") as archive:
        matches = {}
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/").strip("/")
            for relative in wanted:
                if normalized.lower().endswith("/" + relative.lower()) or normalized.lower() == relative.lower():
                    if relative in matches:
                        raise RpAssetError(f"Duplicate support file in ZIP: {relative}")
                    matches[relative] = info
        missing = [relative for relative in wanted if relative not in matches]
        if missing:
            raise RpAssetError("Manual Loader ZIP is incomplete; missing: " + ", ".join(missing))
        for relative in wanted:
            info = matches[relative]
            expected_size = next((spec[1] for spec in ASSET_SPECS.values() if spec[0] == relative), 434_511)
            if info.file_size != expected_size:
                raise RpAssetError(f"Invalid {relative}: {info.file_size} bytes, expected {expected_size}")
            payload = archive.read(info)
            expected_hash = next((spec[2] for spec in ASSET_SPECS.values() if spec[0] == relative), None)
            if expected_hash and hashlib.sha256(payload).hexdigest().lower() != expected_hash.lower():
                raise RpAssetError(f"Hash mismatch for {relative}; camera installation is blocked")
            target = root / Path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_suffix(target.suffix + ".tmp")
            temp.write_bytes(payload)
            temp.replace(target)
    return validate_rp_asset_folder(root)
