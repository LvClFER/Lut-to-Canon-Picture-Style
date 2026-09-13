from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


APP_NAME = "CanonStyleStudio"
PUBLIC_NAME = "Canon Style Studio Public Alpha"
PUBLIC_VERSION = "1.0.0-alpha.23"
BUILD_ID = "2026-09-13-EOS-UTILITY-CANON-NATIVE-ALPHA-23"


def application_root() -> Path:
    """Writable portable root: executable folder when frozen, source folder in development."""
    override = os.environ.get("CANON_STYLE_STUDIO_PORTABLE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def legacy_app_data_dir() -> Path:
    """Previous per-user location, retained for read-only migration only."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    return (Path(base) if base else Path.home() / ".canon_style_studio") / APP_NAME


def app_data_dir() -> Path:
    path = application_root() / "app_data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exported_styles_dir() -> Path:
    path = application_root() / "exported_styles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def camera_support_dir() -> Path:
    path = application_root() / "camera_support"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    path = app_data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def windows_file_version(path: Path) -> str | None:
    if os.name != "nt":
        return None
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(str(path), 0, size, buffer):
            return None
        value = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not ctypes.windll.version.VerQueryValueW(buffer, "\\", ctypes.byref(value), ctypes.byref(length)):
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint32) for name in (
                "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS",
                "dwProductVersionMS", "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags",
                "dwFileOS", "dwFileType", "dwFileSubtype", "dwFileDateMS", "dwFileDateLS",
            )]

        info = ctypes.cast(value, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        return ".".join(str(x) for x in (
            info.dwFileVersionMS >> 16,
            info.dwFileVersionMS & 0xFFFF,
            info.dwFileVersionLS >> 16,
            info.dwFileVersionLS & 0xFFFF,
        ))
    except Exception:
        return None


@dataclass(frozen=True)
class CanonInstallation:
    pse_dir: Path
    pse_exe: Path
    dpp4lib_dir: Path
    dppcore_dll: Path
    edscfparse_dll: Path | None
    pse_version: str | None
    dppcore_version: str | None

    def to_dict(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Path):
                data[key] = str(value)
        return data


def normalize_pse_dir(candidate: str | os.PathLike | None) -> Path | None:
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if path.is_file():
        if path.name.lower() == "dppcore.dll" and path.parent.name.lower() == "dpp4lib":
            path = path.parent.parent
        else:
            path = path.parent
    if path.name.lower() == "dpp4lib":
        path = path.parent
    try:
        return path.resolve()
    except Exception:
        return path


def installation_from_dir(candidate: str | os.PathLike | None) -> CanonInstallation | None:
    root = normalize_pse_dir(candidate)
    if root is None:
        return None
    pse = root / "PSEditor.exe"
    dppdir = root / "DPP4Lib"
    dppcore = dppdir / "DppCore.dll"
    if not (pse.is_file() and dppcore.is_file()):
        return None
    eds = root / "EdsCFParse.dll"
    if not eds.is_file():
        alternative = dppdir / "EdsCFParse.dll"
        eds = alternative if alternative.is_file() else None
    return CanonInstallation(
        pse_dir=root,
        pse_exe=pse,
        dpp4lib_dir=dppdir,
        dppcore_dll=dppcore,
        edscfparse_dll=eds,
        pse_version=windows_file_version(pse),
        dppcore_version=windows_file_version(dppcore),
    )


def _controlled_canon_roots() -> list[Path]:
    roots = []
    for env_name, fallback in (("ProgramFiles", r"C:\Program Files"),
                               ("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        base = Path(os.environ.get(env_name, fallback)) / "Canon"
        if base.is_dir() and base not in roots:
            roots.append(base)
    return roots


def discover_pse(manual_path: str | os.PathLike | None = None) -> CanonInstallation | None:
    candidates: list[Path] = []
    for value in (manual_path, os.environ.get("CANON_STYLE_STUDIO_PSE_DIR")):
        normalized = normalize_pse_dir(value)
        if normalized is not None and normalized not in candidates:
            candidates.append(normalized)
    for canon_root in _controlled_canon_roots():
        standard = canon_root / "Picture Style Editor"
        if standard not in candidates:
            candidates.append(standard)
    for candidate in candidates:
        found = installation_from_dir(candidate)
        if found:
            return found

    # Controlled fallback for versioned/alternative Canon layouts. Only directories
    # containing both PSEditor.exe and DPP4Lib/DppCore.dll are accepted.
    for canon_root in _controlled_canon_roots():
        try:
            for exe in canon_root.glob("**/PSEditor.exe"):
                try:
                    relative_depth = len(exe.parent.relative_to(canon_root).parts)
                except Exception:
                    continue
                if relative_depth > 5:
                    continue
                found = installation_from_dir(exe.parent)
                if found:
                    return found
        except OSError:
            continue
    return None


def validate_canon_scanner_profile(path: Path) -> bytes:
    data = Path(path).read_bytes()
    if len(data) < 132 or data[36:40] != b"acsp":
        raise ValueError("The selected Canon resource is not a valid ICC profile.")
    if data[12:16] != b"scnr" or data[48:52] != b"CANO":
        raise ValueError("The selected ICC is not a Canon scanner/input profile.")
    declared = int.from_bytes(data[:4], "big")
    if declared > len(data):
        raise ValueError("The Canon ICC profile is truncated.")
    return data


def ensure_runtime_input_profile(install: CanonInstallation, destination: Path | None = None) -> Path:
    """Copy a local PSE-owned input profile to the private runtime cache.

    NS.ICC was compared against the previous captured profile on IMG_2748.CR3:
    MAE 0.017, max channel delta 2. It is loaded from the user's own PSE install,
    never bundled or modified in place.
    """
    destination = Path(destination or (cache_dir() / "canon_input_profile.icc"))
    candidates = [
        install.dpp4lib_dir / "icc" / "NS.ICC",
        install.dpp4lib_dir / "icc" / "FDS.ICC",
        install.dpp4lib_dir / "icc" / "FS.ICC",
    ]
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        raise FileNotFoundError("No supported Canon input ICC was found in Picture Style Editor/DPP4Lib/icc.")
    source_bytes = validate_canon_scanner_profile(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file() or destination.read_bytes() != source_bytes:
        temp = destination.with_suffix(destination.suffix + ".tmp")
        temp.write_bytes(source_bytes)
        temp.replace(destination)
    metadata = {
        "source_name": source.name,
        "source_relative_to_pse": str(source.relative_to(install.pse_dir)),
        "bytes": len(source_bytes),
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
        "pse_version": install.pse_version,
        "dppcore_version": install.dppcore_version,
    }
    meta_path = destination.with_suffix(".json")
    temp_meta = meta_path.with_suffix(".json.tmp")
    temp_meta.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_meta.replace(meta_path)
    return destination


def runtime_environment(install: CanonInstallation | None, profile_path: Path | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    if install:
        env["CANON_STYLE_STUDIO_PSE_DIR"] = str(install.pse_dir)
    if profile_path:
        env["CANON_STYLE_STUDIO_PROFILE_PATH"] = str(profile_path)
    return env


def user_roots() -> list[Path]:
    roots = []
    for value in (Path.home(), os.environ.get("USERPROFILE"), os.environ.get("HOMEDRIVE", "") + os.environ.get("HOMEPATH", "")):
        if not value:
            continue
        try:
            path = Path(value).resolve()
        except Exception:
            path = Path(value)
        if str(path) and path not in roots:
            roots.append(path)
    return sorted(roots, key=lambda p: len(str(p)), reverse=True)


def sanitize_text(value: object) -> str:
    text = str(value or "")
    for root in user_roots():
        root_text = str(root)
        text = re.sub(re.escape(root_text), "<USER_PATH>", text, flags=re.IGNORECASE)
        text = re.sub(re.escape(root_text.replace("\\", "/")), "<USER_PATH>", text, flags=re.IGNORECASE)
    username = os.environ.get("USERNAME")
    if username:
        text = re.sub(re.escape(username), "<USER>", text, flags=re.IGNORECASE)
    return text


def sanitize_path(path: str | os.PathLike | None, keep_name: bool = True) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    name = candidate.name
    sanitized = sanitize_text(candidate)
    if "<USER_PATH>" in sanitized:
        return f"<USER_PATH>/{name}" if keep_name and name else "<USER_PATH>"
    return sanitized


def system_summary() -> dict:
    return {
        "windows": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "python_executable": sanitize_path(sys.executable),
        "architecture": platform.machine(),
    }


def copy_clean_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temp)
    temp.replace(destination)
