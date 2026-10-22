# RP UI-lock diagnostic: proposed scope, no execution authorization

All camera access remains stopped after Err70. This document and the new CLI
option do not authorize opening the camera. A new current user authorization
is required before running the following sequence on the recovered RP.

## Purpose and supporting evidence

Four complete archived RP input cycles show911B(1), style transfer, opaque-state
transfer, then911C(). The previous style-only experiment omitted these boundaries
and was followed by Err70. Their omission is established; causation is not.
The existing physical metadata report `RP_INDEPENDENT_SESSION_20261016_04.json`
advertises911B and911C in both vendor capabilities and DeviceInfo. The new test
must check both again rather than trusting an old report or a model registry.

The narrow next question is whether the RP completes an empty lock/unlock cycle
inside our own remote/event session and completes normal cleanup afterward.
This neither sends a LUT nor validates registration, arbitrary-LUT acceptance,
the compiler route, state freshness or visual output.

## Exact opt-in sequence

The CLI selection must identify only the explicitly selected RP fingerprint.
Its parent reserves a new metadata-report path before launching one child.

1. Enumerate and require a unique matching Canon fingerprint; open WPD control
   access with style-data writing disabled.
2. Query vendor capabilities and DeviceInfo. Require remote/event support,
   property requests,911B and911C before enabling modes.
3. Enable remote1 and event1; drain the bounded startup batch.
4. RequestD172 and decode the selected User Def.3 observation into memory.
5. Issue911B(1), then911C() once. A failed/ambiguous lock gets one release
   attempt; errors are retained and no alternate opcode or retry is attempted.
6. RequestD172 again and compare the observations in memory. Equality remains
   content evidence only, not a proof of fresh state or registration.
7. Disable event mode, disable remote mode and close the WPD connection.

There are no9110/9192/918A style transfers, no115 writes and no directed
D163..D165 requests. No PF3, descriptor, style pixels or opaque control is saved.
The report contains sizes, hashes, completion flags and safe PTP opcode/status
metadata. It does not contain the USB device ID, serial or driver stdout.

## Driver deadline and uncertain cleanup

The parent waits45 seconds by default, then requests termination of its child
and waits at most2 more seconds. It never uses an unbounded post-kill wait.
A driver/OS that does not finish termination is reported with the worker PID
and `workerMayStillBeRunning=true`; no replacement worker is started.

A timeout/interrupt/crash cannot prove the camera released temporary modes.
Cleanup flags remain unknown, recovery is required and the test is not retried.
Only a normal report after all mode disables and connection close may indicate
completed cleanup. This does not guarantee cancellation inside the WPD host or
camera, and physical power/USB recovery may still be necessary.

## Offline verification

Tests use fake COM for capabilities, order, release failures, slot reads and
numeric PTP errors. A real synthetic child sleeps instead of touching a device;
it is terminated at the deadline. A separate fake child refuses termination to
verify that the parent still stops waiting. Existing registration tests use the
same lock context and preserve write gating, ordering and primary errors.

At preparation time, the process wrapper and empty-cycle test had not been run
on the RP; the subsequent authorized execution is recorded below.

## Execution ledger

The user subsequently authorized this diagnostic only and confirmed the RP was
connected and ready. One run produced private metadata report
`RP_UI_LOCK_DIAGNOSTIC_20261016_01.json` and exited0. The empty UI-lock cycle,
both mode disables and connection close completed; the twoD172 observations
matched the pre-Err70 baseline hash. No style/state transfer or retry occurred.
The user separately confirmed: "Sim, continua normal", without Err70 or a
lockup. This execution grants no authorization for another session or a style
write.
