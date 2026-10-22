# Own-transport RP compiler inputs — 2026-10-16

Initial scope: user authorized diagnostic requests, remote/event modes, reads
and cleanup. These diagnostic sessions performed no preset writes or raw-data
persistence. The separately authorized registration attempt and private style
backup are recorded at the end. No Canon process or DLL was started.

## Integrated acquisition

The existing `RemoteEventSession` now requests D17F via9127 and reads at most six
completed GetEvent drains. It does not use its initial event cache as a response.
Contradictory values fail instead of selecting the first/latest value. Malformed
descriptor or style data fails through the existing strict decoders; context
cleanup still disables both modes. This is protocol/session code without COM,
so it remains reusable by future platform adapters.

The existing standalone diagnostic exposes `--request-descriptor` and
`--request-slot 1|2|3`. The latter requests D170..172 and applies701d0's observed
event conversion. These are diagnostic reads, not a replacement for a9189 getter,
registration authorization or evidence of post-write freshness. DeviceInfo is
read with1001 through the same bounded transport when requesting a slot.

## Physical observations

Three successive separately opened own-WPD sessions completed after the initial
startup-only success. Private metadata reports are in
`../tmp/PF3_FIELD_EXPERIMENTS_20261004/`:

- `RP_INDEPENDENT_SESSION_20261016_02.json`: explicit D17F request succeeds,
  descriptor15076 bytes, modes/connection cleanup complete.
- `_03.json`: same request, version2000000b, SHA256
  `2bff34bc3d7cae7d6c65c5e930befe2e0d0920d725ca9fdb18acbb9c8a7aec60`.
  This equals the previously studied genuine RP descriptor. Live acquisition
  used no archived bytes as inputs. Version selects the existing modern importer;
  it does not establish serializer class, object flags or LUT acceptance.
- `_04.json`: DeviceInfo175 operation codes; neither9189 nor9192 nor918a is
  advertised. Explicit D170 request for slot1 returns a701d0-normalized16720-byte
  structure with validity1. SHA256
  `a136ba3254152b1c44fda5976299a190cecd6132712d7a231295c8c234923f32`.
  Both modes and connection cleanup complete.

The actual read contract matters: this RP does not advertise the direct9189
readback used by the existing synthetic confirmation tests. The event path now
has physical receive evidence, but equality/freshness/slot confirmation after
an authorized write still requires its own experiment. Never turn a successful
event request into an installation-success result.

## Remaining integration boundaries

The descriptor's encrypted matrix regions and PF3 source still require external
cipher keys. Raw live descriptor acquisition solves neither normalization nor
independent key derivation. Modern importer selection also does not prove the
compact cache-only route appropriate to this RP's arbitrary LUTs. The existing
offline cache compositor must not be automatically enabled from descriptor size
or model name.

The editor/fallback, RAW engine and build packaging are unchanged. The active
objective remains full independent compilation/registration/confirmation; this
checkpoint does not satisfy it. 610 discovered tests and changed-module
py_compile pass, including bounded missing/contradictory property requests and
private-data exclusion from diagnostic reports.

## Directed state request negative result and recovery

The next authorized experiment requested D163 explicitly after successful
descriptor/style requests. `9127(D163)` blocked inside synchronous WPD dispatch;
the bounded event loop was never reached. After the user disconnected/powered
the RP, the command returned driver HRESULT802A0006 and both mode-cleanup
attempts failed. `_06.json` records only failure metadata. The earlier `_05.json`
attempt stopped at absent-device selection before opening a connection.

Do not generalize successful9127(D17F/D170) to directed registration-state
acquisition. The speculative directed-state helper was removed. The shared
marshaller now rejects9127(D163..D165) before COM allocation, and the older
registration-state probe is disabled before Open. This guard requires protocol
attribution before removal; it is not a claim that all cameras lack that feature.
Startup state remains an observation, never a manufactured or replayable nonce.

After the user reconnected the RP, `_07.json` repeats only the validated
D17F/D170 path successfully, including both mode disables and connection Close.
No preset write occurred during either the blocked or recovered session.
Synchronous driver-call cancellation/time limits remain unresolved; bounded
event counts alone must not be described as a wall-clock timeout.

The earlier static note already attributed D163's handler flag0 and its reliance
on event population rather than generic9127 fallback. The directed experiment
was not justified by D17F/D170 success and should have remained outside the
generic request helper. The runtime block and disabled legacy probe now enforce
that distinction; this negative result is not a new compiler requirement.

