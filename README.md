# Canon Style Studio Public Alpha

Version **1.0.0-alpha.17** · Build **2026-09-05-FUJI-WB-CALIBRATION-PF3-ALPHA-17**

Canon Style Studio is an experimental Windows editor for developing Canon RAW files through the Canon DPP4Lib runtime installed with Picture Style Editor, building sequential LUT stacks, previewing Canon's 33³/12-bit LUT result and exporting PF3 Picture Style files.

## Requirements

- Windows 10 or 11, 64-bit.
- Canon **Picture Style Editor** installed. The app discovers standard 64-bit and 32-bit Canon install locations; use **Locate PSE…** if it is installed elsewhere.
- Canon Digital Photo Professional is **not required**.
- **Send to Camera** additionally requires EOS Utility 3 and the externally supplied, hash-validated Manual Loader v2.4 EOS RP support folder.

The Windows x64 standalone build includes its own Python runtime and application dependencies. Testers do **not** need to install Python or packages.

## Portable storage

Application-owned files stay beside `CanonStyleStudio.exe`: `app_data/` contains settings, caches and logs; `camera_support/` contains the user's private imported support copy; and `exported_styles/` is the default folder for normal PF3 exports and permanently retains each camera preparation attempt. Moving the complete application folder therefore carries this state to another writable location/computer. The former `%LOCALAPPDATA%\CanonStyleStudio` settings are read once for non-destructive migration and are never deleted.

The distribution contains no Canon DLL, executable, ICC/ICM profile, PF3 base, RAW image, native carrier, descriptor or captured payload. At runtime it uses DPP4Lib and an input profile from the user's own local Picture Style Editor installation. Generated working PF3 data and caches are stored beside the application.

## Start

1. Extract the entire ZIP to a normal writable folder.
2. Run `CanonStyleStudio.exe` (or `START_CANON_STYLE_STUDIO.bat`).
3. In the app, press **Test** beside RAW engine. If PSE was not found, press **Locate PSE…** and select the folder containing `PSEditor.exe` and `DPP4Lib`.

Without PSE, JPEG/PNG/TIFF and LUT work remains available. Canon RAW rendering and PF3 export clearly report that Picture Style Editor is required; LibRaw remains only a fallback.

## Main workflow

- Open CR3/CR2, JPEG, PNG or TIFF references.
- Adjust Canon-native Exposure, fixed/Kelvin White Balance, WB Shift, Picture Style, Contrast, Saturation and Color Tone for RAW files. Fuji-style Recipe WB is a separate LUT-baked approximation calibrated from a controlled X-T1/Provia/5000 K reference sequence.
- Add `.cube` or Hald LUTs, reorder layers and set opacity. LUT-only changes reuse the cached Canon development.
- Use recipe-style Highlight and Shadow controls from -2 to +4 and Color from -4 to +4; shape a five-point monotonic Tone Curve; tune Red, Yellow, Green, Cyan, Blue and Magenta Hue/Saturation/Luminance axes; and add experimental Color Chrome-style or Blue Chrome-style density. These controls are baked after the LUT stack and reuse the cached Canon development.
- Save a portable `.canonstyleproject` archive containing every editor setting and all CUBE/Hald LUTs used by the current edit or snapshots. Reference photographs are deliberately not embedded; only their filenames are retained as reconnect hints.
- Switch to **Canon 33³ Preview** to simulate only the final sequential LUT stack quantized to Canon's 33³/12-bit table.
- Export PF3 through Canon's locally installed EdsCFParse serializer. The default destination is the portable `exported_styles/` folder, and `.pf3` is added automatically. No Picture Style is applied a second time by Canon 33³ Preview.
- Use **Send to Camera** for the integrated, loader-assisted EOS RP workflow. The app exports the current editor state, runs the exact compiler self-test, builds Block1/carrier, arms the hook and then waits while you perform a normal EOS Utility registration.

The editor records `basePictureStyle` in projects and PF3 manifests. Public releases do not contain extracted Canon base PF3 files. When a hash-validated local base set is available, select it with **Bases…**; otherwise generated PSE/EdsCFParse templates are clearly labelled experimental before export.

Highlight, Shadow, Color, Tone Curve, Six Color-Axes and both Chrome-style controls are LUT-baked creative transforms, not claimed Canon-native PF3 controls. Working Preview applies them as a responsive 33³ creative stage after the full LUT stack. Canon 33³ Preview recomposes the complete LUT stack plus creative stage into the final 33³/12-bit transform, matching PF3 table export.

Portable projects validate embedded LUT sizes and SHA-256 hashes before extraction, reject unsafe archive paths, and remain backward-compatible with the earlier plain-JSON project format. Local Canon PF3/DLL/ICC resources and RAW/JPEG/TIFF references are never embedded. An Imported PF3 must be selected again on the destination computer.

**Send to Camera remains experimental outside the physically validated EOS RP path.** Dynamic carrier-family detection recognizes the currently mapped legacy and modern layouts; the 83076-byte path has been physically exercised on an EOS R8 with Aerochrome. Opening a RAW from a body does not validate its registration payload, and a valid PF3 is not equivalent to a validated EDSDK transaction. The hook remains fail-closed when its compiler self-test, carrier family or structural checks do not match.

Fit, zoom and pan share stable view state. Zooming a RAW requests validated higher-detail Canon output where safe; portrait RAW is developed using the validated landscape-stage pipeline and returned in portrait orientation.

## Privacy-safe reports

Use **Create Test Report** in the top bar when reporting a problem. It includes app/runtime versions, camera model, dimensions, settings, LUT metadata and sanitized logs. Usernames and personal paths are replaced. The original RAW is **off by default** and is included only after two explicit confirmations.

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for the tester matrix and bug-report format, and [PUBLIC_ALPHA_RELEASE_NOTES.md](PUBLIC_ALPHA_RELEASE_NOTES.md) for validated and experimental boundaries.

## Legal notice

Canon Style Studio is independent experimental software and is not affiliated with or endorsed by Canon. Canon, DPP, Picture Style Editor and related names are trademarks of their respective owners. Users must install and license Canon software separately.
