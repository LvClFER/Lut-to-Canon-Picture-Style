from __future__ import annotations

import traceback
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout,
)

from canon_engine import export_pf3, save_compiled_style_project
from canon_runtime import exported_styles_dir, style_export_path, logs_dir, open_local_path
from .eos_hook import EosRpInstaller, find_eos_utility
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


class IndependentInstallDialog(QDialog):
    """Explicit experimental controller; all device work stays outside Qt state."""
    def __init__(self,main,parent=None):
        super().__init__(parent)
        self.main=main
        self.worker=None
        self.busy=False
        self.install_available=sys.platform=='win32'
        self.pool=QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.setWindowTitle('Send to Camera · Independent USB')
        self.resize(760,520)
        layout=QVBoxLayout(self)
        title=QLabel('Send Picture Style to Camera')
        title.setStyleSheet('font-size:18pt;font-weight:700;')
        layout.addWidget(title)
        subtitle=QLabel('Independent PF3 compiler · direct USB · no Canon application or DLL required')
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        warning=QLabel('Experimental · reconstructed Canon serializer families; physical USB validation on EOS RP only. '
            'Close other camera applications before connecting. A failed write may require '
            'power/USB recovery. Camera capabilities, descriptor and slot format are checked before writing.')
        warning.setWordWrap(True)
        warning.setStyleSheet('color:#8A4C08;')
        layout.addWidget(warning)
        camera_group=QGroupBox('Camera and destination')
        camera_layout=QVBoxLayout(camera_group)
        row=QHBoxLayout()
        self.devices=QComboBox()
        self.devices.setPlaceholderText('Click Find USB cameras')
        self.devices.currentIndexChanged.connect(
            lambda _:self.install.setEnabled(self.install_available and not self.busy and bool(self.devices.currentData())))
        row.addWidget(self.devices,1)
        self.scan=QPushButton('Find USB cameras')
        self.scan.clicked.connect(self.find_devices)
        row.addWidget(self.scan)
        self.slot=QComboBox()
        for value in (1,2,3):self.slot.addItem(f'User Def. {value}',value)
        self.slot.setCurrentIndex(2)
        row.addWidget(self.slot)
        camera_layout.addLayout(row)
        self.camera_status=QLabel('Camera not queried. No USB access occurs until you click Find USB cameras.')
        self.camera_status.setWordWrap(True)
        camera_layout.addWidget(self.camera_status)
        layout.addWidget(camera_group)

        self.style_group=QGroupBox('Style to send')
        form=QHBoxLayout(self.style_group)
        self.style_name=QLineEdit(main.project_name.text().strip().rstrip('*') or 'Picture Style'
                                 if hasattr(main,'project_name') else 'Picture Style')
        self.style_name.setMaxLength(31)
        form.addWidget(QLabel('Picture Style name'))
        form.addWidget(self.style_name,1)
        layout.addWidget(self.style_group)
        editor_note=QLabel('Uses the base Picture Style, sharpness, colour controls and LUTs already '
                          'defined in the editor. To change them, close this window and edit the style.')
        editor_note.setWordWrap(True)
        layout.addWidget(editor_note)
        self.style_info=QLabel(f'{len(getattr(main,"luts",[]))} LUT layer(s) in editor · '
            'one editable .canonstyleproject saved in Documents/Canon Style Studio PF3. '
            'The selected slot is backed up before writing; no automatic retry or restore.')
        self.style_info.setWordWrap(True)
        layout.addWidget(self.style_info)
        self.details=QCheckBox('Show technical log')
        layout.addWidget(self.details)
        self.log=QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)
        self.details.toggled.connect(self.log.setVisible)
        layout.addWidget(self.log,1)
        buttons=QHBoxLayout()
        self.close_button=QPushButton('Close')
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.close_button)
        buttons.addStretch()
        self.install=QPushButton('Install independently…')
        self.install.setObjectName('AccentButton')
        self.install.clicked.connect(self.start_install)
        self.install.setEnabled(False)
        buttons.addWidget(self.install)
        layout.addLayout(buttons)

    def set_busy(self,value):
        self.busy=value
        self.camera_status.setStyleSheet('')
        self.style_group.setEnabled(not value)
        for widget in (self.scan,self.slot,self.devices,self.close_button):widget.setEnabled(not value)
        self.install.setEnabled(self.install_available and not value and bool(self.devices.currentData()))

    def find_devices(self):
        if sys.platform=='darwin':
            from .macos_discovery import enumerate_isolated as discover
        else:
            from .windows_wpd_probe import enumerate_portable_devices as discover
        self.set_busy(True)
        self.log.append('Discovering USB devices; no camera session is opened.')
        self.worker=CameraPrepareWorker(discover)
        self.worker.signals.result.connect(self.devices_found)
        self.worker.signals.error.connect(self.failed)
        self.pool.start(self.worker)

    def devices_found(self,devices):
        self.devices.clear()
        for device in devices:
            if device.get('canonCandidate') and device.get('idFingerprint'):
                self.devices.addItem(device.get('friendlyName') or device.get('name') or 'Canon camera',device['idFingerprint'])
        if self.devices.count()==1:self.devices.setCurrentIndex(0)
        self.log.append(f'{self.devices.count()} Canon device(s) found. Select the camera and slot explicitly.')
        self.camera_status.setText(f'{self.devices.count()} camera(s) found. Model compatibility and slot '
            'contents are checked during installation; finding a device does not confirm compatibility.')
        if not self.install_available:
            self.camera_status.setText(f'{self.devices.count()} camera(s) found. '
                'Camera installation on macOS is still under development.')
        self.set_busy(False)

    def start_install(self):
        import copy
        from types import SimpleNamespace
        if not self.install_available or self.busy or not self.devices.currentData():return
        try:
            base=Path((self.main.base_resolution or {}).get('path') or
                      getattr(self.main,'project_base_path',None) or
                      getattr(self.main,'custom_base_path',None) or '')
            selected_base=self.main.base_combo.currentText() if hasattr(self.main,'base_combo') else 'Neutral'
            if not base.is_file():
                from canon_engine import ensure_runtime_base_pf3, PICTURE_STYLE_IDS
                if selected_base not in PICTURE_STYLE_IDS:
                    raise ValueError('Reopen the imported PF3 or style project before sending it.')
                base=ensure_runtime_base_pf3(None,selected_base,
                    cipher_reference=base if base.is_file() else None)
            if not base or not Path(base).is_file():
                raise ValueError('Open an owned style project or PF3 to initialize independent generation.')
            base=Path(base)
            # Snapshot all editor/Qt state before starting background work.
            luts=[dict(id=item.get('id'),cube=item['cube'],enabled=bool(item.get('enabled',True)),
                       opacity=float(item.get('opacity',1.0))) for item in self.main.luts]
            controls=copy.deepcopy(self.main.controls_dict())
            title=canon_style_name(self.style_name.text(),'Picture Style')
            project=copy.deepcopy(self.main.project_document(base_override=base))
            project.name=title
            project.edit.update(controls,base_name=selected_base,basePictureStyle=selected_base,
                base_path=str(base),custom_pf3=str(base) if selected_base=='Imported PF3' else '')
            fingerprint=self.devices.currentData()
            device_name=self.devices.currentText()
            slot=self.slot.currentData()
        except Exception as error:
            QMessageBox.warning(self,'Independent installation',str(error));return
        bundle=style_export_path(safe_file_stem(title))
        folder=logs_dir()/'camera_install'/('independent_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        self.set_busy(True)
        self.log.append(f'Preparing style: {bundle}')
        self.camera_status.setText(f'Preparing {title} for {device_name} · User Def. {slot}.')
        def work():
            folder.mkdir(parents=True,exist_ok=False)
            pf3=folder/(safe_file_stem(title)+'.pf3')
            export_pf3(None,base,pf3,luts,controls,title)
            save_compiled_style_project(None,base,bundle,project,pf3)
            args=SimpleNamespace(device_id=None,device_fingerprint=fingerprint,
                request_descriptor=True,request_slot=slot,test_ui_lock=False,
                preflight_style=bundle,experimental_register=True,
                update_known_basic_controls=False,
                baseline_backup=folder/f'UserDef{slot}_baseline.bin',timeout_seconds=45)
            return dict(args=args,bundle=str(bundle),folder=str(folder),device_name=device_name,style_name=title)
        self.worker=CameraPrepareWorker(work)
        self.worker.signals.result.connect(self.installation_prepared)
        self.worker.signals.error.connect(self.failed)
        self.pool.start(self.worker)

    def installation_prepared(self,prepared):
        args=prepared['args']
        self.log.append(f"Style saved: {prepared['bundle']}")
        answer=QMessageBox.warning(self,'Authorize experimental camera write',
            f"Replace User Def. {args.request_slot} on {prepared['device_name']} with this saved style?\n"
            f"{prepared['bundle']}\n\n"
            'The slot Basic controls must match the style values. Other slot data is preserved.\n\n'
            'A baseline style backup will be saved. This experimental write can require camera '
            'power/USB recovery. No automatic retry or restore will be performed.',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:
            self.set_busy(False)
            self.camera_status.setText('Style saved. Camera installation cancelled.')
            self.log.append('Style saved; camera installation cancelled.')
            return
        def work():
            import json
            from .independent_session_diagnostic import _run_isolated
            report,code=_run_isolated(args)
            with (Path(prepared['folder'])/'INDEPENDENT_INSTALL_REPORT.json').open('x',encoding='utf-8') as stream:
                json.dump(report,stream,indent=2)
            return dict(report=report,code=code,folder=prepared['folder'],bundle=prepared['bundle'],
                slot=args.request_slot,device_name=prepared['device_name'],style_name=prepared['style_name'])
        self.worker=CameraPrepareWorker(work)
        self.camera_status.setText(f'Installing in User Def. {args.request_slot} · do not disconnect the camera.')
        self.worker.signals.result.connect(self.installation_finished)
        self.worker.signals.error.connect(self.failed)
        self.pool.start(self.worker)

    def installation_finished(self,result):
        self.set_busy(False)
        report=result['report']
        if report.get('model'):
            self.log.append(f"Camera: {report['model']} · serializer family {report.get('serializerFamily')} · {report.get('route')}")
        self.log.append(f"Style saved: {result['bundle']}")
        self.log.append(f"Technical report and baseline backup: {result['folder']}")
        control_changes=report.get('knownBasicControlChanges',[])
        if (result['code'] or report.get('requestedSlotContentMatched') is not True
                or type(control_changes) is not list
                or (control_changes and report.get('requestedSlotStateMatched') is not True)
                or report.get('requestedSlot')!=result['slot']
                or report.get('temporaryModesCleanupCompleted') is not True
                or report.get('connectionCleanupCompleted') is not True
                or report.get('failed') or report.get('recoveryRequired')):
            self.details.setChecked(True)
            self.camera_status.setText('Installation not confirmed. See the technical log; no retry was performed.')
            if report.get('blockedReason'):
                self.log.append(report['blockedReason'])
            for difference in report.get('controlDifferences',[]):
                self.log.append(f"{difference['control']}: slot {difference['slotValue']}, "
                    f"candidate {difference['candidateValue']}. Use matching editor/camera values; state was not rewritten.")
            self.log.append('Installation not confirmed. No retry was performed. '+
                ('Camera USB/power recovery may be required.' if report.get('recoveryRequired') else
                 'Read the report before trying again.'))
            return
        self.log.append('Requested slot content matches the compiled style. Session closed. '
                        'Verify the look in camera; byte equality alone is not visual confirmation.')
        message=(f"{result['style_name']} was sent successfully to {result['device_name']} · "
                 f"User Def. {result['slot']}.\n\n"
                 'The camera slot was read back and matches the sent style. The USB session closed '
                 'correctly. Verify the look in camera.')
        if control_changes:
            message+='\n\nThe changed Basic controls were also confirmed by the camera.'
        self.camera_status.setText(f"✓ Sent successfully · User Def. {result['slot']} · verified in camera.")
        self.camera_status.setStyleSheet('color:#28734D;font-weight:600;')
        self.install.setEnabled(False)
        QMessageBox.information(self,'Picture Style sent successfully',message)

    def failed(self,message,trace):
        self.set_busy(False)
        self.camera_status.setText('Operation failed. See the technical log.')
        self.details.setChecked(True)
        self.log.append('ERROR: '+message)
        self.log.append(trace)

    def reject(self):
        if not self.busy:super().reject()

    def closeEvent(self,event):
        if self.busy:event.ignore()
        else:event.accept()


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

        layout = QVBoxLayout(self)
        title = QLabel("Send to Camera · Canon Native")
        title.setStyleSheet("font-size:18pt;font-weight:700;")
        layout.addWidget(title)
        warning = QLabel(
            "EOS Utility opens and compiles the selected PF3 through Canon's native camera path. The app only "
            "corrects the internal compiler gate that otherwise discards arbitrary PF3 tables. Canon selects the "
            "camera representation; validated EDSDK calls keep Canon's original buffer unchanged, while any "
            "unvalidated call is blocked before it reaches the camera."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#8A4C08;font-weight:600;")
        layout.addWidget(warning)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target"))
        self.target = QLabel("Automatic · original EOS Utility compiler and camera transport")
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

        self.steps = QLabel(
            "Workflow: export PF3 → identify that exact PF3 when EOS Utility opens it → correct Canon's internal "
            "table acceptance during its original compilation → validate both 33³ tables and compare the compiler "
            "output byte-for-byte with Canon's EDSDK buffer. Property 0x00000115 remains untouched."
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
        self.independent_button = QPushButton('Independent · experimental')
        self.independent_button.clicked.connect(lambda: IndependentInstallDialog(self.main,self).exec())
        buttons.addWidget(self.independent_button)
        buttons.addStretch()
        self.prepare_button = QPushButton("Prepare / Capture")
        self.prepare_button.setObjectName("AccentButton")
        self.prepare_button.clicked.connect(self.start_prepare)
        buttons.addWidget(self.prepare_button)
        layout.addLayout(buttons)

        self.refresh_summary()

    def append(self, text):
        self.log.append(str(text))

    def refresh_summary(self):
        base = dict(self.main.base_resolution or {})
        validity = "validated local PF3 base" if base.get("validated") else "Canon-serialized runtime base · experimental"
        active = sum(1 for item in self.main.luts if item.get("enabled") and item.get("opacity", 0) > 0)
        creative = self.main.controls_dict().get("creative") or {}
        axes = creative.get("color_axes") or {}
        creative_active = any(any(values.values()) for values in axes.values()) or creative.get("color_chrome") != "Off" or creative.get("color_chrome_fx_blue") != "Off" or creative.get("tone_curve") != [0.0, 0.25, 0.5, 0.75, 1.0]
        self.summary.setText(
            f"Current editor state: <b>{self.main.base_combo.currentText()}</b> · {validity} · "
            f"{active} active LUT layer(s) · Creative Color {'active' if creative_active else 'neutral'} · Canon 33³/12-bit export"
        )
        self.update_prepare_enabled()

    def prepare_block_reasons(self):
        reasons = []
        if not bool((self.main.base_resolution or {}).get("cameraReady")):
            reasons.append("Canon Picture Style Editor is required to generate the selected PF3 base")
        return reasons

    def update_prepare_enabled(self):
        armed = bool(self.installer and self.installer.armed)
        reasons = self.prepare_block_reasons()
        if reasons:
            self.requirements.setText("Before preparing:\n• " + "\n• ".join(reasons))
            self.requirements.setStyleSheet("color:#8A4C08;font-weight:600;")
        else:
            self.requirements.setText("✓ Ready to prepare the dynamic Canon camera workflow")
            self.requirements.setStyleSheet("color:#72D58A;font-weight:600;")
        # Keep the button clickable while prerequisites are missing so a click
        # explains the blockers instead of appearing to do nothing. Safety is
        # still fail-closed below and again inside the background installer.
        self.prepare_button.setEnabled(not self.preparing and not armed and not self.completed)
        self.independent_button.setEnabled(not self.preparing and not armed)

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
            dll = self.main.dll_path()
            base = self.main.current_base_path()
            base_info = dict(self.main.base_resolution or {})
            if not base_info.get("cameraReady"):
                raise RuntimeError("The selected PF3 base could not be generated with Canon EdsCFParse")
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
            project = self.main.project_document()
        except Exception as exc:
            QMessageBox.critical(self, "Cannot prepare camera installation", str(exc))
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_dir = exported_styles_dir()
        project_path = style_export_path(safe_file_stem(style_name))
        session_dir = logs_dir() / 'camera_install' / stamp
        pf3_path = session_dir / (safe_file_stem(style_name) + '.pf3')
        self.installer = EosRpInstaller(event_callback=lambda event:self.worker.signals.event.emit(event))
        self.preparing = True
        self.completed = False
        self.progress.setValue(0)
        self.log.clear()
        self.append("Current editor state captured on the UI thread.")
        base_label = "validated local template" if base_info.get("validated") else "Canon-serialized runtime template · experimental"
        self.append(f"Base: {base_style} · {base_label}")
        self.append(f"Persistent export folder: {output_dir}")
        self.update_prepare_enabled()
        def work():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.worker.signals.event.emit({"type":"stage", "message":"Exporting current Canon 33³ PF3…"})
            size, digest = export_pf3(
                dll, base, pf3_path, luts, controls, style_name,
                log=lambda message:self.worker.signals.event.emit({"type":"log", "message":str(message)}),
                progress=lambda value:None,
            )
            save_compiled_style_project(dll, base, project_path, project, pf3_path)
            self.worker.signals.event.emit({'type':'log', 'message':f'Style saved: {project_path}'})
            self.worker.signals.event.emit({"type":"pf3_ready", "size":size, "sha256":digest})
            return self.installer.prepare_and_arm(
                pf3_path, slot, style_name, session_dir, launch_eos=True,
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
            self.append("Legacy fixture compiler self-test passed.")
        elif kind == "ready":
            self.append("Canon native compiler acceptance + read-only EDSDK observer ready inside EOS Utility.")
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
        elif kind == "compiler_transport_match":
            if event.get("exact"):
                self.append(f"✓ Compiler output matches Canon's EDSDK buffer byte-for-byte · {event.get('size')} bytes")
            else:
                self.append("ERROR: Compiler output does not match Canon's outgoing EDSDK buffer")
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
        elif kind == "registration_return":
            self.append(
                f"Canon registration returned rc={event.get('rc')} · "
                "original buffer/size unchanged"
            )
        elif kind == "registration_blocked":
            self.append("BLOCKED BEFORE CAMERA WRITE: " + str(event.get("reason")))
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
        elif kind in {"install_error", "hook_error", "frida_error"}:
            self.append("ERROR: " + str(event.get("reason") or event.get("error")))
        elif kind == "disarmed":
            self.append("Camera hook disarmed.")

    def prepared(self, result):
        self.preparing = False
        self.progress.setValue(4)
        self.append("✓ ARMED · live target-PF3 validation is waiting; no external support files are required")
        self.append(f"PF3: {Path(result['pf3']).name}")
        self.append(f"Install report: {Path(result['reportPath']).name}")
        self.steps.setText(
            "FINAL STEP — In EOS Utility, register the generated PF3 normally to User Def. 1, 2 or 3. "
            f"Expected camera name: {result['styleName']}. EOS Utility will compile and send it normally while "
            "the app corrects and validates only the selected PF3 inside Canon's compiler. "
            "Do not close this window until success or until you intentionally disarm."
        )
        try:
            open_local_path(Path(result["pf3"]).parent)
        except Exception:
            pass
        self.update_prepare_enabled()

    def failed(self, message, trace):
        self.preparing = False
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
