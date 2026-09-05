from __future__ import annotations
import json, os, copy, hashlib, re, zipfile
from pathlib import Path
from dataclasses import dataclass, field, asdict

from canon_runtime import app_data_dir, legacy_app_data_dir
from creative_controls import DEFAULT_CREATIVE_CONTROLS, DEFAULT_RECIPE_WB

APP_DIR_NAME = "CanonStyleStudio"
PORTABLE_FORMAT = "canon-style-studio-portable-project"
PORTABLE_FORMAT_VERSION = 1
MAX_LUT_FILES = 128
MAX_LUT_BYTES = 256 * 1024 * 1024
MAX_TOTAL_LUT_BYTES = 1024 * 1024 * 1024
MAX_PROJECT_JSON_BYTES = 8 * 1024 * 1024


def app_config_dir():
    return app_data_dir()


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else app_config_dir() / "settings.json"
        self.data = {
            "last_lut_folder": "",
            "last_image_folder": "",
            "last_export_folder": "",
            "last_project_folder": "",
            "last_pf3_folder": "",
            "last_dll_folder": "",
            "manual_pse_path": "",
            "base_pf3_folder": "",
            "camera_assets_folder": "",
        }
        self.load()

    def load(self):
        # One-way, non-destructive migration from the former per-user settings.
        # The old file is never deleted and all future saves go beside the app.
        source = self.path
        if not source.is_file() and self.path == app_config_dir() / "settings.json":
            legacy = legacy_app_data_dir() / "settings.json"
            if legacy.is_file():
                source = legacy
        try:
            loaded = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                if source != self.path:
                    self.save()
        except Exception:
            pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def get_folder(self, key, fallback):
        p = Path(self.data.get(key, "")) if self.data.get(key) else None
        if p and p.exists() and p.is_dir():
            return p
        return Path(fallback)

    def remember_file(self, key, file_path):
        try:
            self.data[key] = str(Path(file_path).resolve().parent)
            self.save()
        except Exception:
            pass


@dataclass
class EditState:
    base_name: str = "Neutral"
    basePictureStyle: str = "Neutral"
    baseTemplateSource: str = ""
    base_path: str = ""
    custom_pf3: str = ""
    contrast: int = 0
    saturation: int = 0
    color_tone: int = 0
    sharpness_override: bool = False
    sharp_strength: int = 0
    fineness: int = 2
    threshold: int = 4
    raw_wb_mode: str = "As Shot"
    raw_kelvin: int = 5200
    raw_exposure: float = 0.0
    raw_shot_index: int = 0
    wb_ab_shift: int = 0
    wb_gm_shift: int = 0
    custom_wb_mult: list | None = None
    preview_quality_mode: str = "working"
    recipe_wb: dict = field(default_factory=lambda: copy.deepcopy(DEFAULT_RECIPE_WB))
    creative: dict = field(default_factory=lambda: copy.deepcopy(DEFAULT_CREATIVE_CONTROLS))
    luts: list = field(default_factory=list)


@dataclass
class ProjectDocument:
    version: int = 5
    name: str = "Untitled"
    edit: dict = field(default_factory=lambda: asdict(EditState()))
    references: list = field(default_factory=list)
    current_reference: int = 0
    compare_mode: str = "Side by side"
    zoom: float = 1.0
    pan_x: float = 0.5
    pan_y: float = 0.5
    split: float = 0.5
    snapshots: dict = field(default_factory=lambda: {"A": None, "B": None, "C": None})
    referenceHints: list = field(default_factory=list)
    portableWarnings: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        obj = cls()
        for k in obj.to_dict().keys():
            if k in d:
                setattr(obj, k, d[k])
        return obj


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_asset_name(name):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(str(name)).name).strip("._")
    return (name[:120] or "lut.cube")


def _iter_edit_states(data):
    edit = data.get("edit")
    if isinstance(edit, dict):
        yield edit
    snapshots = data.get("snapshots")
    if isinstance(snapshots, dict):
        for state in snapshots.values():
            if isinstance(state, dict):
                yield state


