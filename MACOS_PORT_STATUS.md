# macOS port — local work, not a release

## Current source versus validated bundles — 27 October

Both current-source native jobs in
[run 40519938596](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/40519938596)
passed tests, packaging, bundle audit and frozen startup. Both DMGs were downloaded
and their artifact SHA-256 and ZIP CRC verified locally; see
`research/MACOS_CANDIDATES_20261027.json`. Their separate native
mount/signature/startup checks are running in
[run 40523856550](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/40523856550). Neither
candidate is a release, and no camera was accessed.

The DMG hashes below identify the 24 October source only. Later recipe-tone
changes and RAW reference research are not verified inside those bundles.
On Windows, the current source passed 36 portability, discovery, PTP and
recipe-tone tests (one native-only test skipped). Those checks use platform
doubles where necessary and do not establish native Cocoa or camera behavior.
The complete current-source suite also passed on Windows: 903 tests in 342
seconds, with one skip, using Qt offscreen. This does not validate a frozen app.
The existing candidate workflow discovers all tests, including the newer tone
and RAW reference tests, when a new native candidate is built. No new native
build or physical camera operation was performed for this local check.

The 24 October smooth-v5 source candidate includes the reorganized editor menus
and the corrected relative Nikon NP3 converter. Inversion retains extended RGB
before clipping, starts from known forward samples and regularizes colour-table
changes to limit numerical contours. It requires a separately supplied, validated
coefficient file; no Nikon profile data or DLL is bundled. Nikon RAW development
and sharpening are excluded. Both updated native architectures ran 851 tests with
three skips and no failures, plus 102 platform integration tests, then built,
passed the bundle audit and started their frozen Cocoa interfaces in
[run 40130750021](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/40130750021).
The first Intel packaging attempt failed with `hdiutil: Resource busy`; one
controlled rerun succeeded without changing the source.
Both exact downloaded DMGs were subsequently mounted read-only on their native
architectures, their signatures verified and their Cocoa interfaces started in
[run 40134516386](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/40134516386).
The proof hashes match the local DMGs in `LOCAL_MACOS_SMOOTH_CANDIDATES_20261024`:

- Apple Silicon: `39c560a8048b9671c175895cb47c0bace0e5af1eb9230d3fd5405f32adea0cc7`.
- Intel: `54902b2538647b9223c6d30c48b218fc349cbdd1ffbd3381adf5396535cbf5d3`.

The earlier results below are historical.
These checks did not access a camera; physical Mac USB validation, interactive
user acceptance and notarization remain outstanding. Mac installation stays disabled.

The hosted build now uses the reorganized `tests.*` module names and explicitly
runs the NP3 reader, profile validation, conversion and import tests. The frozen
bundle audit also requires the NP3 modules on both architectures.

The editor uses the same six included basic PF3 files, independent serializers
and editable project format as Windows. Native macOS state belongs in
`~/Library/Application Support/CanonStyleStudio`, caches in
`~/Library/Caches/CanonStyleStudio`, and user styles remain flat documents in
`~/Documents/Canon Style Studio PF3`. The explicit portable-root override is
retained. Folder buttons use the system desktop service.

`build_macos.py` builds an app bundle and a local disk image on macOS. Use an
environment containing the application and build dependencies, then run:

```sh
python build_macos.py --arch arm64
# In a separate native Intel environment:
python build_macos.py --arch x86_64
```

