"""Explicit opt-in session diagnostic, no style registration or Canon DLLs.

No device activity occurs on import. CLI requires a device ID and explicit
consent flag. Reports contain sizes/codes only, no opaque state or descriptors.
"""
import argparse
import json
from pathlib import Path
from .wpd_connection import WpdConnection
from .wpd_data_phase_reference import COMMON, MTP, CommandPropertyMapAdapter, ReadPropertyMapAdapter
from .remote_session_reference import RemoteEventSession
from .event_mode_plan_reference import plan_event_modes
from .windows_wpd_probe import enumerate_portable_devices


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


def inspect_open_connection(connection):
    """Caller must have authorization for real temporary remote/event modes."""
    result = connection.capabilities({(COMMON, 1001): MTP, (COMMON, 1002): 11})
    error = result.get((COMMON, 1003))
    if type(error) is not int or not 0 <= error <= 0xffffffff or error & 0x80000000:
        raise RuntimeError('Vendor capability query failed or omitted HRESULT')
    codes = result.get((MTP, 1005))
    if (type(codes) is not tuple or len(codes) > 4096
            or any(type(code) is not int or not 0 <= code <= 0xffff for code in codes)):
        raise RuntimeError('Missing or invalid vendor capability collection')
    if not {0x9114, 0x9115, 0x9116}.issubset(codes):
        raise RuntimeError('Required remote/event operations were not advertised')
    commands = CommandPropertyMapAdapter(connection.commands)
    reader = ReadPropertyMapAdapter(connection.data)
    plan = plan_event_modes(1, helper_predicate=True, registry_option_enabled=False)
    with RemoteEventSession(commands, reader, plan) as session:
        inputs = session.observed_inputs
        report = dict(format='CanonStyleStudio.IndependentSessionDiagnostic',
            version=1, styleRegistrationAttempted=False, canonRuntimeUsed=False,
            stateFreshnessEstablished=False, vendorOperations=[hex(code) for code in codes],
            cameraId=None if inputs.camera_id is None else hex(inputs.camera_id),
            descriptorBytes=None if inputs.raw_descriptor is None else len(inputs.raw_descriptor),
            observedSlotHandlers=[hex(slot.handler_selector) for slot in inputs.slots],
            eventBatches=session.startup_events.batch_count,
            eventBytes=session.startup_events.received_bytes,
            propertyCodes=[hex(event.property_code) for event in session.startup_events.properties])
    report['temporaryModesCleanupCompleted'] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--device-id')
    selection.add_argument('--device-fingerprint', help='Explicit fingerprint from WPD discovery')
    parser.add_argument('--allow-temporary-session', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_temporary_session:
        parser.error('Explicit permission for temporary remote/event modes is required')
    # Reserve a new output before opening anything; never overwrite a report.
    with args.output.open('x', encoding='utf-8') as stream:
        try:
            device_id = args.device_id or resolve_fingerprint(args.device_fingerprint)
            with WpdConnection(device_id) as connection:
                report = inspect_open_connection(connection)
            report['connectionCleanupCompleted'] = True
        except Exception as error:
            # Do not include exception strings that could expose a device ID.
            json.dump(dict(failed=True, exceptionType=type(error).__name__,
                           styleRegistrationAttempted=False), stream, indent=2)
            raise
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
