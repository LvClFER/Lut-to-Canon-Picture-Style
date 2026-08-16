# Canon Style Studio 1.0.0-alpha.1

Build: `2026-08-16-PUBLIC-ALPHA-1`

## Fixed

- Replaced the weak standalone fixed-WB enum path with Canon-native Kelvin mapping. Tungsten on daylight material now produces the expected strong blue result.
- Added native DPP4Lib WB Shift on both B↔A and G↔M axes.
- Added all six supported Canon Picture Styles: Standard, Portrait, Landscape, Neutral, Faithful and Fine Detail.
- Separated Canon RAW development from LUT processing. LUT opacity/order changes reuse the developed RAW cache.
- Added debounce, cancellation and generation checks so obsolete slider renders cannot overwrite newer results.
- Stabilized Fit, zoom, pan, split and viewer geometry across intermediate/final renders.
- RAW zoom requests validated higher-detail Canon output instead of enlarging only the working preview.
- Corrected portrait processing: landscape-stage development followed by portrait output.
- Canon 33³ Preview now simulates only the final sequential LUT stack quantized to 33³/12-bit; it does not reapply the Picture Style.
- Added PSE discovery, manual location, local runtime ICC extraction and generated runtime PF3 bases. No Canon resource is bundled.
- Added sanitized Test Report creation, Alpha/About information and a guarded launcher with persistent logs.
- Added a Windows x64 standalone build containing the Python runtime and application dependencies; public testers do not need Python installed.

## Verified automatically

- Python compilation, dependency/startup checks and PF3 structural validation.
- Landscape and portrait CR3 geometry, deterministic DPP output, cancellation recovery and developed-stage cache hits.
- Exposure, Contrast, Saturation, Color Tone and fixed/Kelvin WB pixel changes.
- Strong Tungsten/daylight blue shift and both WB Shift directions.
- Six distinct Picture Style render outputs.
- Sequential LUT opacity/order, Hald parsing and Canon 33³/12-bit output versus exported PF3 table.
- PF3 export of Basic and Sharpness fields.
- Undo/Redo, snapshots/project data round-trip, JPEG/TIFF decode and report privacy defaults.
- Recursive public-package scan excludes Canon DLL/EXE/ICC/ICM/PF3/RAW/log/dump files, caches and personal paths.

## Experimental

- Eyedropper WB uses a robust neutral patch calculation after Canon development; it is not stored in PF3.
- Imported PF3 preview uses Canon Neutral plus the imported table/known fields. Direct standalone native PF3 injection remains unresolved.
- Sharpness Strength/Fineness/Threshold are written natively to PF3, but on-screen sharpness is an approximation.
- Canon bodies not present in the regression set are accepted without a hard-coded model block and labelled experimental.
- Exact WB matching to each physical camera/PSE version requires tester comparisons.

## Known issues

- Canon DPP4Lib can return corrupted pixels for full-native portrait output. The app intentionally uses the validated portrait-safe Canon render size; logical native geometry is retained for the viewer.
- A fast embedded/LibRaw image may be shown only while Canon output is unavailable. Exact Canon rendering is authoritative.
- Picture Style Editor is required for Canon RAW rendering and PF3 export. Digital Photo Professional is not required.
- Windows SmartScreen may warn about the unsigned Alpha executable. Code signing is not yet configured.

## Distribution integrity

The public standalone ZIP contains Canon Style Studio, its embedded open-source runtime dependencies, documentation and application-owned example identity Hald assets. Canon software and resources are discovered and used from the tester's own installation at runtime.
