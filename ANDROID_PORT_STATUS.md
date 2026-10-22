# Android candidate — local development

Android is now the next platform ahead of further macOS work. The requested
scope is the complete app: editor, editable portable projects and Canon USB
installation. This document separates implemented source from device validation.

The Android activity embeds the existing Python engine through Chaquopy, with
a native touch interface instead of desktop Qt widgets. It reuses the six
included basic PF3 files and independent compiler; no Canon or Nikon DLL is
packaged. `prepare_android.py` stages the shared sources and records their hashes.
Build tools and generated Python sources stay outside the tracked source set.

Implemented editor operations include image/reference selection, portrait-safe
fit, a draggable before/after divider, base Picture Style, Basic controls,
exposure/WB preview, creative color, LUT opacity and enable/remove, undo/redo,
snapshots A/B/C, PF3 export and the existing `.canonstyleproject` format. Creative
settings use native sliders and dropdowns, including the five curve points,
six color axes and chrome effects. Opening a project preserves images already
loaded in the editor.
The Android document picker handles import and export without broad filesystem
permissions. Inputs are copied into app-private storage; the activity does not
request network permission. Private imports currently remain until app data is
cleared. A separate atomic private-session checkpoint restores edits, reference
selection and snapshots after process termination; portable exports remain
explicit user actions.

The candidate uses Pillow/NumPy and a native LibRaw 0.22.2 decoder built for both
Android architectures. Canon RAW files are unpacked from their sensor plane;
there is no embedded-JPEG fallback. Unsupported or failed RAW development is an
error, leaving the current project untouched. White balance uses camera/auto
coefficients; exposure and the selected PF3 LUT are applied to the developed
pixels. One sensor decode is cached until the source or white balance changes.

This solves the previously styled JPEG contamination, but not Canon base-look
matching. The six bundled PF3 bases contain identity LUTs and camera-side base
selectors, not standalone implementations of Standard/Portrait/etc. A LibRaw
render plus these tables must not be described as Canon-native RAW rendering.
The RAW status explicitly identifies this missing calibration. Direct application
of installed Canon ICCs was evaluated against DPP references and rejected as a
substitute: the tested fixed input-space/gamma/brightness combinations did not
match. Those Canon ICCs are not included in the Android app. DPReview gallery
integration and independent NP3 colour conversion are also not implemented.

`camera_install/android_ptp.py` implements bounded bulk PTP framing, receive and
send adapters compatible with the existing compiler/session controllers.
`AndroidBulk.java` owns an explicitly permitted Canon still-image interface,
with bounded reads/writes and no forced driver detachment. The UI offers explicit
camera and User Def. slot selection, then a confirmation and Android USB
permission. `CameraWorker` runs in its own `:camera` process with a hard 45-second
deadline and never restarts a transfer. The shared registration controller backs
up the original slot, verifies the final style/Basic controls and closes temporary
modes. Success is displayed only after session and connection cleanup return.
A physical Android round trip is still required. No camera session or physical
write was performed while developing this port.
An Android build must not inherit Windows/RP validation claims.

## Local build

Use JDK 17, Gradle 8.13, Android SDK platform 35, NDK 28.2.13676358,
CMake 3.22.1 and Python 3.12:

```powershell
python prepare_android.py
$env:CANON_ANDROID_BUILD_PYTHON = (Get-Command python).Source
gradle -p android assembleDebug --no-daemon --console=plain
```

Set `ANDROID_HOME` to the local SDK. ARM64 devices and x86-64 emulators are
configured; minimum Android API is 26. A debug APK is a test candidate, not a
release. Native compilation, emulator startup and physical-device checks must
be recorded independently from desktop Python tests.

## Validation on 20 October 2026

The initial debug APK compiled for ARM64 and x86-64 and passed APK signature verification.
Its 151 staged shared source/resource hashes matched the source tree. No
Canon/Nikon DLL or Internet permission is included. Android lint reported zero
errors; remaining warnings concern hardcoded English UI strings.

The dedicated mobile/PTP tests passed 22 checks on the development host. A native
Android 15 x86-64 emulator then executed the packaged Pillow/NumPy engine,
preserved portrait dimensions, exported a 434,511-byte PF3, reopened a portable
project while preserving its photo, recovered a private session and launched and
rendered the activity. A test screenshot records the portrait fit and comparison
divider.

The subsequent sensor-RAW candidate compiles LibRaw from a SHA-256-pinned
official source archive. An Android 15 x86-64 instrumented test developed an EOS R
CR3 and a same-size copy whose largest embedded JPEG was replaced by solid red.
Bytes outside that JPEG were identical. Both produced exactly the same developed
3371 × 2249 RGB pixels, SHA-256
`c3b0375ba4736dd86c4a8bf7a59ce935342848afcaea7fc91a72ebe45204429b`.
The test also confirmed that invalid RAW input fails without creating a preview.
This is sensor-decoding evidence, not proof of a Canon base look. ARM64 execution,
physical USB, Canon base-render matching and DPReview remain outstanding. No
release was published.

On 21 October, RAW exposure was moved into LibRaw development, before gamma
encoding and RGB8 output. The cache now includes exposure, and the editor skips
the later RGB exposure adjustment when the native decoder confirms it already
applied it. Ordinary image exposure still uses the shared editor path. This does
not establish Canon Picture Style matching; the uncalibrated-base indication
remains in place.

The updated APK and instrumentation APK built successfully for both configured
ABIs. The Android 15 x86-64 emulator confirmed native -2 EV development produces
a darker, nonempty image and reports sensor exposure applied. At zero exposure,
the original and modified-preview CR3 still produce the exact sensor hash above.
The native Python, portrait, PF3, project, session and activity checks also passed.
ARM64 is compiled but this change has not been executed on a physical device.

The sensor decoder now applies a valid vendor default inset crop before
development. Absolute vendor coordinates are converted to LibRaw's coordinates
relative to sensor margins, with bounds checks; absent/invalid inset metadata
leaves LibRaw's ordinary active area in use. The EOS R fixture now develops to
3360 × 2240 rather than including the extra margins at 3371 × 2249. The updated
RGB SHA-256 is `f602d256af0e499a81c8eee6cc71c97cbc334ae71710190e153b4363adebfc26`.

The Android 15 emulator passed the updated crop test, unchanged embedded-JPEG
independence and sensor-exposure tests. Two private CR3 copies change only the
two-byte CMT1 orientation field from 1 to 6/8; both developed portraits matched
the exact clockwise/counterclockwise rotation of the cropped horizontal pixels.
They exercise RAW orientation metadata, not separate real portrait captures.
The PF3/project/session/activity checks also passed. Source RAWs were not changed.

LibRaw source: [official 0.22.2 archive](https://www.libraw.org/data/LibRaw-0.22.2.zip),
SHA-256 `f4448371523f9960d26a131ed9dc21bee49f967adbcc4fb6f56b9b47c2ba87c6`.
The bundled CDDL licence and copyright notice accompany the native decoder.

References: [Chaquopy Gradle integration](https://chaquo.com/chaquopy/doc/current/android.html),
[Android USB host](https://developer.android.com/develop/connectivity/usb/host),
[bounded bulk transfers](https://developer.android.com/reference/android/hardware/usb/UsbDeviceConnection).
