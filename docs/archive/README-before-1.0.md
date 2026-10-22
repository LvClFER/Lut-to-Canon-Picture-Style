# Archived development README

Historical notes; see the current [README](../../README.md) for version 1.0.0.

# Canon Style Studio

## LUT generator (local candidate, 22 October 2026)

Use **LUT GENERATOR · COLOR GRADING** to create a look with brightness, contrast,
saturation, hue, temperature/tint, separate RGB gamma, toe/midtone contrast/shoulder,
lightness and colour density. The adjustments preview on the current photograph,
survive project saving and undo/redo, and are baked into PF3 colour tables.
**Export .cube…** writes a 17-, 33- or 65-point sRGB LUT combining the look and
enabled LUT stack at their current strengths. No photograph is needed to export.
Camera base-style rendering, RAW development and spatial sharpening are excluded
from the `.cube`. New projects start with Standard; saved projects retain their base.
These are independent grading tools, not a claim to reproduce another app's formulas.

Local development candidate **1.0.0-dev** · Build **2026-10-18-WINDOWS-PORTRAIT-UI-FIX**

This local Windows candidate has a light editorial layout, a large left-hand
photo preview, right-hand adjustment cards and a reference gallery. It includes
six basic PF3 files for first use. The experimental Basic-control rewrite is
disabled in the editor; installation retains the matching-control workflow.
Nothing has been published; the published RC7 remains unchanged.

The supplied Canon logo is included in the header. **RAW samples…** opens an
optional, user-operated DPReview browser. **Open gallery** connects to the site;
select a photograph there, then **Download RAW and open**. The download uses the
same private browser session and preserves the displayed photograph's original
source and photographer credit. Existing browser profiles and cookies are not
imported. RAW photos are cached locally, not bundled with exported projects.
Cancelled, oversized, incomplete and non-RAW responses are rejected.

The current DPReview gallery schema was inspected in a normal browser, but direct
HTTP requests on this machine receive a Cloudflare challenge. The picker now uses
Qt WebEngine instead of that HTTP route. Site verifications are left to the user;
none are solved automatically. The actual renderer was checked with a local
gallery fixture, and download handling with controlled requests. A live DPReview
download in the embedded browser is **not yet validated**. The external-browser
button and **Open** for a locally downloaded RAW remain available.

Distributable builds now require and include rawpy/LibRaw. CR3 previews use the
original CMT1 orientation and camera metadata instead of assuming the embedded
JPEG contains them. This fixes portrait RAWs whose unrotated JPEG caused a
landscape Canon render. The reported IMG_2408.CR3 was checked with both decoding
paths and a real local DPP render; no camera was opened. Dialogs and menus have
explicit light backgrounds, slider handles are solid red circles, and spin boxes
use bundled arrow icons.

The editor integrates independent PF3 compilation and USB installation across the ten reconstructed Canon serializer families. It uses live capabilities, descriptors and complete slot-format validation rather than an RP-only gate. The catalog covers 77 known compiler identifiers and retains the reconstructed default dispatch for others; it is not a list of physically tested bodies. See [camera compatibility](CAMERA_COMPATIBILITY.md). Independent physical evidence remains EOS RP. Canon RAW development is a separate optional Canon-dependent feature.

Canon Style Studio is an experimental Windows editor for developing Canon RAW files through the Canon DPP4Lib runtime installed with Picture Style Editor, building sequential LUT stacks, previewing Canon's 33³/12-bit LUT result and exporting PF3 Picture Style files.

## Earlier changes in alpha.29

- Fixed generated PF3 bases that could produce black camera output by using identity matrices and neutral post-LUT curves.
- Corrected the PF3 Contrast and Sharpness Strength field mapping. Camera-registration state is not modified by this correction.
- Added compiler and transport reference implementations with automated tests to the source repository. They do not replace the editor's existing Canon workflow.

## Requirements

