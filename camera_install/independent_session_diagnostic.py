"""Isolated independent diagnostic; registration requires a separate explicit flag.

No device activity occurs on import. CLI requires a device ID and explicit
consent flag. Reports contain sizes/codes only, no opaque state or descriptors.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from .wpd_connection import WpdConnection
from .wpd_data_phase_reference import PtpCommandError
from .registration_sequence_reference import ui_lock
from .remote_session_reference import RemoteEventSession
from .event_mode_plan_reference import plan_event_modes
from .windows_wpd_probe import enumerate_portable_devices
from .mtp_read_reference import receive
from .ptp_device_info_reference import decode as decode_device_info
from .connection_profile import load as load_connection_profile


def resolve_fingerprint(fingerprint):
    """Discover only; require an explicit unique Canon fingerprint, no Open."""
    if (type(fingerprint) is not str or len(fingerprint) != 16
            or any(char not in '0123456789abcdef' for char in fingerprint)):
        raise ValueError('Require the16-character lowercase discovery fingerprint')
    matches = []
    def select(device_id, summary):
        if summary.get('canonCandidate') and summary.get('idFingerprint') == fingerprint:
            matches.append(device_id)
    enumerate_portable_devices(_on_device=select)
    if len(matches) != 1:
        raise RuntimeError('Selected Canon device is absent or ambiguous')
    return matches[0]


def inspect_open_connection(connection, *, request_descriptor=False, request_slot=None, test_ui_lock=False, preflight_source=None):
    """Caller must have authorization for real temporary remote/event modes."""
    if type(request_descriptor) is not bool or type(test_ui_lock) is not bool:
        raise ValueError('Require explicit descriptor-query policy')
    if request_slot is not None and (type(request_slot) is not int or request_slot not in (1, 2, 3)):
        raise ValueError('Require explicit user slot1..3')
    if preflight_source is not None and (not request_descriptor or request_slot is None):
        raise ValueError('Compiler preflight requires an explicit descriptor and slot request')
    profile=load_connection_profile(connection)
    codes=profile.operations
    if not {0x9114, 0x9115, 0x9116}.issubset(codes):
        raise RuntimeError('Required remote/event operations were not advertised')
    if (request_descriptor or request_slot is not None) and 0x9127 not in codes:
        raise RuntimeError('Property request operation was not advertised')
    if test_ui_lock and not {0x911b, 0x911c}.issubset(codes):
        raise RuntimeError('UI lock operations were not advertised')
    commands,reader=profile.commands,profile.reader
    info = (profile.device_info or decode_device_info(receive(reader,0x1001))) if request_slot is not None or test_ui_lock else None
    if test_ui_lock and not {0x911b, 0x911c}.issubset(info.operations):
        raise RuntimeError('DeviceInfo did not advertise UI lock operations')
    plan = plan_event_modes(1, helper_predicate=True, registry_option_enabled=False)
    with RemoteEventSession(commands, reader, plan) as session:
        inputs = session.observed_inputs
        descriptor = session.request_descriptor() if request_descriptor else inputs.raw_descriptor
        style = session.request_slot_style(0x20 + request_slot) if request_slot is not None else None
        matching = None
        if test_ui_lock:
            with ui_lock(commands):
                pass
            if request_slot is not None:
                after = session.request_slot_style(0x20 + request_slot)
                matching = after == style
                if not matching:
                    raise RuntimeError('Requested slot content differed after UI lock cycle')
        inputs = session.observed_inputs
        report = dict(format='CanonStyleStudio.IndependentSessionDiagnostic',
            version=1, styleRegistrationAttempted=False, canonRuntimeUsed=False,
            stateFreshnessEstablished=False, vendorOperations=[hex(code) for code in codes],
            uiLockTestRequested=test_ui_lock, uiLockCycleCompleted=test_ui_lock,
            requestedSlotContentMatched=matching,
            cameraId=None if inputs.camera_id is None else hex(inputs.camera_id),
            descriptorBytes=None if descriptor is None else len(descriptor),
            descriptorRequested=request_descriptor,
            descriptorSha256=None if descriptor is None else hashlib.sha256(descriptor).hexdigest(),
            descriptorVersion=None if descriptor is None or len(descriptor) < 4
                else hex(int.from_bytes(descriptor[:4], 'little')),
            requestedSlot=request_slot,
            slotStyleEventBytes=None if style is None else len(style),
            slotStyleEventSha256=None if style is None else hashlib.sha256(style).hexdigest(),
            slotStyleEventValidity=None if style is None else int.from_bytes(style[:4], 'little'),
            deviceOperations=None if info is None else [hex(code) for code in info.operations],
            observedSlotHandlers=[hex(slot.handler_selector) for slot in inputs.slots],
            eventBatches=session.startup_events.batch_count,
            eventBytes=session.startup_events.received_bytes,
            propertyCodes=[hex(event.property_code) for event in session.startup_events.properties])
    report['temporaryModesCleanupCompleted'] = True
    if preflight_source is not None:
        # Compile only after remote/event cleanup; no data-phase writes exist here.
        from .family_registration_reference import prepare_family_registration,prepare_family_sequence
        try:
            _job, candidate = prepare_family_registration(*preflight_source,camera_id=inputs.camera_id,
                descriptor=descriptor,slot_style=style,slot=request_slot,
                vendor_operations=codes,device_operations=info.operations)
            try:
                sequence=prepare_family_sequence(_job,inputs.slots)
                candidate.update(sequencePlanValidated=True,statePacketBytes=len(sequence.state.data),
                    stateProperty=hex(sequence.state.property_code),writeAuthorized=False)
            except ValueError as error:
                candidate.update(sequencePlanValidated=False, sequenceBlockedReason=str(error))
        except ValueError as error:
            candidate = dict(compilerProfileMatched=False,blockedReason=str(error))
        candidate['selectedSlotStateObserved'] = any(
            value.handler_selector==0x20+request_slot and value.marker==1
            and value.selector==0x40+request_slot and len(value.control)==32 for value in inputs.slots)
        candidate['writeAuthorized'] = False
        candidate['liveRegistrationEnabled'] = False
        report['compilerPreflight'] = candidate
    return report


def _worker_command(args, output):
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        if sys.platform!='darwin' and not getattr(args,'preflight_style',None):
            command.append('-S')
        command.append(str(Path(__file__).resolve().parents[1] / 'independent_camera_diagnostic.py'))
    command += ['--session-worker', '--allow-temporary-session', '--output', str(output)]
    command += (['--device-id', args.device_id] if args.device_id
                else ['--device-fingerprint', args.device_fingerprint])
    if args.request_descriptor:
        command.append('--request-descriptor')
    if args.request_slot is not None:
        command += ['--request-slot', str(args.request_slot)]
    if args.test_ui_lock:
        command.append('--test-ui-lock')
    if getattr(args,'preflight_style',None):
        command += ['--preflight-style',str(args.preflight_style)]
    if getattr(args,'experimental_register',False):
        command += ['--experimental-register','--baseline-backup',str(args.baseline_backup)]
    if getattr(args,'update_known_basic_controls',False):
        command.append('--update-known-basic-controls')
    return command


def _run_isolated(args):
    """A stuck driver never causes an unbounded parent wait or an automatic retry."""
    registration = getattr(args,'experimental_register',False)
    report = dict(format='CanonStyleStudio.IndependentSessionDiagnostic', version=1,
        failed=True, styleRegistrationAttempted=None if registration else False, canonRuntimeUsed=False,
        registrationRequested=registration,
        workerDeadlineSeconds=args.timeout_seconds, workerDeadlineExceeded=False,
        requestedSlot=args.request_slot, uiLockTestRequested=args.test_ui_lock,
        descriptorRequested=args.request_descriptor,
        workerMayStillBeRunning=False, automaticRetry=False,
        temporaryModesCleanupCompleted=None, connectionCleanupCompleted=None)
    directory = Path(tempfile.mkdtemp(prefix='canon_session_diagnostic_'))
    process = None
    exit_code = 1
    try:
        child_report = directory / 'report.json'
        process = subprocess.Popen(_worker_command(args, child_report),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        report['workerPid'] = process.pid
        try:
            exit_code = process.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            report['workerDeadlineExceeded'] = True
            exit_code = 124
        if not report['workerDeadlineExceeded'] and child_report.is_file():
            with child_report.open('rb') as stream:
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('Diagnostic worker report exceeds limit')
            result = json.loads(raw)
            if registration and exit_code == 0 and getattr(args,'update_known_basic_controls',False):
                changes=result.get('knownBasicControlChanges')
                if (result.get('knownBasicControlUpdateEnabled') is not True
                        or type(changes) is not list
                        or (changes and result.get('requestedSlotStateMatched') is not True)):
                    raise ValueError('Missing Basic control update confirmation')
            if (type(result) is not dict
                    or (not registration and result.get('styleRegistrationAttempted') is not False)
                    or (registration and exit_code == 0 and (
                        result.get('styleRegistrationAttempted') is not True
                        or result.get('requestedSlotContentMatched') is not True
                        or result.get('baselineStyleBackupSaved') is not True
                        or result.get('physicalAcceptanceEstablished') is not False
                        or result.get('visualConfirmationRequired') is not True))
                    or (exit_code == 0 and (result.get('temporaryModesCleanupCompleted') is not True
                                           or result.get('connectionCleanupCompleted') is not True
                                           or result.get('failed', False) is not False))):
                raise ValueError('Invalid diagnostic worker completion report')
            report.update(result)
        elif exit_code == 0:
            raise ValueError('Diagnostic worker omitted its completion report')
    except KeyboardInterrupt:
        report['workerInterrupted'] = True
        exit_code = 130
    except Exception as error:
        report['exceptionType'] = type(error).__name__
        exit_code = 1
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                pass
            report['workerMayStillBeRunning'] = process.poll() is None
        if not report['workerMayStillBeRunning']:
            shutil.rmtree(directory, ignore_errors=True)
        report['failed'] = exit_code != 0
        report['recoveryRequired'] = process is not None and report.get('deviceOpenAttempted') is not False and (
            report['temporaryModesCleanupCompleted'] is not True
            or report['connectionCleanupCompleted'] is not True)
        report['workerExitCode'] = None if process is None else process.poll()
        report['diagnosticExitCode'] = exit_code
        if registration:
            report['cameraContentUnconfirmed'] = exit_code != 0 or report.get('requestedSlotContentMatched') is not True
    return report, exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--device-id')
    selection.add_argument('--device-fingerprint', help='Explicit fingerprint from WPD discovery')
    parser.add_argument('--allow-temporary-session', action='store_true')
    parser.add_argument('--request-descriptor', action='store_true',
                        help='Also request D17F via9127; requires authorization for this query')
    parser.add_argument('--request-slot', type=int, choices=(1, 2, 3),
                        help='Read a slot via property events; does not confirm registration')
    parser.add_argument('--test-ui-lock', action='store_true',
                        help='Test one advertised911B(1)/911C() cycle; sends no style or115 state')
    parser.add_argument('--preflight-style',type=Path,
                        help='Owned PF3/project; compile locally only unless --experimental-register is explicit')
    parser.add_argument('--experimental-register',action='store_true',
                        help='EXPERIMENTAL: authorize style/state writes to the selected slot; may require camera recovery')
    parser.add_argument('--update-known-basic-controls',action='store_true',
                        help='EXPERIMENTAL: apply known source Basic values and require a matching state event')
    parser.add_argument('--baseline-backup',type=Path,
                        help='New baseline style backup file required for experimental registration; not a complete restore')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout-seconds', type=int, default=45,
                        help='Worker deadline1..120 seconds; shutdown wait is at most2 more seconds')
    parser.add_argument('--session-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.allow_temporary_session:
        parser.error('Explicit permission for temporary remote/event modes is required')
    if not 1 <= args.timeout_seconds <= 120:
        parser.error('Worker deadline must be1..120 seconds')
    if args.update_known_basic_controls and not args.experimental_register:
        parser.error('--update-known-basic-controls requires --experimental-register')
    if args.preflight_style and (not args.request_descriptor or args.request_slot is None):
        parser.error('Compiler preflight requires --request-descriptor and --request-slot')
    if args.experimental_register:
        if not args.preflight_style or args.baseline_backup is None or args.test_ui_lock:
            parser.error('Registration requires --preflight-style and --baseline-backup; no separate UI-lock test')
        if args.baseline_backup.exists() or args.baseline_backup.resolve()==args.output.resolve():
            parser.error('Baseline backup must be a new file distinct from the report')
        if not args.baseline_backup.parent.is_dir():
            parser.error('Baseline backup parent directory must already exist')
    elif args.baseline_backup is not None:
        parser.error('--baseline-backup requires --experimental-register')
    # Reserve a new output before opening anything; never overwrite a report.
    with args.output.open('x', encoding='utf-8') as stream:
        if not args.session_worker:
            report, exit_code = _run_isolated(args)
            json.dump(report, stream, indent=2)
            if exit_code:
                raise SystemExit(exit_code)
            return
        device_open_attempted = False
        try:
            with tempfile.TemporaryDirectory(prefix='canon_preflight_source_') as local:
                prepared = None
                if args.preflight_style:
                    from .rp_preflight_reference import load_preflight_source
                    prepared = load_preflight_source(args.preflight_style,Path(local)/'project')
                connection_policy = dict(allow_control=True)
                if args.experimental_register:
                    connection_policy['allow_write'] = True
                if sys.platform=='darwin':
                    if args.device_id:raise ValueError('macOS requires an explicit discovery fingerprint')
                    from .macos_ptp import open_selected
                    context=open_selected(args.device_fingerprint,allow_session=True,**connection_policy)
                else:
                    device_id = args.device_id or resolve_fingerprint(args.device_fingerprint)
                    context=WpdConnection(device_id,**connection_policy)
                device_open_attempted = True
                with context as connection:
                    if args.experimental_register:
                        from .independent_registration_reference import register_open_connection
                        report = register_open_connection(connection,prepared,slot=args.request_slot,
                            backup_path=args.baseline_backup,allow_experimental_write=True,
                            update_known_basic_controls=args.update_known_basic_controls)
                        report['canonRuntimeUsed'] = False
                    else:
                        report = inspect_open_connection(connection, request_descriptor=args.request_descriptor,
                            request_slot=args.request_slot, test_ui_lock=args.test_ui_lock,preflight_source=prepared)
            report['connectionCleanupCompleted'] = True
            report['deviceOpenAttempted'] = True
        except Exception as error:
            attempted=getattr(error,'device_open_attempted',None)
            if type(attempted) is bool:device_open_attempted=attempted
            # Do not include exception strings that could expose a device ID.
            failure = dict(failed=True, exceptionType=type(error).__name__,
                           styleRegistrationAttempted=None if args.experimental_register and device_open_attempted else False,
                           deviceOpenAttempted=device_open_attempted)
            if args.experimental_register:
                from .rp_preflight_reference import SlotControlMismatch
                from .family_registration_reference import FamilyCompatibilityError
                if isinstance(error,SlotControlMismatch):
                    failure.update(styleRegistrationAttempted=False,
                        blockedReason='Slot Basic controls differ; no style or registration state was sent.',
                        controlDifferences=error.differences)
                elif isinstance(error,FamilyCompatibilityError):
                    failure.update(styleRegistrationAttempted=False,blockedReason=str(error))
            for field,attribute in (('temporaryModesCleanupCompleted','temporary_modes_cleanup_completed'),
                                    ('connectionCleanupCompleted','connection_cleanup_completed')):
                value=getattr(error,attribute,None)
                if type(value) is bool:failure[field]=value
            current = error
            for _ in range(6):
                if isinstance(current, PtpCommandError):
                    failure.update(commandOpcode=hex(current.opcode), commandResponseCode=hex(current.response_code))
                    break
                current = current.__cause__
                if current is None:
                    break
            json.dump(failure, stream, indent=2)
            raise
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
