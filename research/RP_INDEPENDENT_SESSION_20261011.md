# Authorized RP session diagnostic

Scope authorized by the user: WPD discovery/open, temporary remote/event
modes, capability/event reads, cleanup. No style registration or preset writes.

Discovery returned one Canon EOS RP. The raw USB device identifier was not
printed or written into reports. Explicit fingerprint selection was added;
absent/ambiguous selections abort instead of choosing another device.

First run inside the restricted environment failed at IPortableDevice.Open
with HRESULT80073D54. No remote commands were reached.

The same diagnostic outside the restriction opened its own WPD connection
and passed vendor capability validation, including9114/9115/9116. The first
remote-mode command9114(1) failed at IPortableDevice.SendCommand with
HRESULT80070057, before a PTP completion was available. Its attempted
cleanup9114(0) also failed. Connection cleanup raised no additional error.
No successful remote-mode transition or cleanup transition is established.
No event data or live registration state was obtained. No style was sent.

Do not interpret this as camera registration support or as a Canon compiler
failure. The next transport investigation is the real WPD no-data request
marshalling/access policy. Do not repeat an installation attempt to diagnose it.

Private failure reports: RP_INDEPENDENT_SESSION_20261011_01.json and_02.json
in the PF3_FIELD_EXPERIMENTS_20261004 lab. They intentionally omit device IDs
and opaque camera data. Full offline suite after fingerprint selection:601
tests passed. Existing standalone diagnostic predates fingerprint selection;
the executed diagnostic here used current source, not that executable.

Reference for distinguishing SendCommand dispatch errors from driver-result
errors: https://learn.microsoft.com/en-us/windows/win32/api/portabledeviceapi/nf-portabledeviceapi-iportabledevice-sendcommand