- Windows 10 or 11, 64-bit.
- For **Canon RAW development**, install Canon **Picture Style Editor**. The app discovers standard 64-bit and 32-bit Canon install locations; use **Locate PSE…** if it is installed elsewhere.
- Canon Digital Photo Professional is **not required**.
- **Send to Camera** uses the independent compiler and Windows WPD; no EOS Utility, Picture Style Editor or Canon DLL is required. Six included basic PF3 files initialize the independent editor automatically. Slot Basic controls must match the compiled style; unknown slot bytes are preserved. The style is saved before permission to replace the selected slot is requested. There is no automatic retry or restoration.
- The menu arrow beside **Send to Camera** opens the optional Canon fallback, which requires EOS Utility and Canon's own compiler. The main button opens independent USB without checking Canon prerequisites. Its older physical observations do not establish independent USB support for another body.

The Windows x64 standalone build includes its own Python runtime and application dependencies. Testers do **not** need to install Python or packages.

## Portable storage

Styles are saved directly in `Documents/Canon Style Studio PF3/`, using the Windows Documents location including folder redirection. One `.canonstyleproject` ZIP contains the compiled PF3, base, adjustments, snapshots and LUTs. No per-style directory or external JSON sidecars are created. Settings, caches and technical camera logs remain beside the application under `app_data/`. Legacy files remain readable and are never automatically deleted.

The distribution includes six authorized application-generated basic PF3 files. It contains no Canon DLL, executable, ICC/ICM profile, RAW image, native carrier, descriptor or captured payload. Optional Canon RAW rendering uses DPP4Lib and an input profile from the user's own local Picture Style Editor installation. Generated working PF3 data and caches are stored beside the application.

## Start

1. Copy the complete application folder to a writable location, or extract the entire ZIP there.
2. Run `CanonStyleStudio.exe` (or `START_CANON_STYLE_STUDIO.bat`).
3. In the app, press **Test** beside RAW engine. If PSE was not found, press **Locate PSE…** and select the folder containing `PSEditor.exe` and `DPP4Lib`.

Without PSE, JPEG/PNG/TIFF, LUT editing, independent PF3 generation from an owned input and independent USB installation remain available. Canon RAW development requires the optional DPP4Lib backend; LibRaw remains a separate fallback.

## Main workflow

- Open CR3/CR2, JPEG, PNG or TIFF references.
- Adjust Canon-native Exposure, fixed/Kelvin White Balance, WB Shift, Picture Style, Contrast, Saturation and Color Tone for RAW files. Fuji-style Recipe WB is a separate LUT-baked approximation calibrated from a controlled X-T1/Provia/5000 K reference sequence.
- Add `.cube` or Hald LUTs, reorder layers and set opacity. LUT-only changes reuse the cached Canon development.
- Use recipe-style Highlight and Shadow controls from -2 to +4 and Color from -4 to +4; shape a five-point monotonic Tone Curve; tune Red, Yellow, Green, Cyan, Blue and Magenta Hue/Saturation/Luminance axes; and add experimental Color Chrome-style or Blue Chrome-style density. Recipe Color is baked before the user LUT stack so each film-simulation LUT responds to the adjusted source colour; the remaining creative controls are baked after it. All reuse the cached Canon development.
- Use **Save Style** to save one `.canonstyleproject` archive with the compiled PF3, original base, every editor setting and all current/snapshot LUTs. Open it to continue editing and use Send to Camera on the restored state. Reference photographs are not embedded; their filenames remain as reconnect hints.
- Switch to **Canon 33³ Preview** to simulate only the final sequential LUT stack quantized to Canon's 33³/12-bit table.
- The Save Style file picker also offers a single plain `.pf3` for external tools. Old PF3s and JSON projects still open; a plain PF3 preserves its baked result but cannot reconstruct the original LUT layers. The independent writer uses the included basic files, so an empty cache and no user-supplied PF3 are supported.
- Use **Send to Camera**, find the USB camera and select User Def. 1, 2 or 3 directly. The app saves the style, asks permission for that destination, checks live compatibility, backs up the existing style and verifies the requested content after writing. Success requires matching readback and completed session cleanup.

