from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from canon_runtime import sanitize_path, sanitize_text


def sanitize_value(value):
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, Path):
        return sanitize_path(value)
    if isinstance(value, str):
        return sanitize_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(value)


def tail_sanitized_file(path: Path | None, max_bytes=256_000) -> str:
    if not path or not Path(path).is_file():
        return ""
    data=Path(path).read_bytes()[-max_bytes:]
    return sanitize_text(data.decode("utf-8",errors="replace"))


def _json_bytes(value) -> bytes:
    return json.dumps(sanitize_value(value),indent=2,ensure_ascii=False,sort_keys=True).encode("utf-8")


def create_test_report_zip(output_path, report, settings_snapshot, recent_logs=None,
                           backend_log=None, startup_log=None, source_raw=None,
                           include_source_raw=False):
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    report=dict(report)
    report["created_utc"]=datetime.now(timezone.utc).isoformat()
    report["source_raw_included"]=bool(include_source_raw and source_raw)
    report["privacy"]={
        "personal_paths_sanitized":True,
        "usernames_sanitized":True,
        "source_raw_default":False,
    }
    backend_text=tail_sanitized_file(backend_log)
    startup_text=tail_sanitized_file(startup_log)
    internal_text="\n".join(sanitize_text(line) for line in (recent_logs or [])[-200:])
    temp=output_path.with_suffix(output_path.suffix+".tmp")
    with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr("report.json",_json_bytes(report))
        archive.writestr("settings_snapshot.json",_json_bytes(settings_snapshot))
        archive.writestr("backend.log",backend_text)
        archive.writestr("startup.log",startup_text)
        archive.writestr("recent_internal.log",internal_text)
        if include_source_raw and source_raw:
            raw=Path(source_raw)
            if not raw.is_file():
                raise FileNotFoundError(f"Source RAW no longer exists: {raw.name}")
            archive.write(raw,f"source/{raw.name}")
    temp.replace(output_path)
    validate_test_report_zip(output_path,allow_raw=bool(include_source_raw and source_raw))
    return output_path


def validate_test_report_zip(path,allow_raw=False):
    path=Path(path)
    required={"report.json","settings_snapshot.json","backend.log","startup.log","recent_internal.log"}
    with zipfile.ZipFile(path,"r") as archive:
        names=set(archive.namelist())
        missing=required-names
        if missing:raise ValueError(f"Test report is missing: {sorted(missing)}")
        raw_members=[name for name in names if name.lower().endswith((".cr2",".cr3",".crw",".cip",".crn"))]
        if raw_members and not allow_raw:raise ValueError("A source RAW was included without explicit permission.")
        username=(os.environ.get("USERNAME") or "").lower()
        for name in required:
            data=archive.read(name).decode("utf-8",errors="replace")
            if username and username in data.lower():raise ValueError(f"Unsanitized username found in {name}.")
    return True
