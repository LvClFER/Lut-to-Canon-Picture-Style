# Canon Style Studio 1.0.0-alpha.25

Build: `2026-09-14-REPEATED-CREATE-REF-FIX-ALPHA-25`

- Public and development/test builds now use the same zero-setup camera workflow.
- Removed the runtime dependency on Manual Loader/support binaries and model-specific carriers.
- Canon EdsCFParse generates the selected base locally; EOS Utility compiles for the connected camera.
- Live validation covers both 33³ table conversions and an exact compiler-to-EDSDK buffer comparison.
- No Canon-derived support files are bundled or requested.
- EOS Utility may reopen the same PF3 immediately before registration; that metadata-only reopen no longer discards a completed validation. New compiler inputs or a new compile still invalidate it immediately.

# Canon Style Studio 1.0.0-alpha.17

Build: `2026-09-05-FUJI-WB-CALIBRATION-PF3-ALPHA-17`

- Replaced the symmetric Fuji-style Recipe WB estimate with asymmetric curves measured from the controlled X-T1/Provia/5000 K `0`, `±5` and `±9` reference sequence. Error against the eight published reference JPEGs is reduced by 32–85%.
- Corrected normal PF3 export in standalone builds to default to `exported_styles/` beside the application instead of PyInstaller's internal runtime folder.
- PF3 export now adds the `.pf3` extension when omitted. Automated UI export validation covers the 434,511-byte PF3, sidecar and manifest.
- Includes the current dynamic Canon carrier-family registry. Camera installation remains fail-closed and experimental outside physically tested paths.

# Canon Style Studio 1.0.0-alpha.7

Build: `2026-08-23-PORTABLE-STORAGE-ALPHA-7`

## Alpha.7 portable storage

- Removed camera preparation output from `%LOCALAPPDATA%`: every attempt now remains under `exported_styles/<timestamp>_<style>/` beside the application.
- The PF3, manifest, compiled Block1, complete EOS RP payload and install report are retained. Existing attempts are never automatically deleted or overwritten.
- Send to Camera now performs target-specific live validation using the installed Canon compiler; Manual Loader support files are no longer required or imported.
- Settings, caches, logs, reports and extracted portable-project LUTs now use `app_data/` beside the application. Old AppData settings are copied once for migration and left untouched.
- Portable support discovery takes priority and survives moving the complete application folder to another user/computer.
- Historical camera-install attempts from this development machine were copied into `exported_styles/legacy_*`; their AppData originals were retained.

## Alpha.6 camera-install correction

- Corrected the EOS RP compiler gate to follow the documented, physically validated V37 recipe: exact target legacy Block1 is inserted into the known EOS RP carrier while the carrier's Block2 remains unchanged.
- The exact compiler self-test remains fail-closed and still requires both known-good Superia legacy blocks to match the validated 8192-byte oracle byte-for-byte.
- Target PF3 Block1 and Block2 are no longer incorrectly required to be identical. Real Standard-based PF3 files legitimately compile to different blocks; that previous over-strict check prevented **Prepare and Arm EOS RP** from proceeding.
- Install reports now record both target block hashes, whether they happened to match, the Block1 extraction policy and explicit carrier Block2 preservation.
- Added regression coverage for a target with different Block1/Block2 values; the hook is armed only with exact Block1 after the unchanged self-test passes.

## Alpha.5 changes

- **Save Project is now portable:** `.canonstyleproject` is a ZIP containing the complete editor/view state and every CUBE/Hald LUT referenced by the current edit or snapshots A/B/C.
- LUT assets are deduplicated by SHA-256. Loading verifies identity and size, rejects path traversal/duplicate paths, and extracts to the application data cache using content-addressed folders.
- Reference photographs are not embedded. Their filenames are retained as hints and the app clears any previously displayed photograph when a portable project is opened.
- Legacy plain-JSON `.canonstyleproject` files remain supported.
- Canon-derived DLL/ICC/PF3 resources and machine-specific absolute paths are not embedded. Imported PF3 files must be selected again on the destination computer.
- Reworked Color Chrome-style and Blue Chrome-style masks after real Canon RAW validation showed the previous high-chroma/peak threshold could produce no visible pixel change. Weak/Strong ordering and visible effect are now regression-tested against EOS RP DPP4Lib renders.

## Creative Color introduced in alpha.4

## Fixed

- Added an interactive five-point monotonic Tone Curve with reset and project/history persistence.
- Added Six Color-Axes for Red, Yellow, Green, Cyan, Blue and Magenta, each with Hue, Saturation and Luminance adjustments.
- Integrated the validated Manual Loader Color Chrome-style and Blue Chrome-style perceptual algorithms as clearly labelled experimental creative transforms.
- Tone Curve, Six Color-Axes and Chrome-style controls now reuse the cached Canon development and are composed after the user LUT stack.
- Working Preview uses a responsive cached 33³ creative stage; Canon 33³ Preview recomposes the complete LUT stack plus creative controls into one final 33³/12-bit transform.
- PF3 export, project files, Undo/Redo, snapshots, manifests, test reports and Send-to-Camera export state now preserve the complete Creative Color configuration.
- Added bounded creative/Pillow/33³ caches so long slider drags cannot grow memory indefinitely.

