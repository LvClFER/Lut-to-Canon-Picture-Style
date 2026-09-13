from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .rp_payload import (
    canon_style_name, sha256_bytes,
    validate_agent_source,
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
    """Fail-closed Canon camera-registration coordinator.

    EOS Utility remains the transaction owner and compiles the selected PF3
    itself. The agent scopes the arbitrary-table acceptance correction to that
    exact EdsCFParse reference. EDSDK receives Canon's original pointer and
    size unchanged. No model-specific payload builder is selected by the
    application; 0x00000115 is observation-only.
    """

    def __init__(self, event_callback=None, agent_path=None):
        if frida is None:
            raise RuntimeError("Frida is not installed in this runtime")
        self.event_callback = event_callback or (lambda event: None)
        self.agent_path = Path(agent_path) if agent_path else Path(__file__).with_name("dynamic_camera_agent.js")
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
        self._compiler_hook_info = None
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
        if kind == "compiler_hooks_resolved":
            self._compiler_hook_info = {
                "method": event.get("resolver"),
                "moduleSize": event.get("moduleSize"),
                "addresses": event.get("addresses"),
            }
        if raw:
            event["binarySize"] = len(raw)
            event["binarySha256"] = sha256_bytes(raw)
        with self._lock:
            if self._report is not None:
                # Reports store hashes and sizes. An unknown native 0x01000203
                # carrier is persisted separately for read-only research.
                if kind == "native_payload_captured" and raw and self._report_path is not None:
                    slot = int(event.get("slot", 0))
                    capture_name = f"NATIVE_01000203_SLOT{slot}_{len(raw)}.bin"
                    capture_path = self._report_path.parent / capture_name
                    _atomic_bytes(capture_path, raw)
                    event["captureFile"] = capture_name
                    self._report["nativePayloadCapture"] = {
                        "property": "0x01000203",
                        "slot": slot,
                        "size": len(raw),
                        "sha256": sha256_bytes(raw),
                        "file": capture_name,
                        "readOnly": True,
                        "argumentsModified": False,
                    }
                elif kind == "native_payload_observed" and raw:
                    self._report["nativeCarrier"] = {
                        "size": len(raw), "sha256": sha256_bytes(raw),
                        "stored": False, "argumentsModifiedAtObservation": False,
                    }
                elif kind == "compiler_input_captured":
                    inputs = self._report.setdefault("liveCanonInputs", {})
                    if event.get("input") == "cameraId":
                        inputs["cameraIdHex"] = event.get("cameraIdHex")
                        inputs["cameraIdSize"] = event.get("size")
                    elif event.get("input") == "descriptor":
                        inputs["descriptorSize"] = event.get("size")
                        inputs["descriptorStored"] = False
                elif kind == "carrier_family_detected":
                    self._report["detectedCarrierFamily"] = {
                        "id": event.get("familyId"),
                        "status": event.get("familyStatus"),
                        "compilerRoute": event.get("compilerRoute"),
                        "modelSpecificBuilder": bool(event.get("modelSpecificBuilder")),
                        "validatedForWrite": bool(event.get("validatedForWrite")),
                        "size": event.get("size"),
                    }
                elif kind == "compiler_hooks_resolved":
                    self._report["compilerHookResolver"] = dict(self._compiler_hook_info or {})
                elif kind == "target_pf3_opened":
                    self._report["targetPf3Observed"] = True
                elif kind in {"compiler_validation_pass", "compiler_validation_failed"}:
                    self._report["nativeCompilerValidation"] = dict(event.get("validation") or {})
                    self._report.setdefault("validation", {})["semanticStatus"] = (
                        "passed" if kind == "compiler_validation_pass" else "failed"
                    )
                elif kind == "compiler_transport_match":
                    self._report["compilerTransportValidation"] = {
                        "exact": bool(event.get("exact")),
                        "size": event.get("size"),
                        "method": "byte-for-byte in process",
                    }
                    self._report.setdefault("validation", {})["transportStatus"] = (
                        "passed" if event.get("exact") else "failed"
                    )
                self._report.setdefault("events", []).append(dict(event))
                if kind == "install_success":
                    self.armed = False
                    self._report["status"] = "SUCCESS"
                    self._report.setdefault("validation", {})["status"] = "passed"
                    self._report["completedAt"] = _utc_now()
                elif kind in {"install_error", "registration_blocked"}:
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
            "EOS Utility 3 with EdsCFParse/EDSDK was not ready. Connect the Canon camera, "
            f"open EOS Utility and try again{detail}"
        )

    def prepare_and_arm(self, pf3_path, slot, style_name, output_dir, launch_eos=True, base_pf3_path=None):
        pf3_path = Path(pf3_path).resolve()
        if not pf3_path.is_file() or pf3_path.stat().st_size != 434_511:
            raise RuntimeError("A validated 434,511-byte PF3 is required")
        with pf3_path.open("rb") as handle:
            header = handle.read(8)
        if len(header) < 7 or header[4:7] != b"PSP":
            raise RuntimeError("The camera-install input does not have a valid Canon PF3 header")
        slot = int(slot)
        if slot not in (0, 1, 2, 3):
            raise RuntimeError("Canon User Def. slot policy must be dynamic or 1..3")
        style_name = canon_style_name(style_name, pf3_path.stem)
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        self._emit({"type": "stage", "message": "Connecting to EOS Utility 3…"})
        self.connect(timeout=35.0, launch_if_missing=bool(launch_eos))

        report_path = output_dir / "CANON_CAMERA_INSTALL_REPORT.json"
        report = {
            "format": "CanonStyleStudio.DynamicCameraInstallReport",
            "version": 4,
            "status": "ARMED",
            "createdAt": _utc_now(),
            "cameraCompatibility": "EOS Utility native compiler/transport with target-PF3-scoped table acceptance; physical confirmation remains per body",
            "rawCompatibilityDoesNotImplyCameraCompatibility": True,
            "sourcePf3": pf3_path.name,
            "sourcePf3Sha256": sha256_bytes(pf3_path.read_bytes()),
            "slot": slot or None,
            "slotPolicy": "dynamicUserDef1To3" if slot == 0 else "suggestedSlot",
            "pictureStyleName": style_name,
            "validation": {
                "mode": "liveTargetPf3",
                "externalFixturesRequired": False,
                "targetPathExact": True,
                "semanticTableValidationRequired": True,
                "compilerToEdsdkByteMatchRequired": True,
                "status": "pendingCanonTransaction",
            },
            "targetCompiler": {
                "policy": "EOS Utility compiles the selected PF3 with its native live camera path; only EdsCFParse table acceptance is corrected",
                "modelSpecificBuilder": False,
                "targetPf3PathScoped": True,
                "semanticSignatureResolver": True,
            },
            "compilerHookResolver": dict(self._compiler_hook_info or {}),
            "cameraWritePolicy": {
                "payloadOwner": "EOS Utility / EDSDK",
                "replace203Payload": False,
                "modifyEdsdkArguments": False,
                "compilerValidationRequired": True,
                "compilerToTransportByteMatchRequired": True,
                "unvalidatedTransportBlockedBeforeOriginalCall": True,
                "patch115": False,
                "reason": "Canon selects and sends the camera-native payload; 0x00000115 is opaque binary state/control data",
            },
            "events": [],
        }
        with self._lock:
            self._report = report
            self._report_path = report_path
            self._save_report()

        self._emit({"type": "stage", "message": "Arming target-scoped Canon PF3 compiler acceptance…"})
        armed = self.script.exports_sync.armdynamic(slot, str(pf3_path), style_name)
        if not armed:
            raise RuntimeError("EOS Utility hook did not arm")
        self.armed = True
        return {
            "pf3": pf3_path,
            "slot": slot,
            "styleName": style_name,
            "reportPath": report_path,
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