def _portable_project_data(project):
    """Return sanitized project JSON plus deduplicated LUT asset descriptions."""
    data = copy.deepcopy(project.to_dict())
    data["version"] = max(5, int(data.get("version", 1)))
    references = data.get("references") or []
    hints = []
    for value in references:
        p = Path(str(value))
        hint = {"name": p.name}
        try:
            if p.is_file():
                hint.update({"size": p.stat().st_size, "extension": p.suffix.lower()})
        except OSError:
            pass
        hints.append(hint)
    data["referenceHints"] = hints
    data["references"] = []
    data["current_reference"] = 0
    data["portableWarnings"] = list(data.get("portableWarnings") or [])

    assets = {}
    for state in _iter_edit_states(data):
        # Canon resources are discovered from the user's local Canon installation.
        # Never copy a selected/generated PF3 or leak its machine-specific path.
        if "base_path" in state:
            state["base_path"] = ""
        if "custom_pf3" in state:
            state["custom_pf3"] = ""
        if (state.get("basePictureStyle") or state.get("base_name")) == "Imported PF3":
            state["portableWarning"] = "Imported PF3 was not embedded; select it again on this computer."
            state["portableOriginalBasePictureStyle"] = "Imported PF3"
            state["basePictureStyle"] = "Neutral"
            state["base_name"] = "Neutral"
            warning = "An Imported PF3 was not embedded; Neutral is used until that PF3 is selected again."
            if warning not in data["portableWarnings"]:
                data["portableWarnings"].append(warning)
        for item in state.get("luts") or []:
            if not isinstance(item, dict):
                continue
            source = Path(str(item.get("path") or ""))
            if not source.is_file():
                raise FileNotFoundError(f"LUT required by the project was not found: {source}")
            size = source.stat().st_size
            if size > MAX_LUT_BYTES:
                raise ValueError(f"LUT is too large to embed ({size} bytes): {source.name}")
            digest = _sha256_file(source)
            suffix = source.suffix.lower() or ".lut"
            archive_path = f"luts/{digest[:16]}_{_safe_asset_name(source.stem)}{suffix}"
            if digest not in assets:
                assets[digest] = {
                    "sha256": digest,
                    "size": size,
                    "name": source.name,
                    "archivePath": archive_path,
                    "source": source,
                }
            item["path"] = ""
            item["portableAsset"] = digest
    if len(assets) > MAX_LUT_FILES:
        raise ValueError(f"Project contains too many LUT files ({len(assets)}; maximum {MAX_LUT_FILES})")
    total = sum(asset["size"] for asset in assets.values())
    if total > MAX_TOTAL_LUT_BYTES:
        raise ValueError(f"Embedded LUT data is too large ({total} bytes; maximum {MAX_TOTAL_LUT_BYTES})")
    return data, assets


