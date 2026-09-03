from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .rp_assets import RpAssetSet
from .rp_payload import (
    build_rp_payload, canon_style_name, extract_legacy_block1, sha256_bytes,
    split_legacy_blocks, validate_agent_source, validate_compiler_selftest,
)

try:
    import frida
except Exception:
    frida = None


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def _atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def find_eos_utility():
    candidates = []
    for key in ("ProgramFiles(x86)", "ProgramFiles"):
        base = Path(os.environ.get(key, ""))
        if str(base):
            candidates.extend((
                base / "Canon" / "EOS Utility" / "EU3" / "EOS Utility 3.exe",
                base / "Canon" / "EOS Utility 3" / "EOS Utility 3.exe",
            ))
    for path in candidates:
        if path.is_file():
            return path
    # Controlled fallback limited to Canon installation folders.
    for key in ("ProgramFiles(x86)", "ProgramFiles"):
        canon = Path(os.environ.get(key, "")) / "Canon"
        if not canon.is_dir():
            continue
        try:
            for path in canon.glob("**/EOS Utility 3.exe"):
                if path.is_file():
                    return path
        except OSError:
            pass
    return None


class EosRpInstaller:
    """Validated EOS RP coordinator.

    This class never emulates the registration transaction. It attaches to EOS
    Utility, verifies Canon's compiler byte-for-byte, then arms replacement of
    only the genuine 0x01000203 payload. 0x00000115 is observation-only in the
    immutable bundled agent.
    """

    def __init__(self, assets: RpAssetSet, event_callback=None, agent_path=None):
        if frida is None:
            raise RuntimeError("Frida is not installed in this runtime")
        self.assets = assets
        self.event_callback = event_callback or (lambda event: None)
        self.agent_path = Path(agent_path) if agent_path else Path(__file__).with_name("rp_loader_agent.js")
        self.agent_source = self.agent_path.read_text(encoding="utf-8")
        validate_agent_source(self.agent_source)
        self.device = None
        self.session = None
        self.script = None
        self.pid = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._report = None
        self._report_path = None
        self.armed = False

    @staticmethod
    def _candidate(process):
        name = str(getattr(process, "name", "") or "").lower()
        return "eos utility 3" in name or name == "eos utility 3.exe"

    def _emit(self, event):
        payload = dict(event or {})
        payload.setdefault("timestamp", _utc_now())
        try:
            self.event_callback(payload)
        except Exception:
            pass

    def _save_report(self):
        with self._lock:
            if self._report is not None and self._report_path is not None:
                _atomic_json(self._report_path, self._report)

    def _on_message(self, message, data):
        if message.get("type") != "send":
            self._emit({"type": "frida_error", "error": str(message)})
            return
        event = dict(message.get("payload") or {})
        raw = bytes(data) if data else b""
        kind = event.get("type")
        if raw:
            event["binarySize"] = len(raw)
            event["binarySha256"] = sha256_bytes(raw)
        with self._lock:
            if self._report is not None:
                # Reports store hashes and sizes, never outgoing/control bytes.
                self._report.setdefault("events", []).append(dict(event))
                if kind == "payload_patched" and raw:
                    self._report["actualOutgoingPayloadSha256"] = sha256_bytes(raw)
                if kind == "install_success":
                    self.armed = False
                    self._report["status"] = "SUCCESS"
                    self._report["completedAt"] = _utc_now()
                elif kind == "install_error":
                    self._report["status"] = "ERROR"
                    self._report["error"] = event.get("reason")
                try:self._save_report()
                except Exception:pass
        if kind == "ready":
            self._ready.set()
        elif kind == "armed":
            self.armed = True
        self._emit(event)

    def _attach(self, process):
        if self.session is not None:
            return
        session = self.device.attach(process.pid)
        script = session.create_script(self.agent_source)
        script.on("message", self._on_message)
        script.load()
        self.session = session
        self.script = script
        self.pid = process.pid
        self._emit({"type": "attached", "pid": process.pid, "process": process.name})

    def connect(self, timeout=35.0, launch_if_missing=True):
        if self._stop.is_set():
            raise RuntimeError("Camera installation was cancelled")
        self.device = self.device or frida.get_local_device()
        launch_attempted = False
        deadline = time.monotonic() + float(timeout)
        last_error = None
        while time.monotonic() < deadline and not self._stop.is_set():
            try:
                processes = self.device.enumerate_processes()
                match = next((p for p in processes if self._candidate(p)), None)
                if match is not None and self.session is None:
                    self._attach(match)
                if self._ready.wait(0.15):
                    return self.script
                if match is None and launch_if_missing and not launch_attempted:
                    launch_attempted = True
                    executable = find_eos_utility()
                    if executable:
                        subprocess.Popen([str(executable)], cwd=str(executable.parent))
                        self._emit({"type": "eos_started", "name": executable.name})
            except Exception as exc:
                last_error = exc
                time.sleep(0.15)
        if self._stop.is_set():
            raise RuntimeError("Camera installation was cancelled")
        detail = f" ({last_error})" if last_error else ""
        raise RuntimeError(
            "EOS Utility 3 with EdsCFParse/EDSDK was not ready. Connect the EOS RP, "
            f"open EOS Utility and try again{detail}"
        )

    def _compile(self, pf3_path: Path):
        if self.script is None:
            raise RuntimeError("EOS Utility compiler session is not connected")
        result = self.script.exports_sync.compile(
            str(Path(pf3_path).resolve()),
            self.assets.camera_id.read_bytes().hex(),
            self.assets.descriptor.read_bytes().hex(),
        )
        if not isinstance(result, (list, tuple)) or len(result) != 2:
            raise RuntimeError("Unexpected binary response from the Canon compiler")
        metadata, data = result
        return dict(metadata or {}), bytes(data or b"")

    def prepare_and_arm(self, pf3_path, slot, style_name, output_dir, launch_eos=True):
        pf3_path = Path(pf3_path).resolve()
        if not pf3_path.is_file() or pf3_path.stat().st_size != 434_511:
            raise RuntimeError("A validated 434,511-byte PF3 is required")
        with pf3_path.open("rb") as handle:
            header = handle.read(8)
        if len(header) < 7 or header[4:7] != b"PSP":
            raise RuntimeError("The camera-install input does not have a valid Canon PF3 header")
        slot = int(slot)
        if slot not in (1, 2, 3):
            raise RuntimeError("EOS RP User Def. slot must be 1, 2 or 3")
        style_name = canon_style_name(style_name, pf3_path.stem)
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        self._emit({"type": "stage", "message": "Connecting to EOS Utility 3…"})
        self.connect(timeout=35.0, launch_if_missing=bool(launch_eos))

        self._emit({"type": "stage", "message": "Running exact Canon compiler self-test…"})
        selftest_meta, selftest_legacy = self._compile(self.assets.selftest_pf3)
        if not selftest_meta.get("ok"):
            raise RuntimeError("Canon compiler rejected the known-good self-test PF3")
        selftest_hash = validate_compiler_selftest(
            selftest_legacy, self.assets.read_selftest_block()
        )
        self._emit({"type": "selftest_pass", "blockSha256": selftest_hash})

        self._emit({"type": "stage", "message": "Compiling current PF3 to exact 8192-byte Block1…"})
        target_meta, target_legacy = self._compile(pf3_path)
        if not target_meta.get("ok"):
            raise RuntimeError("Canon compiler could not compile the current PF3")
        # The validated V37 EOS RP recipe consumes exact legacy Block1 only.
        # Block1/Block2 equality is an oracle requirement for the self-test above,
        # not a requirement for a target PF3 (Standard commonly compiles unequal).
        block1 = extract_legacy_block1(target_legacy)
        _target_block1, target_block2 = split_legacy_blocks(target_legacy)
        payload = build_rp_payload(self.assets.read_carrier(), block1, style_name)

        block_path = output_dir / f"{pf3_path.stem}.RP_BLOCK1_8192.bin"
        payload_path = output_dir / f"{pf3_path.stem}.RP_PAYLOAD_16752.bin"
        report_path = output_dir / "EOS_RP_INSTALL_REPORT.json"
        _atomic_bytes(block_path, block1)
        _atomic_bytes(payload_path, payload)
        report = {
            "format": "CanonStyleStudio.EosRpInstallReport",
            "version": 1,
            "status": "ARMED",
            "createdAt": _utc_now(),
            "cameraCompatibility": "EOS RP only — physically validated",
            "rawCompatibilityDoesNotImplyCameraCompatibility": True,
            "sourcePf3": pf3_path.name,
            "sourcePf3Sha256": sha256_bytes(pf3_path.read_bytes()),
            "slot": slot,
            "pictureStyleName": style_name,
            "compilerSelfTest": {
                "exact": True, "blockSha256": selftest_hash, "meta": selftest_meta,
            },
            "targetCompiler": {
                "blockSha256": sha256_bytes(block1),
                "block2Sha256": sha256_bytes(target_block2),
                "duplicateBlocks": block1 == target_block2,
                "extractionPolicy": "validated V37 EOS RP carrier + exact legacy Block1",
                "carrierBlock2Preserved": True,
                "meta": target_meta,
            },
            "rpPayload": {
                "size": len(payload), "sha256": sha256_bytes(payload),
                "containsTwilight": b"TWILIGHT" in payload,
                "nameOffset8": payload[8:40].split(b"\x00", 1)[0].decode("ascii", "replace"),
                "nameOffset44": payload[44:76].split(b"\x00", 1)[0].decode("ascii", "replace"),
            },
            "cameraWritePolicy": {
                "patch203Payload": True, "patch115": False,
                "reason": "0x00000115 is opaque binary state/control data",
            },
            "fixtureHashes": dict(self.assets.hashes),
            "events": [],
        }
        with self._lock:
            self._report = report
            self._report_path = report_path
            self._save_report()

        self._emit({"type": "stage", "message": f"Arming User Def. {slot}…"})
        armed = self.script.exports_sync.arm(slot, payload.hex(), style_name)
        if not armed:
            raise RuntimeError("EOS Utility hook did not arm")
        self.armed = True
        return {
            "pf3": pf3_path,
            "slot": slot,
            "styleName": style_name,
            "blockPath": block_path,
            "payloadPath": payload_path,
            "reportPath": report_path,
            "blockSha256": sha256_bytes(block1),
            "payloadSha256": sha256_bytes(payload),
            "compilerSelfTestSha256": selftest_hash,
            "pid": self.pid,
        }

    def disarm(self):
        with self._lock:
            if self.script is not None:
                try:self.script.exports_sync.disarm()
                except Exception:pass
            self.armed = False
            if self._report is not None and self._report.get("status") == "ARMED":
                self._report["status"] = "DISARMED"
                self._report["completedAt"] = _utc_now()
                try:self._save_report()
                except Exception:pass
        self._emit({"type": "disarmed"})

    def close(self):
        self._stop.set()
        self.disarm()
        if self.script is not None:
            try:self.script.unload()
            except Exception:pass
        if self.session is not None:
            try:self.session.detach()
            except Exception:pass
        self.script = None
        self.session = None
