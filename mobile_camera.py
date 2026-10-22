"""Android worker entry point. Caller owns permission, process and 45 s deadline."""
import json
from pathlib import Path


def install(bulk, source, slot, backup):
    from camera_install.android_ptp import JavaBulk, Transactions
    from camera_install.rp_preflight_reference import load_preflight_source
    from camera_install.independent_registration_reference import register_open_connection
    if type(slot) is not int or slot not in (1, 2, 3):
        raise ValueError('Select User Def. 1, 2 or 3')
    backup = Path(backup)
    if backup.exists():
        raise ValueError('A camera backup must never be overwritten')
    # Validate the entire source before the first device transaction.
    prepared = load_preflight_source(source, backup.parent / 'source')
    owner = Transactions(JavaBulk(bulk), allow_control=True, allow_write=True)
    owner.next_transaction = 0  # USB PTP OpenSession uses transaction zero.
    owner.execute(0x1002, (1,))
    try:
        report = register_open_connection(owner, prepared, slot=slot,
            backup_path=backup, allow_experimental_write=True,
            update_known_basic_controls=True)
    finally:
        if not owner.unusable:
            owner.execute(0x1003)
        owner.unusable = True
    report['ptpSessionClosed'] = True
    report['platform'] = 'android'
    report['physicalAndroidValidationEstablished'] = False
    return json.dumps(report)
