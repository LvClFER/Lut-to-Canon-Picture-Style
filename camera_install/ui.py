from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout,
)

from canon_engine import export_pf3
from canon_runtime import camera_support_dir, exported_styles_dir
from .direct_edsdk import DirectCanonInstaller, find_direct_canon_runtime
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
        self.setWindowTitle("Send to Camera · Canon-native PF3 workflow")
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
        title = QLabel("Send to Camera · Canon Native")
        title.setStyleSheet("font-size:18pt;font-weight:700;")
        layout.addWidget(title)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color:#FFB86B;font-weight:600;")
        layout.addWidget(self.warning)

        assets_row = QHBoxLayout()
        assets_row.addWidget(QLabel("Canon compiler self-test files"))
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
            "The existing Manual Loader support set is retained only for the exact fail-closed Canon compiler "
            "self-test and validated base PF3 files. It is not used to build or select a camera payload."
        )
        support_help.setWordWrap(True)
        support_help.setObjectName("Muted")
        layout.addWidget(support_help)

        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Installation method"))
        self.method_combo = QComboBox()
        self.method_combo.addItem("Direct from Canon Style Studio · experimental", "direct")
        self.method_combo.addItem("EOS Utility guided fallback", "eos")
        self.method_combo.currentIndexChanged.connect(self.update_workflow_text)
        method_row.addWidget(self.method_combo, 1)
        method_row.addWidget(QLabel("Target slot"))
        self.slot_combo = QComboBox()
        for slot in (1, 2, 3):
            self.slot_combo.addItem(f"User Def. {slot}", slot)
        method_row.addWidget(self.slot_combo)
        layout.addLayout(method_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target"))
        self.target = QLabel()
        target_row.addWidget(self.target, 1)
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

        self.steps = QLabel(
            "Workflow: export PF3 → exact compiler self-test → identify that exact PF3 when EOS Utility opens it → "
            "correct Canon's internal table acceptance during its original compilation → validate the conversion → "
            "observe the unchanged Canon EDSDK transaction. Property 0x00000115 remains untouched."
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
        self.prepare_button = QPushButton("Install Directly")
        self.prepare_button.setObjectName("AccentButton")
        self.prepare_button.clicked.connect(self.start_prepare)
        buttons.addWidget(self.prepare_button)
        layout.addLayout(buttons)

        self.refresh_assets()
        self.refresh_summary()
        self.update_workflow_text()

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

    def current_method(self):
        return self.method_combo.currentData() or "direct"

    def update_workflow_text(self):
        direct = self.current_method() == "direct"
        self.slot_combo.setEnabled(direct)
        self.eos_button.setVisible(not direct)
        if direct:
            self.warning.setText(
                "Canon Style Studio opens its own isolated EDSDK session. Canon's installed compiler chooses the "
                "camera representation; the app validates it against the live camera carrier before writing. "
                "EOS Utility must be installed for its current Canon runtime, but it is not opened."
            )
            self.target.setText("Automatic · connected Canon camera · model-independent native compiler")
            self.steps.setText(
                "Workflow: export PF3 → exact compiler self-test → open direct EDSDK session → read live camera "
                "ID, descriptor, carrier and state → Canon-native compile → register selected slot. "
                "Property 0x00000115 is read live and replayed byte-for-byte, never fabricated or patched."
            )
            self.prepare_button.setText("Install Directly")
        else:
            self.warning.setText(
                "EOS Utility opens and compiles the selected PF3 through Canon's native camera path. The app only "
                "corrects the internal compiler gate that otherwise discards arbitrary PF3 tables. Canon selects "
                "the camera representation and EDSDK sends Canon's original buffer unchanged."
            )
            self.target.setText("Automatic · original EOS Utility compiler and camera transport")
            self.steps.setText(
                "Workflow: export PF3 → exact compiler self-test → identify that exact PF3 when EOS Utility opens "
                "it → correct Canon's internal table acceptance → observe the unchanged EDSDK transaction. "
                "Property 0x00000115 remains untouched."
            )
            self.prepare_button.setText("Prepare / Capture")
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
        if self.current_method() == "direct" and find_direct_canon_runtime() is None:
            reasons.append("Install EOS Utility 3 for the current Canon EDSDK/EdsCFParse runtime")
        return reasons

    def update_prepare_enabled(self):
        armed = bool(self.installer and self.installer.armed)
        reasons = self.prepare_block_reasons()
        if reasons:
            self.requirements.setText("Before preparing:\n• " + "\n• ".join(reasons))
            self.requirements.setStyleSheet("color:#FFB86B;font-weight:600;")
        else:
            action = "install directly" if self.current_method() == "direct" else "prepare the guided workflow"
            self.requirements.setText(f"✓ Ready to {action}")
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
            self.append("EOS Utility 3 opened. Connect the Canon camera and leave EOS Utility running.")
        except Exception as exc:
            QMessageBox.critical(self, "EOS Utility", str(exc))

    def start_prepare(self):
        reasons = self.prepare_block_reasons()
        if reasons:
            message = "Camera installation is not ready:\n\n• " + "\n• ".join(reasons)
            self.append(message.replace("\n\n", " ").replace("\n", " "))
            QMessageBox.warning(self, "Cannot prepare camera installation", message)
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
            method = self.current_method()
            slot = int(self.slot_combo.currentData()) if method == "direct" else 0
            base_style = self.main.base_combo.currentText()
        except Exception as exc:
            QMessageBox.critical(self, "Cannot prepare camera installation", str(exc))
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_dir = exported_styles_dir() / f"{stamp}_{safe_file_stem(style_name)}"
        pf3_path = output_dir / (safe_file_stem(style_name) + ".pf3")
        installer_class = DirectCanonInstaller if method == "direct" else EosRpInstaller
        self.installer = installer_class(assets, event_callback=lambda event:self.worker.signals.event.emit(event))
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
        self.method_combo.setEnabled(False)
        self.slot_combo.setEnabled(False)

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
                "cameraTarget":"Canon-native live compiler", "slot":slot or None,
                "slotPolicy":"selectedDirectSlot" if method == "direct" else "dynamicUserDef1To3",
                "installationMethod":method,
            }
            pf3_path.with_suffix(".manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            self.worker.signals.event.emit({"type":"pf3_ready", "size":size, "sha256":digest})
            if method == "direct":
                return self.installer.prepare_and_install(
                    pf3_path, slot, style_name, output_dir,
                )
            return self.installer.prepare_and_arm(pf3_path, slot, style_name, output_dir, launch_eos=True)

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
            if self.current_method() == "direct":
                self.append("Canon compiler acceptance hooks ready inside the isolated app host.")
            else:
                self.append("Canon native compiler acceptance + read-only EDSDK observer ready inside EOS Utility.")
        elif kind == "direct_runtime_ready":
            self.append("Isolated Canon x86 runtime loaded from the installed EOS Utility folder.")
        elif kind == "direct_camera_connected":
            self.append(
                f"Direct camera session opened · {event.get('description') or 'Canon camera'} · "
                f"{event.get('portName') or 'USB'}"
            )
        elif kind == "compiler_hooks_resolved":
            self.append("EdsCFParse internal functions resolved by semantic signatures.")
        elif kind == "armed":
            self.append("Target-PF3 compiler hook armed · choose User Def. 1, 2 or 3 in EOS Utility.")
        elif kind == "target_pf3_opened":
            self.append("EOS Utility opened the exact PF3 generated by Canon Style Studio.")
        elif kind == "target_pf3_compile_started":
            self.append(f"Canon is compiling the target PF3 · native output {event.get('size')} bytes")
        elif kind == "compiler_validation_pass":
            validation = event.get("validation") or {}
            self.append(
                "✓ Canon-native PF3 compilation validated · "
                f"{validation.get('compilerPath')} · EDSDK payload replacement not required"
            )
        elif kind == "compiler_validation_failed":
            self.append("ERROR: " + str(event.get("reason")))
        elif kind == "compiler_input_captured":
            if event.get("input") == "cameraId":
                self.append(f"Live Canon camera ID captured · {event.get('cameraIdHex')}")
            else:
                self.append(f"Live Canon descriptor captured · {event.get('size')} bytes")
        elif kind == "compiler_input_error":
            self.append("ERROR: Could not capture a live Canon compiler input · " + str(event.get("error")))
        elif kind == "registration_seen":
            self.append(f"Genuine registration seen · User Def. {event.get('slot')} · {event.get('size')} bytes")
        elif kind == "carrier_family_detected":
            self.append(
                f"Live Canon carrier observed · {event.get('size')} bytes · "
                "the Canon compiler will select its representation automatically"
            )
        elif kind == "native_payload_observed":
            self.append(f"Genuine Canon carrier observed · {event.get('size')} bytes · retained only as a report hash")
        elif kind == "native_payload_captured":
            self.append(
                f"Read-only diagnostic capture saved · {event.get('captureFile')} · "
                f"SHA-256 {event.get('binarySha256')}"
            )
        elif kind == "native_payload_capture_error":
            self.append("ERROR: Could not capture native registration payload · " + str(event.get("error")))
        elif kind == "control115_seen":
            self.append(f"0x00000115 observed ({event.get('size')} bytes) · UNTOUCHED")
        elif kind == "direct_state_captured":
            self.append(
                f"Live camera state captured · carrier {event.get('nativeCarrierSize')} bytes · "
                f"0x00000115 {event.get('control115Size')} bytes, preserved unchanged"
            )
        elif kind == "registration_return":
            self.append(
                f"Canon registration returned rc={event.get('rc')} · "
                "original buffer/size unchanged"
            )
        elif kind == "install_success":
            self.completed = True
            self.progress.setValue(5)
            self.append(f"✓ Canon camera accepted User Def. {event.get('slot')}.")
            self.steps.setText(
                "Installation completed. Close EOS Utility completely and reopen it before preparing the next "
                "preset; repeated transactions have shown state-related reliability problems."
            )
            self.prepare_button.setText("Installed")
            self.prepare_button.setEnabled(False)
        elif kind == "direct_install_success":
            self.append(
                f"✓ Direct Canon registration completed · User Def. {event.get('slot')} · "
                f"{event.get('payloadSize')} bytes · {event.get('compilerPath')}"
            )
        elif kind in {"install_error", "hook_error", "frida_error"}:
            self.append("ERROR: " + str(event.get("reason") or event.get("error")))
        elif kind == "disarmed":
            self.append("Camera hook disarmed.")

    def prepared(self, result):
        self.preparing = False
        if result.get("mode") == "direct":
            self.completed = True
            self.progress.setValue(5)
            self.assets_button.setEnabled(True)
            self.import_zip_button.setEnabled(True)
            self.method_combo.setEnabled(True)
            self.slot_combo.setEnabled(True)
            camera = result.get("camera") or {}
            self.append(f"PF3: {Path(result['pf3']).name}")
            self.append(f"Install report: {Path(result['reportPath']).name}")
            self.append(
                f"✓ Installed directly on {camera.get('description') or 'Canon camera'} · "
                f"User Def. {result.get('slot')}"
            )
            self.steps.setText(
                "Direct Canon EDSDK installation completed. Confirm the Picture Style name and LUT appearance "
                "on the camera; this physical result remains the final ground truth."
            )
            self.prepare_button.setText("Installed")
            self.update_prepare_enabled()
            return
        self.progress.setValue(4)
        self.assets_button.setEnabled(True)
        self.import_zip_button.setEnabled(True)
        self.method_combo.setEnabled(True)
        self.slot_combo.setEnabled(self.current_method() == "direct")
        self.append("✓ ARMED · exact compiler self-test passed; live Canon compilation is waiting")
        self.append(f"PF3: {Path(result['pf3']).name}")
        self.append(f"Install report: {Path(result['reportPath']).name}")
        self.steps.setText(
            "FINAL STEP — In EOS Utility, register the generated PF3 normally to User Def. 1, 2 or 3. "
            f"Expected camera name: {result['styleName']}. EOS Utility will compile and send it normally while "
            "the app corrects and validates only the selected PF3 inside Canon's compiler. "
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
        self.method_combo.setEnabled(True)
        self.slot_combo.setEnabled(self.current_method() == "direct")
        self.append("ERROR: " + message)
        self.append(trace)
        if self.installer:
            self.installer.close()
            self.installer = None
        self.update_prepare_enabled()
        QMessageBox.critical(self, "Canon camera installation blocked", message)

    def _shutdown(self, confirm=True):
        if self.installer and self.installer.armed and not self.completed:
            if confirm:
                answer = QMessageBox.question(
                    self, "Disarm Canon camera installation",
                    "The Canon camera workflow is active. Close this window and disarm it?",
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
