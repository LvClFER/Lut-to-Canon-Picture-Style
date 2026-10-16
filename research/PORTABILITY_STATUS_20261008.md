# Portability research — 2026-10-08

Mobile first scope: register prepared styles, not a full RAW editor. Keep the
working Windows path unchanged. No camera operations performed in this audit.

## Platform evidence

- Android provides USB host access and bulk transfers. This supplies a possible
  transport, not Canon registration or compiler semantics:
  https://developer.android.com/develop/connectivity/usb
  https://developer.android.com/reference/android/hardware/usb/UsbDeviceConnection
- Apple ImageCaptureCore documents camera PTP commands and iOS tethering access
  requirements; macOS sandbox USB access requires the documented entitlement.
  Availability, supported hardware and command behavior still need native tests:
  https://developer.apple.com/documentation/imagecapturecore
  https://developer.apple.com/documentation/imagecapturecore/iccameradevice/requestsendptpcommand(_:outdata:sendcommanddelegate:didsendcommand:contextinfo:)
- Canon documents EDSDK on Mac and CCAPI across mobile platforms. Neither this
  overview nor our current evidence proves arbitrary PF3 registration via CCAPI:
  https://www.usa.canon.com/support/sdk

## Concrete implementation

ptp_wire.py is a pure, bounded USB PTP container codec with incremental decoding.
Four tests cover every split boundary, coalesced containers, parameter geometry,
malformed lengths and truncated input. 394 discovered tests and py_compile pass.
It opens no devices. Apple command framing must be adapted separately; USB
containers must not simply be passed to Apple's API unchanged.

## Main missing pieces

1. Portable compiler output equivalence across all observed families; current
   mathematical references do not collectively replace EdsCFParse/MLib.
2. Independent registration state machine, dynamic camera state and acceptance
   confirmation. A USB codec alone cannot install a style safely.
3. Native adapters and device tests on Android, iOS and macOS. This Windows host
   cannot establish their runtime behavior or App Store eligibility.
4. Capability discovery: separate transport, RAW support, payload family and
   physical validation. Unknown cameras must not inherit RP validation.

Next safe work: inventory captured command/state evidence and define a replayable
offline transaction model before any write-enabled adapter. Do not introduce
per-model carrier templates as a substitute for the general compiler path.
