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

## WPD access correction — 2026-10-16

Offline investigation found that `_new_mtp_params` forced FILE_READ_ACCESS
for command12 as well as read commands. The diagnostic also opened the device
with GENERIC_READ. Microsoft documents that the driver checks the IOCTL access
against the command payload and can reject a mismatch. This is a plausible
explanation for the earlier E_INVALIDARG, not a physically confirmed diagnosis.

The local Windows `System32/Drivers/UMDF/WpdMtpDr.dll`, SHA256
`2f9f035cea3659e0e91bd19866154c9d4b928f13120a0e28dd0bac07be439cb2`,
contains a contiguous 44-byte-stride table matching the SDK's
WPD_COMMAND_ACCESS_LOOKUP_ENTRY layout. File offsets dc3ec/dc444/dc470/dc49c/
dc4c8/dc4f4/dc520 contain MTP command11..17 respectively, with access words
1/3/1/3/1/3/1 and null access-property keys. This is static table evidence for
this Windows driver revision; it does not establish camera acceptance.
No Windows or Canon DLL was loaded for this inspection, copied or modified.

The shared marshaller now requests access3 for command12/14/16, access1 for
read/query/end commands. Session diagnostics explicitly request control access
when opening WPD. `allow_control=True` does not enable data-phase style writes;
those still require separate `allow_write=True`. Existing read-only connection
defaults and the editor's Canon fallback remain unchanged. Both older opt-in
temporary-session probe callers now open with the corresponding access too.

Separately, Microsoft declares MTP response parameters optional. The sender
now accepts only ERROR_NOT_FOUND (80070490) as absence of that property, returning
an empty tuple. Wrong types, null collections, other HRESULTs and missing required
capabilities/response codes still fail. This cannot explain an earlier dispatch
failure because it runs only after SendCommand returns.

Validation: 604 discovered tests pass, including a real Windows system-COM test
that constructs and reads back operation parameters and access flags without
creating/opening a device. Changed Python modules pass py_compile. No independent
cipher bootstrap, RP registration/readback or RAW/DPP independence is established.

The user authorized only discovery/open, temporary remote/event commands, reads
and cleanup on 16 October. The first authorized enumeration returned no WPD
devices. After the user connected the RP, fingerprint-selected discovery found
one Canon EOS RP and the corrected standalone source diagnostic succeeded:

- Own WPD Open and capability query completed without a Canon runtime.
- 9114(1), 9115(1), bounded 9116 read and transfer completion succeeded.
- One completed startup batch contained 12816 event bytes and D116=80000433.
- The existing decoder extracted slot handlers21/22/23 from observed state.
- No D17F descriptor was present (`descriptorBytes=null`). Route negotiation
  is still incomplete; do not guess a compiler route from the camera name.
- 9115(0), 9114(0), connection Close and COM cleanup completed.
- No style registration, payload write, preset selection or readback occurred.

Private metadata-only report:
`../tmp/PF3_FIELD_EXPERIMENTS_20261004/RP_INDEPENDENT_SESSION_20261016_01.json`.
No raw events, descriptor, opaque control or device identifier was persisted.
The successful run confirms the corrected transport reaches this physical RP;
it does not prove which individual change was necessary, state freshness for
a future registration, independent compilation or family-wide compatibility.
Startup state must not be replayed in a later session. Registration remains
unauthorized. No EOS Utility or Canon DLL was started by this diagnostic.

Sources:
- https://learn.microsoft.com/en-us/windows-hardware/drivers/portable/access-control
- https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/wpd-command-mtp-ext-execute-command-without-data-phase
- https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/PortableDevice.h