`--arch universal2` requires universal builds of Python and all native
dependencies; PyInstaller checks those slices. It is not an Intel binary
renamed as an Apple Silicon build. See [PyInstaller's macOS architecture
support](https://pyinstaller.org/en/stable/feature-notes.html#macos-multi-arch-support).
The local app is ad-hoc signed after its usage strings are written, verified,
and marked as not notarized or approved for publication. Existing output is
not overwritten. There is no upload or release step.

Before producing a bundle, the Mac builder now checks that the installed PyObjC
bridge exposes completion metadata for session open, session close and PTP
transactions. This check never creates a browser or accesses a device. The
bridge version and check result enter the build manifest. The PTP module is an
explicit hidden import so it is retained even while installation is disabled.

The Mac USB adapter is implemented in source using ImageCaptureCore/PTP and
the shared session controller. Its real camera transactions remain unverified. Apple's
[PTP command API](https://developer.apple.com/documentation/imagecapturecore/iccameradevice)
is the native boundary used by the adapter. No Mac camera session has been opened.
The retained Canon-native fallback is available only on Windows. Canon DPP
rendering is also a separate Windows implementation; it is not a dependency
of PF3 generation or JPEG/LUT editing.

Native hosted validation now runs on both Mac architectures in the authorized
test branch. On 20 October 2026, both Apple Silicon and Intel passed 782 tests
(three Windows tests skipped per architecture), built and audited ad-hoc signed
apps and DMGs, and passed the frozen worker's missing-input check without device
discovery. Both downloaded artifact digests and ZIP CRCs matched. A separate
native Cocoa startup check mounted those exact DMGs read-only, verified their
architectures and signatures, and launched each compiled interface successfully.
Its recorded DMG hashes match the local copies. Interactive use and specifically
authorized physical USB validation remain outstanding; these candidates are not releases.

## Manual hosted builds

`.github/workflows/macos-candidate.yml` prepares separate native builds on
GitHub's `macos-15` (Apple Silicon) and `macos-15-intel` runners. It starts only
with `workflow_dispatch` or a push to the explicitly authorized test branch
`codex/macos-candidate-20261020`, uses read-only repository permissions and never
creates a release. A run installs dependencies, checks the host architecture,
runs the regression suite, builds and audits the app, and checks that a missing
PF3 fails in the frozen worker before device discovery. Successful DMGs become
temporary workflow artifacts, retained for seven days. No camera access is
requested. The successful builds for both architectures are recorded in
[run 39408692557](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/39408692557).
`macos-validate-candidate.yml` reused that run's DMGs to check native Cocoa startup
without rebuilding them in [run 39412093234](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/actions/runs/39412093234).
Startup smoke checks do not replace interactive GUI or physical USB testing.

## Native USB implementation boundary

Apple's `ICDeviceBrowser` provides camera discovery without opening a session.
Filter local cameras and use `ICDevice.usbVendorID` for Canon identification;
do not depend on a model-name allowlist. Keep the selected native device alive
for the session instead of treating the Windows WPD device ID as portable.

`ICCameraDevice.requestSendPTPCommand` is asynchronous and requires the
`ICCameraDeviceCanAcceptPTPCommands` capability. Its callback supplies incoming
data, a response and an error. The Mac adapter must validate all three before
returning to the shared controller. It cannot reuse WPD transfer contexts or
apply USB bulk data framing to Apple's separate data argument. The command and
response codecs now reuse `ptp_wire.Container`/`Decoder`, following the original
[PTPPT ImageCaptureCore command implementation](https://github.com/watr/PTPPT/blob/master/PTP/PTPOperation.swift)
and [response implementation](https://github.com/watr/PTPPT/blob/master/PTP/PTPOperationResponse.swift).
This is implementation evidence, not a native validation of our adapter. A Mac
round trip remains required before any registration route is enabled.

Discovery, session opening, PTP transactions and session closing must run inside
the existing bounded worker. A timeout must terminate that worker without an
automatic write retry. The GUI must retain explicit camera and slot selection.
No Mac USB path is currently enabled or physically validated.

`camera_install/macos_discovery.py` now implements this explicit native scan,
with lazy framework imports, a main-thread requirement, a bounded enumeration
deadline and unconditional browser shutdown. It returns Canon USB summaries
with hashed identifiers; it never opens a session. The source package and
macOS-only dependency marker include it. `enumerate_isolated()` invokes a
dedicated worker with an eight-second process deadline and no retry. The frozen
entry point dispatches this worker before importing Qt; reports are private,
bounded and validated before returning. The GUI's explicit Find USB cameras
action now invokes this worker on macOS and displays discovered camera names.
Installation stays disabled with a visible development status pending native
validation of the PTP session controller. Windows discovery and installation keep
their existing path. Windows tests cover identity handling, platform
refusal, completion, timeout cleanup, worker invocation and invalid reports
using framework/process doubles, plus the Mac GUI routing and disabled install
action; native discovery and real camera transactions remain unverified.

API references: [device browser](https://developer.apple.com/documentation/imagecapturecore/icdevicebrowser),
[USB vendor identification](https://developer.apple.com/documentation/imagecapturecore/icdevice),
[PTP command and callback](https://developer.apple.com/documentation/imagecapturecore/iccameradevice/requestsendptpcommand(_:outdata:sendcommanddelegate:didsendcommand:contextinfo:)).

`camera_install/macos_ptp.py` implements the native asynchronous transaction
boundary for an already-open, explicitly authorized session. It checks the PTP
capability, bounds command/outgoing/incoming buffers, waits on the native run
loop and returns the response and data separately. It never retries and ignores
late callbacks after timeout. Timeout requires termination of the owning worker;
it does not claim to cancel an OS transaction. Callback success is not PTP or
registration success. `authorized_session` now owns one explicitly authorized
open/close cycle, rejects pre-existing sessions and attempts closure after
ordinary failures while preserving the original exception. A timed-out operation
requires worker termination without overlapping close IPC. `exchange` now
encodes bounded commands, checks a single complete response with the matching
transaction ID, keeps data separate and raises the shared `PtpCommandError` on
non-OK status without retry. `Transactions` now owns the per-session sequence,
rejects reentrant/cross-thread use and becomes unusable after timeout or malformed
transport completion. `selected_camera` now resolves exactly one Canon device
from the selected fingerprint and retains the browser/native object for the
caller scope; absent, duplicate and non-Canon selections fail before opening.
Valid PTP error responses still permit explicit cleanup
with the next transaction ID. Shared read/write controllers accept its atomic
data phases, retaining the WPD chunk path for Windows. `open_selected` composes
selection, authorized session ownership and transaction invalidation on scope
exit. Command control and outgoing data require separate explicit policies;
read-only owners reject both before native I/O. The session closes before the
browser is released. `connection_profile` now supplies shared adapters and
capabilities to diagnostic and registration controllers. Windows retains its
validated WPD capability query; Mac reads DeviceInfo once and retains both the
complete operation list and vendor operations. Existing required-operation
checks run before remote modes or registration. The isolated session worker now
routes macOS fingerprints to `open_selected` for both diagnostic and explicit
experimental registration paths, while Windows keeps WPD. Mac rejects WPD device
IDs, retains Python site initialization for PyObjC in source workers and uses
the same global process deadline. Discovery failures report no attempted open.
The GUI's Mac install action remains disabled pending native validation.
Tests use native
framework doubles for session and PTP calls. Framework completion metadata has
passed on native Apple Silicon and Intel hosts; real camera round trips remain unverified.