The editor records `basePictureStyle` in projects and PF3 manifests. Public releases do not contain extracted Canon base PF3 files. The independent writer generates the six available bases locally after initializing the cipher from an owned PF3/project. The optional Canon fallback can also create an identity-table base through the installed EdsCFParse serializer.

Highlight, Shadow, Color, Tone Curve, Six Color-Axes and both Chrome-style controls are LUT-baked creative transforms, not claimed Canon-native PF3 controls. Working Preview places Recipe Color before the user LUT stack and the remaining creative stage after it. Canon 33³ Preview recomposes the same ordered pipeline into the final 33³/12-bit transform, matching PF3 table export.

Portable projects validate asset sizes and SHA-256 hashes before extraction, reject unsafe archive paths, and remain backward-compatible with the earlier plain-JSON project format. They contain the user's base and compiled PF3, editable settings, LUTs and any needed owned cipher reference. Canon DLL/ICC resources and RAW/JPEG/TIFF photos are not embedded. Plain PF3 imports preserve the baked look; their original LUT layers cannot be reconstructed.

**Independent USB installation has physical evidence on EOS RP; other bodies remain experimental.** The older Canon-native fallback has separate RP/R8 observations. No carrier or descriptor is bundled. Opening a RAW from a body does not validate installation support.

Fit, zoom and pan share stable view state. Zooming a RAW requests validated higher-detail Canon output where safe; portrait RAW is developed using the validated landscape-stage pipeline and returned in portrait orientation.

## Privacy-safe reports

Use **Create Test Report** in the top bar when reporting a problem. It includes app/runtime versions, camera model, dimensions, settings, LUT metadata and sanitized logs. Usernames and personal paths are replaced. The original RAW is **off by default** and is included only after two explicit confirmations.

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for the tester matrix and bug-report format, and [PUBLIC_ALPHA_RELEASE_NOTES.md](PUBLIC_ALPHA_RELEASE_NOTES.md) for validated and experimental boundaries.

## Validation and independent-mode research

Alpha.29 passed 601 automated tests, including a run from a clean source copy without private research fixtures. The packaged Windows executable also passed its startup smoke test without an external Python installation. These checks do not replace physical camera testing; no new camera registration was performed for this build.

The integrated independent compiler reproduces 24 archived RP/R8 carriers exactly and supports application-generated bases. Its family classifier matches archived dispatch evidence for 713 identifiers. The 694-test main suite passed, followed by targeted checks for final lifecycle, legacy-session, packaging and UI changes. An isolated Windows executable registered NC and Aerochrome in RP User Def. 3 without using the Canon runtime, with matching requested readback and user-reported appearance. The RC5 editor executable also installed Aerochrome in RP User Def. 2 with matching readback and completed cleanup; the user confirmed the look and normal operation. The editor exposes this controller experimentally. A machine with no Canon software installed has not yet been tested. Other bodies, firmware profiles and mobile USB adapters remain unvalidated.

First-run PF3 creation now uses the six included basic files, authorized by the user. Cipher tables are recovered in memory from these files; no fixed cipher table arrays or Canon DLL are required. The underlying zero-encrypted-input derivation has not been solved; it is no longer required by this first-run workflow. Canon RAW preview remains dependent on DPP4Lib; Working Preview is not a claim of Canon rendering equivalence.

See the [independent session results](research/RP_INDEPENDENT_SESSION_20261011.md) and [remaining cipher dependency](research/CIPHER_DEPENDENCY_20261011.md) for the evidence and current blockers. Native Apple Silicon and Intel development candidates now pass the regression suite and compiled Cocoa startup checks; see [macOS validation status](MACOS_PORT_STATUS.md). Mac USB installation remains disabled pending native camera validation. Android builds are not available.

## Legal notice

Canon Style Studio is independent experimental software and is not affiliated with or endorsed by Canon. Canon, DPP, Picture Style Editor and related names are trademarks of their respective owners. Users of Canon RAW development or the Canon fallback must install and license Canon software separately.