- Removed the 390 px sidebar ceiling. The sidebar now starts at 430 px, can be resized up to 720 px and never shows a horizontal scrollbar.
- Integrated the physically validated EOS RP loader-assisted workflow under **Send to Camera**, while keeping it isolated from preview/PF3 code.
- Added exact size/SHA-256 validation for every external compiler/carrier fixture. Public releases still contain none of those captured binaries.
- Added fail-closed compiler self-test with duplicate known-good oracle validation, safe carrier/name construction, runtime install reports and automatic disarm on close.
- Added explicit EOS RP confirmation, User Def. 1–3 selection, EOS Utility launch/discovery and guided normal-registration instructions without GUI auto-clicking.
- Corrected the swapped Canon DPP4Lib properties: Saturation now uses `0x20305` and Color Tone uses `0x20304`, validated through chroma/hue pixel metrics.
- Fixed the PF3 export window close failure caused by an accidental override of Qt's `QDialog.done(int)` method; added an explicit Close button.
- Corrected Hald CLUT parsing to standard flattened R-fastest ordering and regenerated both identity/template assets.
- Added real local Base Picture Style template resolution with exact hash and Style-ID validation.
- Added `basePictureStyle`, template provenance and validation state to projects, PF3 sidecars, manifests and test reports.
- Added LUT color/calibration metadata and a non-forcing Canon Standard warning for the calibrated Velvia/Gold LUT filenames.
- PF3 export now snapshots all Qt state on the UI thread before background generation.

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
- Creative identity, monotonic curve, six-axis selectivity, Chrome hue selectivity and combined LUT + Creative Color PF3-table equivalence.
- PF3 export of Basic and Sharpness fields.
- Undo/Redo, snapshots/project data round-trip, JPEG/TIFF decode and report privacy defaults.
- Recursive public-package scan excludes Canon DLL/EXE/ICC/ICM/PF3/RAW/log/dump files, caches and personal paths.
- EOS RP payload construction preserves the carrier outside the two name fields and compiled Block1 range.
- The camera hook statically enforces observation-only handling for `0x00000115`; simulated arm tests prove a compiler mismatch cannot call `arm`.

## Experimental

- Tone Curve, Six Color-Axes, Color Chrome-style and Blue Chrome-style are LUT-baked creative transforms. They are not claimed as native Canon/Fujifilm controls or pixel-identical reproductions of either manufacturer's processing.
- Eyedropper WB uses a robust neutral patch calculation after Canon development; it is not stored in PF3.
- Imported PF3 preview uses Canon Neutral plus the imported table/known fields. Direct standalone native PF3 injection remains unresolved.
- Sharpness Strength/Fineness/Threshold are written natively to PF3, but on-screen sharpness is an approximation.
- Canon bodies not present in the regression set are accepted without a hard-coded model block and labelled experimental.
- Exact WB matching to each physical camera/PSE version requires tester comparisons.
- Generated PF3 bases remain experimental when a hash-validated local base template is unavailable.
- Camera installation for bodies other than EOS RP is blocked/unvalidated; RAW compatibility never implies camera-install compatibility.

## Known issues

- Canon DPP4Lib can return corrupted pixels for full-native portrait output. The app intentionally uses the validated portrait-safe Canon render size; logical native geometry is retained for the viewer.
- A fast embedded/LibRaw image may be shown only while Canon output is unavailable. Exact Canon rendering is authoritative.
- Picture Style Editor is required for Canon RAW rendering and PF3 export. Digital Photo Professional is not required.
- Windows SmartScreen may warn about the unsigned Alpha executable. Code signing is not yet configured.
- The two calibrated Velvia/Gold CUBE files were not present in the supplied workspace, so their exact image-pixel comparison is not part of this build's automated evidence. Their filenames and Canon Standard calibration metadata are supported and tested with a generated stand-in.
- A complete physical Send-to-Camera test still requires a connected EOS RP and a normal user-driven EOS Utility registration. Automated tests never write to a camera.

## Camera-install safety boundary

PF3 properties and EDSDK registration transaction properties are separate layers. In camera registration, `0x00000115` is an opaque binary state/control blob and is never renamed, resized or patched. The current workflow corrects table acceptance only while Canon compiles the exact selected PF3; it never replaces the outgoing `0x01000203` buffer. Live semantic and byte-for-byte transport validation require no external fixtures. EOS RP and EOS R8 have been physically exercised; other bodies remain experimental.

## Distribution integrity

The public standalone ZIP contains Canon Style Studio, Frida and its other open-source runtime dependencies, documentation, the application-owned hook source and example identity Hald assets. Canon software, PF3 bases, compiler references, descriptors, native carriers and captured payloads are never bundled.
