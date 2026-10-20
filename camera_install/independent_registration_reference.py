"""Experimental session integration over injected adapters, never auto-discovery.

Caller owns the live session, deadline, physical authorization and cleanup.
Reconstructed compiler families share the session and confirmation controller.
Nothing runs on import and the editor's Canon fallback remains unchanged.
"""
import hashlib
import os
from pathlib import Path

from .family_registration_reference import prepare_family_registration, prepare_family_sequence
from .registration_sequence_reference import execute_and_compare
from .mtp_read_reference import receive
from .ptp_device_info_reference import decode as decode_device_info
from .remote_session_reference import RemoteEventSession
from .event_mode_plan_reference import plan_event_modes
from .camera_families_reference import camera_family
from .session_inputs_reference import SlotObservation
from .connection_profile import load as load_connection_profile


def register_open_connection(connection, source, *, slot, backup_path,
                             allow_experimental_write=False,update_known_basic_controls=False):
    """Own remote/event lifecycle on an explicitly opened, authorized connection.

    Caller must isolate the process and impose a deadline before real use.
    Opening/discovery and physical authorization are deliberately not inferred.
    """
    if type(allow_experimental_write) is not bool or not allow_experimental_write:
        raise ValueError('Experimental registration requires explicit write permission')
    if type(slot) is not int or slot not in (1,2,3):
        raise ValueError('Require explicit user slot1..3')
    if type(update_known_basic_controls) is not bool:
        raise ValueError('Require explicit boolean known-control update policy')
    try:profile=load_connection_profile(connection)
    except RuntimeError as error:raise ValueError('Missing verified registration operations') from error
    codes=profile.operations
    if not {0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127}.issubset(codes):
        raise ValueError('Missing verified registration operations')
    commands,reader,writer=profile.commands,profile.reader,profile.writer
    info = profile.device_info or decode_device_info(receive(reader,0x1001))
    required = {0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127}
    if not required.issubset(info.operations):
        raise ValueError('DeviceInfo did not advertise the complete registration profile')
    mode = plan_event_modes(1,helper_predicate=True,registry_option_enabled=False)
    with RemoteEventSession(commands,reader,mode) as session:
        report = register_in_session(session,source,writer,commands,slot=slot,
            vendor_operations=codes,device_operations=info.operations,backup_path=backup_path,
            allow_experimental_write=True,update_known_basic_controls=update_known_basic_controls)
    report['temporaryModesCleanupCompleted'] = True
    return report


def register_in_session(session, source, writer, commands, *, slot,
                        vendor_operations, device_operations, backup_path,
                        allow_experimental_write=False,update_known_basic_controls=False):
    """Read -> compile -> recheck -> backup -> lock/write/unlock -> compare.

    No retry, captured-state loading, unknown-word rewriting or automatic restoration.
    A matching readback is content evidence only; visual acceptance is external.
    Physical evidence covers RP NC/Aerochrome; other bodies remain experimental.
    """
    if type(allow_experimental_write) is not bool or not allow_experimental_write:
        raise ValueError('Experimental registration requires explicit write permission')
    if type(slot) is not int or slot not in (1,2,3):
        raise ValueError('Require explicit user slot1..3')
    if type(update_known_basic_controls) is not bool:
        raise ValueError('Require explicit boolean known-control update policy')
    identifier=session.observed_inputs.camera_id
    legacy=identifier is not None and camera_family(identifier)[0] in (1,2)
    descriptor = None if legacy else session.request_descriptor()
    baseline = session.request_slot_style(0x20 + slot)
    inputs = session.observed_inputs
    if legacy and camera_family(inputs.camera_id,baseline)[0] not in (1,2):
        descriptor=session.request_descriptor()
    job, report = prepare_family_registration(*source, camera_id=inputs.camera_id,
        descriptor=descriptor, slot_style=baseline, slot=slot,
        vendor_operations=vendor_operations, device_operations=device_operations)
    expected = job.carrier[:8] + job.carrier[40:]
    if baseline == expected:
        raise ValueError('Candidate already matches slot; cannot demonstrate a changed installation')
    # Compilation can take time: reject intervening content/state contradictions.
    if session.request_slot_style(0x20 + slot) != baseline:
        raise ValueError('Slot changed while compiling; no registration attempted')
    if update_known_basic_controls:
        sequence=prepare_family_sequence(job,session.observed_inputs.slots,update_known_basic_controls=True)
    else:sequence=prepare_family_sequence(job,session.observed_inputs.slots)
    before=next(s for s in session.observed_inputs.slots if s.handler_selector==0x20+slot)
    wire_length=32 if sequence.state.extended else 24
    control=sequence.state.data[-wire_length:]+before.control[wire_length:]
    after=SlotObservation(before.handler_selector,before.marker,before.selector,control)
    changes=[dict(control=name,slotValue=int.from_bytes(before.control[offset:offset+4],'little',signed=signed),
        candidateValue=int.from_bytes(control[offset:offset+4],'little',signed=signed))
        for name,offset,_value,signed in job.control_words
        if offset+4<=wire_length and before.control[offset:offset+4]!=control[offset:offset+4]]
    backup_path = Path(backup_path)
    # Exclusive creation and fsync must succeed before any lock/data write.
    with backup_path.open('xb') as backup:
        backup.write(baseline)
        backup.flush()
        os.fsync(backup.fileno())
    def read_back(handler):
        if changes:
            if handler!=before.handler_selector:raise ValueError('Registration confirmation slot differs')
            return session.request_registered_slot_style(before,after)
        return session.request_slot_style(handler)
    execute_and_compare(sequence,writer,commands,read_back,allow_write=True)
    report.update(styleRegistrationAttempted=True, requestedSlotContentMatched=True,
        baselineSha256=hashlib.sha256(baseline).hexdigest(), baselineStyleBackupSaved=True,
        physicalAcceptanceEstablished=False, stateFreshnessEstablished=False,
        visualConfirmationRequired=True, automaticRetry=False,
        knownBasicControlUpdateEnabled=update_known_basic_controls,knownBasicControlChanges=changes,
        requestedSlotStateMatched=True if changes else None,
        limitation='Experimental family integration; baseline style backup is not a complete restoration transaction.')
    return report
