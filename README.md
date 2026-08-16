# Canon Style Studio Public Alpha

Version **1.0.0-alpha.1** · Build **2026-08-16-PUBLIC-ALPHA-1**

Canon Style Studio is an experimental Windows editor for developing Canon RAW files through the Canon DPP4Lib runtime installed with Picture Style Editor, building sequential LUT stacks, previewing Canon's 33³/12-bit LUT result and exporting PF3 Picture Style files.

## Requirements

- Windows 10 or 11, 64-bit.
- Canon **Picture Style Editor** installed. The app discovers standard 64-bit and 32-bit Canon install locations; use **Locate PSE…** if it is installed elsewhere.
- Canon Digital Photo Professional is **not required**.

The Windows x64 standalone build includes its own Python runtime and application dependencies. Testers do **not** need to install Python or packages.

The distribution contains no Canon DLL, executable, ICC/ICM profile, PF3 base, RAW image or internal Canon resource. At runtime it uses DPP4Lib and an input profile from the user's own local Picture Style Editor installation. Generated working PF3 data and caches are stored under `%LOCALAPPDATA%\CanonStyleStudio`.

## Start

1. Extract the entire ZIP to a normal writable folder.
2. Run `CanonStyleStudio.exe` (or `START_CANON_STYLE_STUDIO.bat`).
3. In the app, press **Test** beside RAW engine. If PSE was not found, press **Locate PSE…** and select the folder containing `PSEditor.exe` and `DPP4Lib`.

Without PSE, JPEG/PNG/TIFF and LUT work remains available. Canon RAW rendering and PF3 export clearly report that Picture Style Editor is required; LibRaw remains only a fallback.

## Main workflow

- Open CR3/CR2, JPEG, PNG or TIFF references.
- Adjust Canon-native Exposure, fixed/Kelvin White Balance, WB Shift, Picture Style, Contrast, Saturation and Color Tone for RAW files.
- Add `.cube` or Hald LUTs, reorder layers and set opacity. LUT-only changes reuse the cached Canon development.
- Switch to **Canon 33³ Preview** to simulate only the final sequential LUT stack quantized to Canon's 33³/12-bit table.
- Export a validated PF3. No Picture Style is applied a second time by Canon 33³ Preview.

Fit, zoom and pan share stable view state. Zooming a RAW requests validated higher-detail Canon output where safe; portrait RAW is developed using the validated landscape-stage pipeline and returned in portrait orientation.

## Privacy-safe reports

Use **Create Test Report** in the top bar when reporting a problem. It includes app/runtime versions, camera model, dimensions, settings, LUT metadata and sanitized logs. Usernames and personal paths are replaced. The original RAW is **off by default** and is included only after two explicit confirmations.

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for the tester matrix and bug-report format, and [PUBLIC_ALPHA_RELEASE_NOTES.md](PUBLIC_ALPHA_RELEASE_NOTES.md) for validated and experimental boundaries.

## Legal notice

Canon Style Studio is independent experimental software and is not affiliated with or endorsed by Canon. Canon, DPP, Picture Style Editor and related names are trademarks of their respective owners. Users must install and license Canon software separately.
