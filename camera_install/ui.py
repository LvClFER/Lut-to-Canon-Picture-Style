from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout,
)

from canon_engine import export_pf3
from canon_runtime import camera_support_dir, exported_styles_dir
from .eos_hook import EosRpInstaller, find_eos_utility
from .rp_assets import (
    RpAssetError, discover_rp_assets, import_rp_support_folder,
    import_rp_support_zip, validate_rp_asset_folder,
)
from .rp_payload import canon_style_name, safe_file_stem


class CameraSignals(QObject):
    result = Signal(object)
    error = Signal(str, str)
    event = Signal(object)


class CameraPrepareWorker(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = CameraSignals()

    def run(self):
        try:self.signals.result.emit(self.function())
        except Exception as exc:self.signals.error.emit(str(exc), traceback.format_exc())


class CameraInstallDialog(QDialog):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self.setWindowTitle("Send to Camera · EOS RP validated workflow")
        self.resize(760, 680)
        self.setMinimumSize(680, 600)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.worker = None
        self.installer = None
        self.preparing = False
        self.completed = False
        self.assets = None

        layout = QVBoxLayout(self)
        title = QLabel("Send to Camera · EOS RP")
        title.setStyleSheet("font-size:18pt;font-weight:700;")
        layout.addWidget(title)
        warning = QLabel(
            "Physically validated only on EOS RP. RAW compatibility with another Canon model does not "
            "validate its registration payload. EOS Utility remains the transaction owner; this app never "
            "auto-clicks its interface."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#FFB86B;font-weight:600;")
        layout.addWidget(warning)

        assets_row = QHBoxLayout()
        assets_row.addWidget(QLabel("EOS RP support files"))
        self.assets_status = QLabel("Not configured")
        self.assets_status.setWordWrap(True)
        assets_row.addWidget(self.assets_status, 1)
        self.assets_button = QPushButton("Import Folder…")
        self.assets_button.clicked.connect(self.locate_assets)
        assets_row.addWidget(self.assets_button)
        self.import_zip_button = QPushButton("Import Manual Loader ZIP…")
        self.import_zip_button.clicked.connect(self.import_assets_zip)
        assets_row.addWidget(self.import_zip_button)
        layout.addLayout(assets_row)
        support_help = QLabel(
            "Required package: CANON_RP_MANUAL_LOADER_V2_4_0_BASE_STYLE.zip. It contains five exact "
            "compiler/carrier fixtures plus the validated Canon base PF3 files. These captured/Canon-derived "
            "binaries are not redistributed in the public app; import your existing ZIP here."
        )
        support_help.setWordWrap(True)
        support_help.setObjectName("Muted")
        layout.addWidget(support_help)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target"))
        self.target = QLabel("EOS RP install · unvalidated-camera payload capture")
        target_row.addWidget(self.target, 1)
        target_row.addWidget(QLabel("Choose User Def. 1, 2 or 3 in EOS Utility"))
        layout.addLayout(target_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Camera style name"))
        self.style_name = QLineEdit(main.project_name.text().strip() or "Picture Style")
        self.style_name.setMaxLength(31)
        name_row.addWidget(self.style_name, 1)
        layout.addLayout(name_row)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.requirements = QLabel()
        self.requirements.setWordWrap(True)
        layout.addWidget(self.requirements)

        self.confirm_rp = QCheckBox(
            "I understand EOS RP is the only validated write target; unknown payload layouts are captured without patching"
        )
        self.confirm_rp.toggled.connect(self.update_prepare_enabled)
        layout.addWidget(self.confirm_rp)

        self.steps = QLabel(
            "Workflow: export the current editor state → exact Canon compiler self-test → compile Block1 → "
            "build the validated 16752-byte RP payload → arm the hook → you perform a normal registration "
            "in EOS Utility. Property 0x00000115 remains untouched."
        )
        self.steps.setWordWrap(True)
        layout.addWidget(self.steps)

        self.progress = QProgressBar()
        self.progress.setRange(0, 5)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        buttons = QHBoxLayout()
        self.close_button = QPushButton("Close / Disarm")
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.close_button)
        self.eos_button = QPushButton("Open EOS Utility")
        self.eos_button.clicked.connect(self.open_eos_utility)
        buttons.addWidget(self.eos_button)
        buttons.addStretch()
        self.prepare_button = QPushButton("Prepare / Capture")
        self.prepare_button.setObjectName("AccentButton")
        self.prepare_button.clicked.connect(self.start_prepare)
        buttons.addWidget(self.prepare_button)
        layout.addLayout(buttons)

        self.refresh_assets()
        self.refresh_summary()

    def append(self, text):
        self.log.append(str(text))

    def refresh_summary(self):
        base = dict(self.main.base_resolution or {})
        validity = "validated local PF3 base" if base.get("validated") else "EXPERIMENTAL base — camera arm blocked"
        active = sum(1 for item in self.main.luts if item.get("enabled") and item.get("opacity", 0) > 0)
        creative = self.main.controls_dict().get("creative") or {}
        axes = creative.get("color_axes") or {}
        creative_active = any(any(values.values()) for values in axes.values()) or creative.get("color_chrome") != "Off" or creative.get("color_chrome_fx_blue") != "Off" or creative.get("tone_curve") != [0.0, 0.25, 0.5, 0.75, 1.0]
        self.summary.setText(
            f"Current editor state: <b>{self.main.base_combo.currentText()}</b> · {validity} · "
            f"{active} active LUT layer(s) · Creative Color {'active' if creative_active else 'neutral'} · Canon 33³/12-bit export"
        )
        self.update_prepare_enabled()

    def refresh_assets(self):
        configured = self.main.settings.data.get("camera_assets_folder") or ""
        self.assets = discover_rp_assets(configured)
        if self.assets:
            portable_parent = camera_support_dir().resolve()
            try:
                already_portable = self.assets.root.resolve().is_relative_to(portable_parent)
            except (OSError, ValueError):
                already_portable = False
            if not already_portable:
                try:
                    self.assets = import_rp_support_folder(self.assets.root, portable_parent)
                except Exception as exc:
                    self.assets = None
                    self.assets_status.setText("Portable import failed · " + str(exc))
        if configured and not self.assets:
            try:validate_rp_asset_folder(configured)
            except Exception as exc:self.assets_status.setText("Invalid · " + str(exc))
        if self.assets:
            self.assets_status.setText("Validated Manual Loader v2.4 support set")
            self.assets_status.setToolTip(str(self.assets.root))
            if str(self.assets.root) != configured:
                self.main.settings.data["camera_assets_folder"] = str(self.assets.root)
                self.main.settings.data["base_pf3_folder"] = str(self.assets.root)
                self.main.settings.save()
                self.main.base_resolution = None
                self.main.update_base_source_status()
        elif not configured:
            self.assets_status.setText("Required external research/support files are not configured")
        self.update_prepare_enabled()

    def locate_assets(self):
        start = self.main.settings.data.get("camera_assets_folder") or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Import Manual Loader v2.4 support folder", start)
        if not selected:
            return
        try:
            assets = import_rp_support_folder(selected, camera_support_dir())
        except RpAssetError as exc:
            QMessageBox.critical(self, "Invalid EOS RP support folder", str(exc))
            return
        self.assets = assets
        self.main.settings.data["camera_assets_folder"] = str(assets.root)
        # The same validated loader package contains the five exact Canon base
        # templates. The editor's independent hash checks still decide whether
        # the currently selected base is valid.
        self.main.settings.data["base_pf3_folder"] = str(assets.root)
        self.main.settings.save()
        self.main.base_resolution = None
        self.main.update_base_source_status()
        self.assets_status.setText("Validated Manual Loader v2.4 support set")
        self.assets_status.setToolTip(str(assets.root))
        self.refresh_summary()
        self.append(f"Support fixtures copied into the app and validated: {assets.root}")

    def import_assets_zip(self):
        start = Path.home() / "Downloads"
        selected, _ = QFileDialog.getOpenFileName(
            self, "Import Manual Loader v2.4 support ZIP", str(start), "Manual Loader ZIP (*.zip)"
        )
        if not selected:
            return
        try:
            assets = import_rp_support_zip(selected, camera_support_dir())
        except Exception as exc:
            QMessageBox.critical(self, "Invalid Manual Loader ZIP", str(exc))
            return
        self.assets = assets
        self.main.settings.data["camera_assets_folder"] = str(assets.root)
        self.main.settings.data["base_pf3_folder"] = str(assets.root)
        self.main.settings.save()
        self.main.base_resolution = None
        self.main.update_base_source_status()
        self.assets_status.setText("Imported into app · SHA-256 validated private copy")
        self.assets_status.setToolTip(str(assets.root))
        self.refresh_summary()
        self.append(f"Manual Loader ZIP imported into the app: {assets.root}")

    def prepare_block_reasons(self):
        reasons = []
        if not self.assets:
            reasons.append("Import the Manual Loader v2.4 ZIP or locate its extracted folder")
        if not bool((self.main.base_resolution or {}).get("validated")):
            reasons.append("Select a hash-validated Canon base PF3 (the imported ZIP supplies these bases)")
        if not self.confirm_rp.isChecked():
            reasons.append("Confirm that the connected camera is an EOS RP")
        return reasons

    def update_prepare_enabled(self):
        armed = bool(self.installer and self.installer.armed)
        reasons = self.prepare_block_reasons()
        if reasons:
            self.requirements.setText("Before preparing:\n• " + "\n• ".join(reasons))
            self.requirements.setStyleSheet("color:#FFB86B;font-weight:600;")
        else:
            self.requirements.setText("✓ Ready to prepare and arm the validated EOS RP workflow")
            self.requirements.setStyleSheet("color:#72D58A;font-weight:600;")
        # Keep the button clickable while prerequisites are missing so a click
        # explains the blockers instead of appearing to do nothing. Safety is
        # still fail-closed below and again inside the background installer.
        self.prepare_button.setEnabled(not self.preparing and not armed and not self.completed)

    def open_eos_utility(self):
        executable = find_eos_utility()
        if not executable:
            QMessageBox.warning(self, "EOS Utility", "EOS Utility 3 was not found in the standard Canon installation folders.")
            return
        try:
            import subprocess
            subprocess.Popen([str(executable)], cwd=str(executable.parent))
            self.append("EOS Utility 3 opened. Connect the EOS RP and leave EOS Utility running.")
        except Exception as exc:
            QMessageBox.critical(self, "EOS Utility", str(exc))

    def start_prepare(self):
        reasons = self.prepare_block_reasons()
        if reasons:
            message = "Camera installation is not ready:\n\n• " + "\n• ".join(reasons)
            self.append(message.replace("\n\n", " ").replace("\n", " "))
            QMessageBox.warning(self, "Cannot prepare EOS RP", message)
            return
        try:
            assets = validate_rp_asset_folder(self.main.settings.data.get("camera_assets_folder") or "")
            dll = self.main.dll_path()
            base = self.main.current_base_path()
            base_info = dict(self.main.base_resolution or {})
            if not base_info.get("validated"):
                raise RuntimeError("Camera installation requires a hash-validated Canon PF3 base")
            # Immutable request snapshot: no Qt state is touched by the worker.
            luts = [
                {"id": item.get("id"), "cube": item["cube"],
                 "enabled": bool(item.get("enabled", True)), "opacity": float(item.get("opacity", 1.0))}
                for item in self.main.luts
            ]
            controls = dict(self.main.controls_dict())
            style_name = canon_style_name(self.style_name.text(), self.main.project_name.text())
            slot = 0  # The genuine EOS Utility transaction determines the slot.
            base_style = self.main.base_combo.currentText()
        except Exception as exc:
            QMessageBox.critical(self, "Cannot prepare EOS RP", str(exc))
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_dir = exported_styles_dir() / f"{stamp}_{safe_file_stem(style_name)}"
        pf3_path = output_dir / (safe_file_stem(style_name) + ".pf3")
        self.installer = EosRpInstaller(assets, event_callback=lambda event:self.worker.signals.event.emit(event))
        self.preparing = True
        self.completed = False
        self.progress.setValue(0)
        self.log.clear()
        self.append("Current editor state captured on the UI thread.")
        self.append(f"Base: {base_style} · validated template")
        self.append(f"Persistent export folder: {output_dir}")
        self.update_prepare_enabled()
        self.assets_button.setEnabled(False)
        self.import_zip_button.setEnabled(False)

        def work():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.worker.signals.event.emit({"type":"stage", "message":"Exporting current Canon 33³ PF3…"})
            size, digest = export_pf3(
                dll, base, pf3_path, luts, controls, style_name,
                log=lambda message:self.worker.signals.event.emit({"type":"log", "message":str(message)}),
                progress=lambda value:None,
            )
            manifest = {
                "format":"CanonStyleStudio.CameraExport", "version":1,
                "pf3":pf3_path.name, "pf3Size":size, "pf3Sha256":digest,
                "basePictureStyle":base_style, "baseTemplateValidated":True,
                "basePf3Sha256":base_info.get("sha256"),
                "cameraTarget":"EOS RP", "slot":None, "slotPolicy":"dynamicUserDef1To3",
            }
            pf3_path.with_suffix(".manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            self.worker.signals.event.emit({"type":"pf3_ready", "size":size, "sha256":digest})
            return self.installer.prepare_and_arm(
                pf3_path, slot, style_name, output_dir, launch_eos=True
            )

        self.worker = CameraPrepareWorker(work)
        # Rebind the installer callback now that the worker/signal object exists.
        self.installer.event_callback = lambda event:self.worker.signals.event.emit(event)
        self.worker.signals.event.connect(self.handle_event)
        self.worker.signals.result.connect(self.prepared)
        self.worker.signals.error.connect(self.failed)
        self.pool.start(self.worker)

    def handle_event(self, event):
        kind = event.get("type")
        if kind == "stage":
            self.progress.setValue(min(4, self.progress.value() + 1))
            self.append(event.get("message"))
        elif kind == "log":
            self.append(event.get("message"))
        elif kind == "attached":
            self.append(f"Attached to EOS Utility 3 · PID {event.get('pid')}")
        elif kind == "eos_started":
            self.append("EOS Utility 3 started. Waiting for Canon modules…")
        elif kind == "selftest_pass":
            self.append("Compiler self-test: EXACT 8192-byte match.")
        elif kind == "ready":
            self.append("EdsCFParse + EDSDK hook ready inside EOS Utility.")
        elif kind == "armed":
            self.append("Hook armed · choose User Def. 1, 2 or 3 in EOS Utility.")
        elif kind == "registration_seen":
            self.append(f"Genuine registration seen · User Def. {event.get('slot')} · {event.get('size')} bytes")
        elif kind == "native_payload_captured":
            self.append(
                f"Read-only diagnostic capture saved · {event.get('captureFile')} · "
                f"SHA-256 {event.get('binarySha256')}"
            )
        elif kind == "native_payload_capture_error":
            self.append("ERROR: Could not capture native registration payload · " + str(event.get("error")))
        elif kind == "control115_seen":
            self.append(f"0x00000115 observed ({event.get('size')} bytes) · UNTOUCHED")
        elif kind == "payload_patched":
            self.append("Outgoing 0x01000203 payload replaced with validated EOS RP payload.")
        elif kind == "registration_return":
            self.append(f"0x01000203 returned rc={event.get('rc')} · patched={event.get('patched')}")
        elif kind == "install_success":
            self.completed = True
            self.progress.setValue(5)
            self.append(f"✓ EOS RP accepted User Def. {event.get('slot')}.")
            self.steps.setText(
                "Installation completed. Close EOS Utility completely and reopen it before preparing the next "
                "preset; repeated transactions have shown state-related reliability problems."
            )
            self.prepare_button.setText("Installed")
            self.prepare_button.setEnabled(False)
        elif kind in {"install_error", "hook_error", "frida_error"}:
            self.append("ERROR: " + str(event.get("reason") or event.get("error")))
        elif kind == "disarmed":
            self.append("Camera hook disarmed.")

    def prepared(self, result):
        self.preparing = False
        self.progress.setValue(4)
        self.assets_button.setEnabled(True)
        self.import_zip_button.setEnabled(True)
        self.append(f"✓ ARMED · compiler/self-test and payload validation passed")
        self.append(f"PF3: {Path(result['pf3']).name}")
        self.append(f"Install report: {Path(result['reportPath']).name}")
        self.steps.setText(
            "FINAL STEP — In EOS Utility, register the generated PF3 normally to User Def. 1, 2 or 3. "
            f"Expected camera name: {result['styleName']}. The app is waiting for the genuine 0x01000203 write. "
            "Do not close this window until success or until you intentionally disarm."
        )
        try:
            import os
            os.startfile(str(Path(result["pf3"]).parent))
        except Exception:
            pass
        self.update_prepare_enabled()

    def failed(self, message, trace):
        self.preparing = False
        self.assets_button.setEnabled(True)
        self.import_zip_button.setEnabled(True)
        self.append("ERROR: " + message)
        self.append(trace)
        if self.installer:
            self.installer.close()
            self.installer = None
        self.update_prepare_enabled()
        QMessageBox.critical(self, "EOS RP installation blocked", message)

    def _shutdown(self, confirm=True):
        if self.installer and self.installer.armed and not self.completed:
            if confirm:
                answer = QMessageBox.question(
                    self, "Disarm EOS RP installation",
                    "The EOS Utility hook is armed. Close this window and disarm it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return False
        if self.installer:
            self.installer.close()
            self.installer = None
        if self.preparing:
            try:self.pool.clear();self.pool.waitForDone(5000)
            except Exception:pass
            self.preparing = False
        return True

    def reject(self):
        if self._shutdown(confirm=True):
            super().reject()

    def closeEvent(self, event):
        if not self._shutdown(confirm=True):
            event.ignore()
            return
        event.accept()
