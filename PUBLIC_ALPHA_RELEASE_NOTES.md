# Historical alpha and release-candidate notes

For the current release, see [version 1.0.0](RELEASE_NOTES.md). The dated sections below describe their own historical scope.

# Local development candidate · 2026-10-18 · not published

- Includes six user-authorized application-generated basic PF3 files. First use no longer requires a user reference, pre-existing cache or Canon software for PF3 generation.
- Included resources are hash-checked and remain read-only; styles are still saved as one editable document in Documents.
- Adds a light editorial Windows layout with a large left photo preview, right adjustment cards and reference thumbnails. Known Basic-control updates remain disabled in the editor; the matching-control camera path is retained.
- Canon RAW development remains optional and requires DPP4Lib. The historical releases below describe their own validation scope.

# Canon Style Studio 1.0.0-rc.7 · candidate · 2026-10-18

- Corrects Fine Detail selection to follow the reconstructed identifier policy: the 5DS/5DS R class-6 path is accepted, while the coefficient-policy 7D-II path remains rejected. Three private offline native cases confirmed this distinction.
- Removes the blanket reference-bank rejection for compact families 5/6 in the strict PF3 3000 path. Original reference records remain in the style/project; compilation uses active records.
- Static constructor/vtable evidence and twelve private offline native-oracle cases establish no-op callbacks and reference-only edit invariance. The independent compiler reproduces nine complete native carriers for compact coefficient selectors and the headers/second pair for all twelve. The 5DS first pair retains the application's previously established dense-table policy.
- A synthetic regression checks all catalogued family-5/6 identifiers, preserving the high bank and rejecting other envelopes. Borrowed descriptors and compiler-selector tests do not establish physical support for those bodies. No new camera access was performed.

# Canon Style Studio 1.0.0-rc.6 · candidate · 2026-10-18

- Restores an explicit optional EOS Utility fallback in the Send to Camera menu. The main action remains independent USB and never resolves native prerequisites when opened.
- Corrects test reports to distinguish independent RP validation from the native fallback's separate RP/R8 evidence. Updates the main toolbar version/About labels.
- Ten focused entrypoint/UI tests passed. All 54 generated-base/family combinations inside the reconstructed domain compiled and passed complete carrier inspection; six older-family Fine Detail combinations were correctly rejected. These are offline checks, not physical tests of additional bodies.
- The independent compiler and transport implementation are unchanged from RC5, which was physically tested on RP User Def. 2. No new camera session is authorized or performed for these UI changes. Candidate packaging/equivalence validation is separate from direct physical validation of a new executable.

# Canon Style Studio 1.0.0-rc.5 · 2026-10-18

- Replaces RP-only installation dispatch with integrated compilation/session planning for the ten reconstructed Canon serializer families and 77 known compiler identifiers. Unique modern formats can also be negotiated for unknown identifiers after complete live grammar, descriptor and operation checks.
- Connects legacy dense9 metadata, compact integer/cache/pixel combinations, modern17 and full33 dense tables to the existing backup, lock, write, unlock and requested-slot confirmation flow. Source/PF3 processing does not load Canon code.
- Preserves legacy 24-byte and extended 32-byte slot controls without fabricating missing bytes. Selects the style operation from capabilities advertised by both WPD and DeviceInfo. Does not retry a different command after failure.
- This RC5 executable registered Aerochrome in EOS RP User Def. 2 with matching requested readback and completed cleanup; the user confirmed Aerochrome visible and no camera error. Earlier evidence covers User Def. 3 and the user's RC4 User Def. 1 report. Independent physical evidence remains RP only. Other bodies are experimental; the catalog describes reconstructed compiler families, not 77 physically tested cameras. See CAMERA_COMPATIBILITY.md for constraints.

# Canon Style Studio 1.0.0-rc.4 · 2026-10-17

