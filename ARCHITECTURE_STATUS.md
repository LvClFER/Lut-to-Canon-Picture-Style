# Canon Style Studio Architecture Status

Local candidate 1.0.0-dev; published release remains 1.0.0-rc.7

The Windows layout candidate keeps known Basic-control updates disabled in the
editor, retaining the matching-control path. The optional diagnostic update
requires a matching post-write state event in addition to exact style readback;
it has simulated evidence only. Unknown state bytes are preserved. See
`research/KNOWN_BASIC_CONTROL_UPDATES_20261018.md`.

## Camera workflow entry points

The main Send to Camera action opens the independent dialog without native prerequisites. Its menu exposes the retained EOS Utility fallback explicitly; only selecting that fallback resolves Canon requirements. Test reports distinguish independent RP physical evidence from the native fallback's older RP/R8 evidence. The current main window no longer displays the old Public Alpha label.

## Independent family integration

In RC7, strict PF3 3000 high reference records no longer block compact families 5/6: the verified format callback is a no-op, and builders use active records while projects retain the full reference bank. See `research/PF3_REFERENCE_BANK_CALLBACKS_20261018.md` for oracle and independent replay scope.

`family_registration_reference.py` connects the ten reconstructed serializers to the existing isolated registration controller. `camera_families_reference.py` retains known identifiers/names and the reconstructed non-default dispatch facts. Live slot grammar, descriptor structure and the intersection of WPD/DeviceInfo operations corroborate the choice; no Canon file is a runtime dependency. Legacy 24-byte state and modern 32-byte state remain separate and opaque. The pure compiler/framing/sequence core uses injected adapters; Windows WPD remains the implemented transport adapter.

Offline evidence covers the 77 catalog identifiers with synthetic live inputs and a simulated complete registration for each family. The new dispatcher also reproduces 24 complete historical RP/R8 carriers exactly with independently recovered keys and no Canon DLL reads. These are compiler/integration checks, not new physical-camera validation. RC5 also registered Aerochrome on RP User Def. 2 with exact requested readback and completed cleanup; the user confirmed the visible look and normal operation. Independent physical evidence remains RP; other bodies are experimental. Full constraints and model names are in `CAMERA_COMPATIBILITY.md`.

## Editor and RAW preview

- `canon_style_studio.py`: Qt editor, viewer, immutable render request capture, latest-state-wins UI and PF3 export dialog.
- `canon_dpp_worker.py`: isolated Canon DPP4Lib process. A DPP crash cannot directly terminate the editor.
- `dpp_client.py`: IPC, developed-RAW cache, render cancellation and bounded memory/disk caching.
- `render_geometry.py`: orientation, aspect ratio, Fit and portrait-safe geometry.
- `canon_engine.py`: CUBE/Hald parsing, sequential LUT stack, Working/Canon 33³ previews, independent PF3 generation and optional EdsCFParse fallback.
- `creative_controls.py`: normalized Tone Curve, Six Color-Axes, experimental Chrome-style transforms and deterministic creative 3D LUT generation.
- `project_state.py`: atomic portable ZIP projects, embedded/deduplicated LUT assets, SHA-256/path validation, legacy JSON compatibility, `basePictureStyle`, snapshots and Undo/Redo.

Style documents are flat files in the system Documents folder under `Canon Style Studio PF3/`. Each `.canonstyleproject` ZIP embeds its compiled PF3, base, adjustments and LUTs. Portable runtime state remains in `app_data/` beside the executable; camera PF3 extraction and reports use timestamped internal log folders. Duplicate style names receive numbered filenames instead of replacing prior exports. Legacy projects and plain PF3 remain readable.

The working path is deliberately:

`Canon RAW → DPP4Lib selected Canon base → full-precision LUT stack → cached 33³ Creative Color stage`

The Canon 33³ path is:

`Canon RAW → DPP4Lib selected Canon base → LUT stack + Creative Color recomposed to 33³/12-bit`

The base style is never applied a second time to the DPP image.

## PF3 generation

PF3 export remains separate from RAW controls. Exposure, WB, WB Shift and Eyedropper are preview-only. The independent source writer uses the owned cipher input, generates or preserves the selected base, writes Basic/Sharpness fields and composes the LUT stack followed by Creative Color into `0x40001070` and `0x40001071`. The optional Canon fallback copies a validated local base through EdsCFParse.

The local candidate includes six user-authorized application-generated basic PF3 files. These provide automatic cipher initialization on first use without a user-supplied reference or Canon installation; they are hash-checked read-only resources. User exports remain separate single documents. No fixed cipher table arrays are embedded in code. In the retained native fallback, a local template must match the validated hash and expected `0x00000114` Style ID. The generated PSE/EdsCFParse fallback remains experimental.

## Retained Canon-native fallback boundary

The older Canon-native camera workflow remains isolated in `camera_install/`; the primary editor dialog uses the independent controller described above. It discovers the compiler and camera inputs at runtime through EOS Utility, without external Manual Loader fixtures. Camera installation is not equivalent to PF3 generation:

`PF3 → EOS Utility/EdsCFParse live camera compiler → Canon-selected representation → unchanged EDSDK 0x01000203 transaction`

The exact selected PF3 is tracked inside EOS Utility. Its two 33³ tables must pass semantic conversion validation, and the resulting compiler output must match the outgoing EDSDK buffer byte-for-byte. Canon Style Studio never chooses a carrier or changes the EDSDK pointer/size. EOS Utility remains transaction owner and no GUI auto-click path is used.

Camera-registration property `0x00000115` is a binary state/control blob. Its pointer, size and contents must never be patched or used for an ASCII style name. Style names belong only in the two known EOS RP payload fields. This rule is scoped to the EDSDK registration transaction: it does not remove or reinterpret a historical PF3 property merely because it has the same numeric ID.

No carrier, descriptor, captured payload, Canon PF3 or compiler reference is distributed or required. `camera_install/eos_hook.py` manages Frida and EOS Utility; `camera_install/ui.py` captures immutable editor state and coordinates the user workflow.

The retained Canon-native fallback has been physically exercised on EOS RP and EOS R8. RAW compatibility with another Canon body does not imply installation compatibility. The UI advises closing/reopening EOS Utility between successive registrations until its state-related reliability is better understood.

## Accuracy labels

- Canon-native path with pixel-change validation: DPP RAW base render, Exposure, fixed/Kelvin WB, WB Shift, Contrast, Saturation, Color Tone and the six tested base render IDs. This label does not claim pixel identity with every camera body or PSE/DPP version.
- Approximate preview: Sharpness and imported PF3 preview.
- Experimental LUT-baked controls: Tone Curve, Six Color-Axes and both Chrome-style effects. Their Working Preview/PF3 composition is tested, but they are not claimed manufacturer-native.
- `.canonstyleproject` is a portable ZIP containing sanitized project JSON, a manifest and all current/snapshot LUTs. Photos and Canon-derived binaries stay external; reference filenames are preserved only as reconnect hints.
- Experimental: generated PF3 base fallback, untested Canon bodies, cross-camera WB fidelity.
- Ground truth for camera calibration: actual EOS RP output after the loader-assisted installation path.