## Live format inspection with reconstructed keys

`CHECKSUM_CIPHER_LIVE_OFFSET1_20261016.json` joins the private encrypted-corpus
checksum reconstruction to a new authorized live session. The process reads no
Canon DLL and persists neither keys nor camera bytes. The candidate decrypts
all four observed compact tables with valid packed10 upper-bit/unused-slot
geometry. Clear style/envelope/control markers also match the strict portable
`inspect_compact16752_style` grammar; this exceeds identification by size alone.
The observed base style is81, four10-node blocks. This does not prove cache/pixel
compiler path selection or arbitrary-LUT acceptance.

The live descriptor normalizes to14796 bytes plus an uninterpreted280-byte tail;
normalized SHA256 is
`e1af5fd5f6f3e2c257966e77b7966105e39c4d2f68df61ee282d5bb0a62f0031`.
Startup state metadata contains marker1 for all slots, selectors41/42/43 and
exact32-byte opaque controls. All controls existed only within that session.
Both temporary modes and the connection close successfully.

`_08.json` separately reads slot3 viaD172: normalized16720 bytes, validity1,
SHA256`0c6086390683ab343936da8bf27be2f4c9ed78add8ba9d7fd63b2c3d39d820c9`.
No state-property request or style write occurs.

## Portable registration execution and preflight

`registration_sequence_reference.execute_and_compare` now connects the existing
ordered style/state plan to the bounded write controller and a normalized-style
read callback. Writes require explicit opt-in; a failed style write prevents the
state write, a failed state write prevents comparison, and no write is retried.
The real fake-COM integration test now links PF3 decoding/compilation, startup
slot observation, both transfers, a requestedD171 event, content comparison and
mode cleanup. These tests do not establish physical write acceptance/freshness.

A private read-only preflight harness prepares the specific Classic_Cuban_Neg
export for slot3 and checks its original source/output hashes, actual DeviceInfo,
observed compact grammar and initial slot3 content. Actual writing remains behind
a separate flag and current human authorization. It obtains115 control anew from
the active session, does not save it, backs up the original style before a write
and requestsD172 after completed style/state transfers. No editor path or public
standalone release enables this experimental operation.

`RP_REGISTRATION_PREFLIGHT_20261016_01.json` completed in read-only mode with
stage`ready`, both cleanups complete and no style write. Candidate source SHA256
is`020692320372a007f0faf203810ff59397f930373f422bb13c52819edbc2a2b4`;
carrier SHA256 is
`4230866b11f05421f6303a8a7f750599264de288072b58de2a2bd50bd98d5642`.
Its expected normalized content hash is
`2d0756f47721c26b2e941e8e4c50a03f3f0804a729840129bc664acdecca6a3f`.
The plan contains two9110 transfers of16728 and52 bytes. The preflight does not
persist the opaque control or authorize using its old session state later;
an approved write reruns acquisition and checks the baseline has not changed.

Validation checkpoint:615 discovered tests, changed-module py_compile and
git diff whitespace checks pass. No physical registration result is claimed.

## Authorized registration attempt: transport timeout

The user explicitly authorized one experimental Classic_Cuban_Neg registration
in User Def.3 with a private baseline backup and subsequent D172 comparison.
`RP_REGISTRATION_ATTEMPT_20261016_01.json` records the single execution; it
reconstructed keys in memory, checked the reviewed source/carrier/baseline
hashes and obtained the opaque control from that newly opened session.
The baseline normalized style was saved privately before writing and verified
against SHA256
`0c6086390683ab343936da8bf27be2f4c9ed78add8ba9d7fd63b2c3d39d820c9`.
The backup excludes the opaque115 control.

The write controller reached WPD command17 completion and received HRESULT
`80070079` (timeout). Both remote/event cleanup stages also failed. No retry,
alternate opcode, rollback or second registration execution was attempted.
The generic traceback does not identify which of the two planned transfers
was completing: neither a completed style transfer nor execution of the state
transfer can be asserted. `styleWriteCompleted=false` means the full execution
and comparison did not complete; it does not prove that the camera retained
the old content. No D172 comparison or visual confirmation completed.

