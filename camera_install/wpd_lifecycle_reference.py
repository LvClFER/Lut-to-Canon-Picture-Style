"""Injected WPD/GIT cleanup reference; no COM, OS, camera or global objects.

Acquisition -> Close -> Revoke -> Release follows the observed kind2 path.
Unlike the native path, failures are reported after attempting all cleanup.
This helper does not open anything or authorize registration.
"""


def close_registered_device(table, cookie):
    """Injected table has get(cookie)/revoke(cookie), device close()/release().

    close/revoke return HRESULT integers. get/release raise on failure.
    The cookie is a process-local COM handle, never a camera transaction ID.
    """
    if type(cookie) is not int or not 0 < cookie <= 0xffffffff:
        raise ValueError('Require nonzero process-local cookie')
    device = None
    failures = []
    try:
        try:
            device = table.get(cookie)
            if device is None:
                raise RuntimeError('No acquired device interface')
            result = device.close()
            if type(result) is not int or not 0 <= result <= 0xffffffff or result & 0x80000000:
                raise RuntimeError('Device Close failed')
        except Exception as error:
            failures.append(error)
        try:
            result = table.revoke(cookie)
            if type(result) is not int or not 0 <= result <= 0xffffffff or result & 0x80000000:
                raise RuntimeError('Interface cookie revocation failed')
        except Exception as error:
            failures.append(error)
    finally:
        if device is not None:
            try:
                device.release()
            except Exception as error:
                failures.append(error)
    if failures:
        raise RuntimeError(f'WPD cleanup incomplete: {len(failures)} failed stage(s)') from failures[0]