def save_project(path, project: ProjectDocument):
    """Save a portable .canonstyleproject ZIP with all current/snapshot LUT files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data, assets = _portable_project_data(project)
    public_assets = [{k: v for k, v in asset.items() if k != "source"} for asset in assets.values()]
    manifest = {
        "format": PORTABLE_FORMAT,
        "formatVersion": PORTABLE_FORMAT_VERSION,
        "projectVersion": data["version"],
        "photosEmbedded": False,
        "assets": public_assets,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("project.json", json.dumps(data, indent=2, ensure_ascii=False))
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            for asset in assets.values():
                archive.write(asset["source"], asset["archivePath"])
        tmp.replace(path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _safe_zip_member(name):
    normalized = str(name).replace("\\", "/")
    parts = normalized.split("/")
    return bool(normalized) and not normalized.startswith("/") and not re.match(r"^[A-Za-z]:", normalized) and all(part not in ("", ".", "..") for part in parts)


def _load_portable_project(path, extraction_root=None):
    archive_hash = _sha256_file(path)
    root = Path(extraction_root) if extraction_root else app_config_dir() / "portable_projects"
    destination = root / archive_hash[:24]
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if len(infos) > MAX_LUT_FILES + 2:
            raise ValueError("Portable project contains too many files")
        if any(not _safe_zip_member(info.filename) for info in infos):
            raise ValueError("Portable project contains an unsafe archive path")
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError("Portable project contains duplicate archive paths")
        names = {info.filename for info in infos}
        if not {"project.json", "manifest.json"}.issubset(names):
            raise ValueError("Portable project is missing project.json or manifest.json")
        if archive.getinfo("project.json").file_size > MAX_PROJECT_JSON_BYTES or archive.getinfo("manifest.json").file_size > MAX_PROJECT_JSON_BYTES:
            raise ValueError("Portable project metadata exceeds the safety limit")
        manifest = json.loads(archive.read("manifest.json"))
        data = json.loads(archive.read("project.json"))
        if manifest.get("format") != PORTABLE_FORMAT or manifest.get("formatVersion") != PORTABLE_FORMAT_VERSION:
            raise ValueError("Unsupported portable project format")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or len(assets) > MAX_LUT_FILES:
            raise ValueError("Portable project has an invalid asset manifest")
        asset_map = {}
        asset_members = set()
        total = 0
        for asset in assets:
            if not isinstance(asset, dict):
                raise ValueError("Portable project has an invalid LUT asset")
            digest = str(asset.get("sha256") or "").lower()
            member = str(asset.get("archivePath") or "")
            size = int(asset.get("size", -1))
            if not re.fullmatch(r"[0-9a-f]{64}", digest) or not re.fullmatch(r"luts/[^/]+", member) or not _safe_zip_member(member):
                raise ValueError("Portable project has an invalid LUT asset identity")
            if digest in asset_map or member in asset_members:
                raise ValueError("Portable project contains a duplicate LUT asset identity")
            if member not in names or size < 0 or size > MAX_LUT_BYTES or archive.getinfo(member).file_size != size:
                raise ValueError(f"Portable LUT asset has an invalid size: {member}")
            total += size
            if total > MAX_TOTAL_LUT_BYTES:
                raise ValueError("Portable project LUT data exceeds the safety limit")
            payload = archive.read(member)
            if hashlib.sha256(payload).hexdigest() != digest:
                raise ValueError(f"Portable LUT asset failed SHA-256 validation: {member}")
            target = destination / "luts" / Path(member).name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.stat().st_size != size or _sha256_file(target) != digest:
                tmp = target.with_suffix(target.suffix + ".tmp")
                tmp.write_bytes(payload)
                tmp.replace(target)
            asset_map[digest] = str(target)
            asset_members.add(member)
        if names != {"project.json", "manifest.json", *asset_members}:
            raise ValueError("Portable project contains files not declared in its manifest")
    for state in _iter_edit_states(data):
        for item in state.get("luts") or []:
            if not isinstance(item, dict):
                continue
            digest = str(item.pop("portableAsset", ""))
            if digest not in asset_map:
                raise ValueError("Portable project references a missing LUT asset")
            item["path"] = asset_map[digest]
    return ProjectDocument.from_dict(data)


def load_project(path, extraction_root=None):
    path = Path(path)
    if zipfile.is_zipfile(path):
        return _load_portable_project(path, extraction_root=extraction_root)
    # Backward compatibility with the original plain-JSON project format.
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectDocument.from_dict(data)


class HistoryManager:
    def __init__(self, max_items=100):
        self.max_items = max_items
        self.items = []
        self.index = -1

    @staticmethod
    def _norm(state):
        return json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def reset(self, state):
        self.items = [copy.deepcopy(state)]
        self.index = 0

    def push(self, state):
        if self.index >= 0 and self._norm(self.items[self.index]) == self._norm(state):
            return
        self.items = self.items[:self.index+1]
        self.items.append(copy.deepcopy(state))
        if len(self.items) > self.max_items:
            self.items.pop(0)
        self.index = len(self.items)-1

    def can_undo(self): return self.index > 0
    def can_redo(self): return 0 <= self.index < len(self.items)-1
    def undo(self):
        if not self.can_undo(): return None
        self.index -= 1
        return copy.deepcopy(self.items[self.index])
    def redo(self):
        if not self.can_redo(): return None
        self.index += 1
        return copy.deepcopy(self.items[self.index])