Physical power/USB recovery was requested before a separately opened read-only
D172 inspection. Until that result exists, User Def.3 content and acceptance of
the experimental compiler route remain unknown. The editor's independent mode
stays disabled; this failed experiment is not a build-release milestone.

The executor now adds a content-free style/state phase note to the original
transfer exception and reraises it unchanged, without retrying or entering the
next phase. Both failure phases and the fake-COM integration pass (8 focused
tests). This improves future attribution; it cannot recover the missing phase
from this attempt and is not a transport fix.

A review against Microsoft's [write-begin contract](https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/wpd-command-mtp-ext-execute-command-with-data-to-write)
and [write-data contract](https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/wpd-command-mtp-ext-write-data)
confirms the existing required input property types (UI8 total size, UI4 byte
count, byte-vector buffer). The driver-reported optimal write buffer size is
currently ignored. Neither this omission nor malformed candidate content is
established as the timeout cause; do not vary packets or retry on that basis.

After the user confirmed power/USB recovery,
`RP_POST_ATTEMPT_SLOT3_20261016_01.json` completed a newly opened read-only
session and explicit D172 request. Returned validity1,16720 bytes and SHA256
`0c6086390683ab343936da8bf27be2f4c9ed78add8ba9d7fd63b2c3d39d820c9`,
exactly the original baseline/backup and different from the candidate. Both
mode disables and connection Close completed. No additional style write was
attempted and no restoration is needed from this observed post-recovery state.
This proves unchanged requested slot content after restart, not the unobserved
transient state during the timed-out transaction or visual LUT acceptance.

Independent upstream cross-check: libgphoto2's
[`ptp_canon_eos_setdevicepropvalueex`](https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/ptp.c)
also sends9110 with no command parameters and a host-to-device data phase.
Its generic property setter frames total length/property code before the value.
This supports the operation-level framing; it does not validate this candidate's
style serialization, opaque control, camera route or WPD completion behavior.

## Identical-style isolation: PTP completion followed by Err70

The user separately authorized one unchanged-style transfer after reviewing its
16728-byte packet and two local success/failure checks. The private harness
`rp_identical_style_transport_20261016.py` first reread D172 and required exact
equality with the original backup; it used no compiler, cipher keys or115 state
write. Every phase was flushed immediately to
`RP_IDENTICAL_STYLE_ATTEMPT_20261016_01.jsonl`.

Begin14 completed; Write16 acknowledged16728 bytes; End17 returned PTP2001
after0.422 seconds. A requested D172 value still equaled the baseline. Temporary
mode cleanup then failed with a non-OK PTP response. The old generic command
exception discarded its numeric code, so this recording cannot identify that
response. The shared command adapter now includes the command opcode and actual
PTP response in the error; regression coverage retains the original completion
and proves no retry.

The user reported camera Err70 after this experiment. All device access stopped.
The user subsequently confirmed normal startup without USB after power/battery
recovery. No further device request or style write was made. User Def.3 has not
been reread after this Err70 recovery. The backup remains available, but neither
restoration nor a new installation is authorized by that recovery confirmation.
Both private experimental write flags now fail before opening a device or an
output report; isolated mock checks verify these gates.

PTP2001 is therefore transport completion only, not a safe/full registration
result. The style-only diagnostic omitted the state phase and UI-lock handling;
it was insufficient to establish a complete registration contract. The cause of
Err70 is not proved. A normal subsequent boot does not validate the experiment.

## Typed native-input review finds omitted UI lock boundary

`inspect_archived_wpd_20261016.py` deserializes all39 retained V25 RP WPD input
buffers through Windows' [IWpdSerializer](https://learn.microsoft.com/windows/win32/wpd_sdk/iwpdserializer).
All39 serialize back byte-for-byte. No device is instantiated/opened, no Canon
DLL runs, and no context string, style bytes or opaque control is persisted.
The report contains only schema/count/command/hash metadata:
`RP_ARCHIVED_WPD_INPUTS_TYPED_20261016.json`.

All ten native write-begins use command14/opcode9110 with an empty UI4 parameter
collection and UI8 total size (16728 for style;52 for state). This confirms the
existing WPD input types; it does not explain the physical failure.