- Removes duplicate base, sharpness and colour controls from the independent send dialog. Installation uses the existing editor settings and saves those same settings in the style project.
- Adds a visible success message naming the style, camera and User Def. slot. Success requires matching readback from the requested slot, completed temporary-mode/connection cleanup and no worker failure or recovery requirement.
- Six UI tests cover editor snapshots, confirmation/cancellation and false-success cases. This revision was tested locally without accessing the camera; physical and clean-Windows validation scope is unchanged.

# Canon Style Studio 1.0.0-rc.3 · 2026-10-17

- Send to Camera opens the independent USB workflow directly, without resolving a Canon DLL or launching EOS Utility.
- Adds camera selection, User Def. 1–3, Picture Style name/base, Sharpness Strength/Fineness/Threshold, Contrast, Saturation and Color tone in the same window. Exported projects retain the selected settings; the editor stays unchanged.
- Shows preparation, installation, readback and session status. Technical logs expand on failure. New bases use only the independent generator and the owned PF3 reference.
- Physical validation remains limited to the previously tested RP profile and User Def. 3. Slot Basic controls must already match. No camera access was performed for this UI revision; clean-Windows deployment remains unverified. Canon RAW rendering remains a separate optional Canon-dependent feature.

# Canon Style Studio 1.0.0-rc.2 · 2026-10-17

- A reopened project or owned PF3 can initialize new generated bases with an empty cache, without loading Canon code. The selected base is built from application-owned fields; the imported LUT is not copied into it.
- Independent base resolution now validates the complete generated base and regenerates stale cache entries, including old zero-matrix bases.
- Clean-Windows deployment remains untested; the user has no second Windows machine and Windows Sandbox is unavailable on this host. The independent RP path remains experimental.

# Canon Style Studio 1.0.0-rc.1 · 2026-10-17

- Adds independent compilation and isolated Windows WPD registration through **Send to Camera → Independent · experimental**. The exact RP profile was physically exercised with NC and Aerochrome, including requested readback and user-reported appearance.
- Saves one editable `.canonstyleproject` directly in `Documents/Canon Style Studio PF3`. Temporary PF3s, camera reports and baseline backups stay in `app_data/logs/camera_install`.
- Prepares the style before requesting permission for the camera write. Unknown profiles and conflicting Basic controls are blocked; writes are not retried automatically.
- Canon RAW preview still requires DPP4Lib. Fresh generation without an owned encrypted input, clean-machine deployment, other physical camera profiles and macOS/Android adapters remain unverified.
- This local release candidate does not replace the published alpha.29 release. Clean-machine deployment must be verified before declaring 1.0.0 stable.

# Canon Style Studio 1.0.0-alpha.29

Build: `2026-10-16-PF3-BASE-CONTROLS-FIX-ALPHA-29`

- Generated PF3 bases now use identity matrices and neutral post-LUT curves instead of zero coefficients that could produce black camera output.
- Corrected PF3 Contrast and Sharpness Strength offsets without changing camera-registration state.
- Added offline compiler/protocol reference code and regression tests to the source repository. The independent camera path remains experimental and is not enabled in the public editor.
- Windows x64 standalone includes Python and dependencies; Picture Style Editor and EOS Utility requirements are unchanged. No proprietary Canon resources are bundled.

# Canon Style Studio 1.0.0-alpha.26

Build: `2026-09-14-LEGACY-16744-COMPATIBILITY-ALPHA-26`

- Public and development/test builds now use the same zero-setup camera workflow.
- Removed the runtime dependency on Manual Loader/support binaries and model-specific carriers.
- Canon EdsCFParse generates the selected base locally; EOS Utility compiles for the connected camera.
- Live validation covers both 33³ table conversions and an exact compiler-to-EDSDK buffer comparison.
- No Canon-derived support files are bundled or requested.
- EOS Utility may reopen the same PF3 immediately before registration; that metadata-only reopen no longer discards a completed validation. New compiler inputs or a new compile still invalidate it immediately.
- Restored the Canon-native 16744-byte legacy family after a 12-vector matrix matched every known EOS 1300D compiler reference exactly. Other unproven no-builder routes remain blocked.

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
