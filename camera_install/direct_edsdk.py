from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from .rp_assets import RpAssetSet
from .rp_payload import (
    canon_style_name, sha256_bytes, validate_agent_source,
    validate_compiler_selftest,
)

try:
    import frida
except Exception:
    frida = None


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def find_direct_canon_runtime():
    """Find the current x86 Canon compiler/EDSDK pair without copying it."""
    candidates = []
    for key in ("ProgramFiles(x86)", "ProgramFiles"):
        base = Path(os.environ.get(key, ""))
        if str(base):
            candidates.extend((
                base / "Canon" / "EOS Utility" / "EU3",
                base / "Canon" / "EOS Utility 3" / "EU3",
            ))
    for folder in candidates:
        if (folder / "EDSDK.dll").is_file() and (folder / "EdsCFParse.dll").is_file():
            return folder
    return None


def find_x86_host():
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = (
        windows / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        windows / "SysWOW64" / "cmd.exe",
    )
    return next((path for path in candidates if path.is_file()), None)


class DirectCanonInstaller:
    """Isolated direct Canon compiler + EDSDK registration coordinator.

    A hidden x86 host loads the Canon DLLs in place from the user's installed
    EOS Utility. Canon Style Studio never redistributes them. EdsCFParse still
    chooses the connected camera's native representation, and EDSDK receives
    that exact compiler output. Camera-owned 0x00000115 data is read live and
    replayed byte-for-byte; it is never fabricated or patched.
    """

    def __init__(self, assets: RpAssetSet, event_callback=None, agent_path=None, extension_path=None):
        if frida is None:
            raise RuntimeError("Frida is not installed in this runtime")
        self.assets = assets
        self.event_callback = event_callback or (lambda event: None)
        folder = Path(__file__).resolve().parent
        self.agent_path = Path(agent_path) if agent_path else folder / "dynamic_camera_agent.js"
        self.extension_path = Path(extension_path) if extension_path else folder / "direct_edsdk_extension.js"
        self.agent_source = self.agent_path.read_text(encoding="utf-8")
        validate_agent_source(self.agent_source)
        self.extension_source = self.extension_path.read_text(encoding="utf-8")
        self._validate_extension(self.extension_source)
        self.device = None
        self.session = None
        self.script = None
        self.pid = None
        self.armed = False
        self._ready = threading.Event()
        self._lock = threading.RLock()
        self._report = None
        self._report_path = None
        self._compiler_hook_info = None

    @staticmethod
    def _validate_extension(source: str):
        required = (
            "directcompileandinstall", "EdsInitializeSDK", "EdsGetCameraList",
            "EdsOpenSession", "EdsCloseSession", "EdsGetPropertySize",
            "EdsGetPropertyData", "EdsSetPropertyData", "EdsSendStatusCommand",
            "directReadProperty(0x00000115", "control115ReadAndReplayedUnchanged",
            "native203.size !== payload.length", "More than one Canon camera",
        )
        missing = [value for value in required if value not in source]
        if missing:
            raise RuntimeError("Direct Canon agent is missing safety guards: " + ", ".join(missing))
        forbidden = (
            "bytes.fromhex", "RP_SUPERIA_TEMPLATE", "1300D_DESCRIPTOR",
            "args[3] =", "args[4] =",
        )
        present = [value for value in forbidden if value in source]
        if present:
            raise RuntimeError("Direct Canon agent contains a model-specific/unsafe path: " + ", ".join(present))

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
        kind = event.get("type")
        if kind == "compiler_hooks_resolved":
            self._compiler_hook_info = {
                "method": event.get("resolver"),
                "moduleSize": event.get("moduleSize"),
                "addresses": event.get("addresses"),
            }
        with self._lock:
            if self._report is not None:
                self._report.setdefault("events", []).append(event)
                if kind == "compiler_hooks_resolved":
                    self._report["compilerHookResolver"] = dict(self._compiler_hook_info or {})
                elif kind == "direct_camera_connected":
                    self._report["camera"] = {
                        "description": event.get("description"),
                        "portName": event.get("portName"),
                    }
                elif kind == "compiler_validation_pass":
                    self._report["nativeCompilerValidation"] = dict(event.get("validation") or {})
                elif kind == "direct_state_captured":
                    self._report["liveCameraState"] = {
                        "slot": event.get("slot"),
                        "selector114Size": event.get("selector114Size"),
                        "control115Size": event.get("control115Size"),
                        "nativeCarrierSize": event.get("nativeCarrierSize"),
                        "control115Untouched": True,
                    }
                try:
                    self._save_report()
                except Exception:
                    pass
        if kind == "ready":
            self._ready.set()
        self._emit(event)

    def _start_host(self):
        runtime = find_direct_canon_runtime()
        if runtime is None:
            raise RuntimeError(
                "The current Canon EOS Utility compiler runtime was not found. "
                "Install EOS Utility 3; it does not need to be opened."
            )
        host = find_x86_host()
        if host is None:
            raise RuntimeError("A Windows x86 helper host was not found")
        self.device = frida.get_local_device()
        if host.name.lower() == "powershell.exe":
            command = [
                str(host), "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden",
                "-NoExit", "-Command", "-",
            ]
        else:
            command = [str(host), "/q", "/k"]
        pid = self.device.spawn(command)
        try:
            session = self.device.attach(pid)
            source = self.agent_source + "\n\n" + self.extension_source
            script = session.create_script(source)
            script.on("message", self._on_message)
            script.load()
            self.device.resume(pid)
            self.device = self.device
            self.session = session
            self.script = script
            self.pid = pid
            info = dict(script.exports_sync.loaddirectruntime(str(runtime)) or {})
            if not info.get("ok"):
                raise RuntimeError("The isolated Canon runtime did not initialize")
            self._emit({"type": "direct_runtime_ready", **info})
            return info
        except Exception:
            try:
                self.device.kill(pid)
            except Exception:
                pass
            raise

    def _compile(self, pf3_path: Path):
        result = self.script.exports_sync.compile(
            str(pf3_path.resolve()),
            self.assets.camera_id.read_bytes().hex(),
            self.assets.descriptor.read_bytes().hex(),
        )
        if not isinstance(result, (list, tuple)) or len(result) != 2:
            raise RuntimeError("Unexpected binary response from the Canon compiler")
        metadata, data = result
        return dict(metadata or {}), bytes(data or b"")

    def prepare_and_install(self, pf3_path, slot, style_name, output_dir, base_pf3_path=None):
        pf3_path = Path(pf3_path).resolve()
        if not pf3_path.is_file() or pf3_path.stat().st_size != 434_511:
            raise RuntimeError("A validated 434,511-byte PF3 is required")
        with pf3_path.open("rb") as handle:
            header = handle.read(8)
        if len(header) < 7 or header[4:7] != b"PSP":
            raise RuntimeError("The camera-install input does not have a valid Canon PF3 header")
        slot = int(slot)
        if slot not in (1, 2, 3):
            raise RuntimeError("Direct Canon installation requires User Def. 1, 2 or 3")
        style_name = canon_style_name(style_name, pf3_path.stem)
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "CANON_DIRECT_INSTALL_REPORT.json"
        self._report_path = report_path
        self._report = {
            "format": "CanonStyleStudio.DirectCanonInstallReport",
            "version": 1,
            "status": "STARTING",
            "createdAt": _utc_now(),
            "sourcePf3": pf3_path.name,
            "sourcePf3Sha256": sha256_bytes(pf3_path.read_bytes()),
            "pictureStyleName": style_name,
            "slot": slot,
            "transport": {
                "owner": "Canon Style Studio isolated host + Canon EDSDK",
                "eosUtilityProcessRequired": False,
                "canonRuntimeDiscoveredInPlace": True,
                "modelSpecificBuilder": False,
                "patch115": False,
                "control115Policy": "read live and replay byte-for-byte without modification",
            },
            "events": [],
        }
        self._save_report()
        try:
            self._emit({"type": "stage", "message": "Starting isolated Canon x86 runtime…"})
            runtime_info = self._start_host()
            self._report["runtime"] = runtime_info

            self._emit({"type": "stage", "message": "Running exact Canon compiler self-test…"})
            selftest_meta, selftest_legacy = self._compile(self.assets.selftest_pf3)
            if not selftest_meta.get("ok"):
                raise RuntimeError("Canon compiler rejected the known-good self-test PF3")
            selftest_hash = validate_compiler_selftest(
                selftest_legacy, self.assets.read_selftest_block()
            )
            self._report["compilerSelfTest"] = {
                "exact": True, "blockSha256": selftest_hash, "meta": selftest_meta,
            }
            self._emit({"type": "selftest_pass", "blockSha256": selftest_hash})

            self._emit({"type": "stage", "message": "Opening a direct Canon EDSDK camera session…"})
            camera = dict(self.script.exports_sync.directconnect() or {})
            if not camera.get("ok"):
                raise RuntimeError("The direct Canon camera session did not initialize")
            descriptor = bytes.fromhex(camera.pop("descriptorHex"))
            self._report["camera"] = {
                **camera,
                "descriptorSha256": hashlib.sha256(descriptor).hexdigest(),
            }
            self._report["status"] = "CAMERA_CONNECTED"
            self._save_report()

            self.armed = True
            self._emit({"type": "stage", "message": "Compiling and registering through Canon EDSDK…"})
            result = dict(self.script.exports_sync.directcompileandinstall(
                str(pf3_path), style_name, slot,
                camera["cameraIdHex"], descriptor.hex(),
            ) or {})
            if not result.get("ok"):
                raise RuntimeError("Canon direct installation did not complete")
            self.armed = False
            self._report["status"] = "SUCCESS"
            self._report["completedAt"] = _utc_now()
            self._report["result"] = result
            self._save_report()
            try:
                self.script.exports_sync.directdisconnect()
            except Exception:
                pass
            return {
                "mode": "direct",
                "completed": True,
                "pf3": pf3_path,
                "slot": slot,
                "styleName": style_name,
                "reportPath": report_path,
                "camera": self._report.get("camera", {}),
                "result": result,
            }
        except Exception as exc:
            self.armed = False
            self._report["status"] = "ERROR"
            self._report["error"] = str(exc)
            self._report["completedAt"] = _utc_now()
            try:
                self._save_report()
            except Exception:
                pass
            if self.script is not None:
                try:
                    self.script.exports_sync.directdisconnect()
                except Exception:
                    pass
            raise

    def close(self):
        self.armed = False
        if self.script is not None:
            try:
                self.script.exports_sync.directdisconnect()
            except Exception:
                pass
            try:
                self.script.unload()
            except Exception:
                pass
        if self.session is not None:
            try:
                self.session.detach()
            except Exception:
                pass
        if self.device is not None and self.pid is not None:
            try:
                self.device.kill(self.pid)
            except Exception:
                pass
        self.script = None
        self.session = None
        self.pid = None