Four complete archived input cycles (sequences8..15,16..23,24..31,32..39) show:
911B(1) -> style14/16/17 -> state14/16/17 ->911C(). The initial partial cycle
starts with style and ends in911C; its preceding lock is outside the recording.
Upstream [libgphoto2 names](https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/ptp.h)
identify911B/911C as SetUILock/ResetUILock. The captured one-argument lock is
typed evidence for this RP revision, not a universal argument convention.
These are archived **inputs**, not newly proved successful response/cleanup
boundaries. Missing UI lock is a concrete executor omission, not an established
cause of Err70 or permission for another physical test.

The injected executor now requires a command adapter, attempts the observed
lock before either transfer and releases once after both transfers or an
ambiguous lock/write failure. Failed locking prevents all data writes; failed
unlocking prevents content comparison. Primary errors survive failed release.
The full fake-COM integration checks lock/style/state/unlock/request order.

The executor now validates plan coherence before any UI-lock command: the
style slot and state handler must agree, selector metadata must match the
serialized state, and property/direct-operation framing must match the plan.
A reproduced mixed-slot plan previously reached the mocked transport. It now
fails before commands or transfers, without changing opaque state. All planned
slot/route/legacy-or-extended combinations retain their exact wire bytes in
offline tests.659 full-suite tests and py_compile pass. This hardening does
not identify the cause of Err70 or establish live registration acceptance.

## Complete archived style/state plan parity

The private `verify_registration_plan_archive_parity.py` joins the five native
EDSDK114/203/115 input groups to all ten typed WPD write buffers. Each input
file is hash-checked against the earlier Windows-serializer report; all39
retained WPD input records have exact serializer round trips. Plans generated
from the corresponding archived carrier/selector/control match both submitted
payload hashes and lengths for every pair:16728 style bytes and52 state bytes.
The32 opaque control bytes remain unchanged. The current executor accepts all
five plans with local mocks and preserves the lock/style/state/unlock/read
call contract. No device adapter is constructed or captured state sent to one.

Four complete cycles contain911B(1) before the pair and911C() after it. The
first cycle's preceding lock is outside the capture, not evidence of omission.
Private reports `RP_REGISTRATION_PLAN_ARCHIVE_PARITY.json` and
`RP_REGISTRATION_EXECUTOR_ARCHIVE_PARITY.json` persist only counts/booleans and
limitations. This proves submitted-input parity, not completed WPD responses,
live control freshness, post-write camera state or the cause of Err70. It does
not authorize retrying either failed physical experiment. The script passes
its assertions and py_compile without loading Canon resources or a runtime.
616 discovered tests pass. The revised executor remains physically unvalidated;
both private live-write gates and the disabled editor mode remain in force.

## Standalone read/compiler integration, 2026-10-17

The explicitly authorized `RP_FROZEN_PREFLIGHT_AUTHORIZED_01.json` records a
successful run of the new standalone diagnostic against the RP. The executable
read D17F and User Def.3, compiled the owned NC.pf3 locally, and constructed a
coherent style/state sequence (16728/52 bytes, state property D165). Shared pure
validation is now used by both preflight and the injected registration executor.
Opaque control remains in memory only; reports contain no state packet bytes.
Remote/event cleanup and connection cleanup completed, with no recovery needed.
No style or registration state was sent; state freshness and physical LUT
acceptance remain unproved. The standalone package excludes Canon resources,
native research loaders, Frida, Qt and RAW dependencies; isolated help starts
with external Python environment/path removed. This is not a clean-machine
installation test and does not validate registration or resolve prior Err70.

## State/header coherence and retained side events, 2026-10-17

The offline `verify_rp_basic_state_coherence.py` pairs all five captured203
setters with their immediately following115 setters. All30 comparisons match:
control offsets0/4/8/12/24/28 equal carrier offsets76/80/84/88/100/104.
The two intervening control words and complete state semantics remain unproved.
In particular this is not authority to patch115 or replay a captured value.
Preflight now rejects a current-slot control that disagrees with the candidate;
the earlier standalone report validated framing, not this newly added check.
The existing executable predates this additional gate.

Requested descriptor/style drains previously discarded other input events.
RemoteEventSession now retains bounded completed observations across requests
and rejects contradictions rather than silently retaining startup state.
Diagnostics use the updated snapshot after requests. Tests cover a side-state
arrival and a later conflicting state, including remote/event cleanup.
These changes involved no further physical camera operation.

## Integrated experimental registration controller

`independent_registration_reference.register_open_connection` now owns the
remote/event lifecycle on an explicitly supplied connection: verify advertised
operations, read descriptor/slot, compile the dense-pixel candidate, reread the
slot, reject state/header inconsistencies, exclusively save and fsync a baseline
style backup, lock/write style/write unchanged state/unlock, request and compare
content, then clean up remote/event modes. It never discovers or opens a device,
retries writes, replays stored control or automatically restores a preset.
The caller still needs a bounded isolated process and explicit physical consent.
The new test runs the actual compiler, session, sequence executor and WPD maps
with injected device replies, checking16728/52-byte writes and lifecycle order.
This is offline integration, not a live registration result. The saved style
alone is not a complete restoration transaction, and matching readback still
requires external visual confirmation. The editor fallback is unchanged.

## First authorized complete independent transport, 2026-10-17

The new standalone executable exposes writes only through the explicit
`--experimental-register` flag, with a required new baseline-backup path and
the existing isolated45-second supervisor. Read-only requests still open no
write-enabled data adapter. A killed registration worker reports unknown write
status rather than falsely claiming that nothing was sent.

`RP_AUTHORIZED_REGISTRATION_01.json` stopped before Open because discovery found
no WPD device. After the user explicitly confirmed readiness and authorized
resumption, `RP_AUTHORIZED_REGISTRATION_02.json` completed on the RP/User Def.3:
owned NC.pf3 SHA732d6b809f9c663edd2a8d8908ff392e0ede6e1deacc8dc4efb15b8c17c246dd,
dense-pixel compilation, unchanged observed control, baseline16720-byte backup,
style/state transfer, matching requested readback, completed remote/event and
connection cleanup. No Canon runtime was used, no retries or recovery needed.
The packet hash matches the earlier standalone preflight candidate exactly.
This is physical transport/readback evidence for this RP/profile/candidate,
not universal family coverage or proof that all state fields are understood.
Visual acceptance was requested from the user and remains pending. The report
keeps physicalAcceptanceEstablished=false rather than treating matching bytes
as proof of image appearance.673 regression tests and py_compile passed.

## User confirms visible Aerochrome; RP integration milestone

The user reported no errors and that NC appeared correct, then explicitly
authorized an Aerochrome test on the same slot. The old standalone Aerochrome
PF3 could not bootstrap itself in the frozen tool and was rejected before Open
(`RP_AUTHORIZED_AEROCHROME_01.json`). Its original bytes were then packaged in
an owned portable project with a mathematically generated identity reference,
using the independent writer and no Canon DLL. No LUT or control was changed.

`RP_AUTHORIZED_AEROCHROME_02.json` records a completed independent transfer and
matching requested readback of source SHA
5617bee4d983feb4e794d7c777f1be873f0cc49c61f4f029ac0c19a27b49d53b.
Both remote/event and connection cleanup succeeded, without retry or recovery.
The user explicitly confirmed: "Sim, Aerochrome visível e sem erros".
The private evidence sidecar `RP_VISUAL_ACCEPTANCE_20261017.json` distinguishes
this later human observation from the runtime's content-only confirmation.
Original transport reports remain unchanged.

This demonstrates the full independent compiler/session/registration/visible-LUT
flow for this RP/profile in the standalone tool. It does not establish exact
color matching, arbitrary Basic-control transitions, other families, a clean
Windows machine without installed Canon applications, or editor UI integration.
Those remaining requirements are not silently relabeled as complete.

## Experimental editor UI integration

Send to Camera now retains the EOS Utility path and offers a separate
Independent experimental dialog. It snapshots editor state on the UI thread,
exports with dll_path=None, packages the compiled style/reference, requires
explicit device/slot selection and write confirmation, then invokes the same
bounded isolated controller. Backups/project/reports remain in exported_styles.
The frozen editor dispatches camera workers before importing Qt, and catches
worker exceptions after report creation so windowed bootloader popups cannot
stall a failed worker. The former mandatory DLL check no longer blocks opening
the camera dialog when an independent project/base is available.

675 regression tests passed, plus the focused worker-popup regression. The
dialog was rendered and visually inspected offscreen. The unzipped private
editor build is CanonStyleStudio_Independent_RP_Experimental_20261017. Frozen
startup passed with external Python removed, empty portable storage and hidden
Canon discovery roots; source rejection in its frozen worker occurred before
camera Open without a popup. These are simulated absence/startup checks, not a
clean Windows deployment or a new physical registration through the editor UI.
