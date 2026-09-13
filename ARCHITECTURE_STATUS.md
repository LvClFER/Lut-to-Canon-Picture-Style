# Canon Style Studio Architecture Status

Version 1.0.0-alpha.7

## Editor and RAW preview

- `canon_style_studio.py`: Qt editor, viewer, immutable render request capture, latest-state-wins UI and PF3 export dialog.
- `canon_dpp_worker.py`: isolated Canon DPP4Lib process. A DPP crash cannot directly terminate the editor.
- `dpp_client.py`: IPC, developed-RAW cache, render cancellation and bounded memory/disk caching.
- `render_geometry.py`: orientation, aspect ratio, Fit and portrait-safe geometry.
- `canon_engine.py`: CUBE/Hald parsing, sequential LUT stack, Working/Canon 33³ previews and EdsCFParse PF3 export.
- `creative_controls.py`: normalized Tone Curve, Six Color-Axes, experimental Chrome-style transforms and deterministic creative 3D LUT generation.
- `project_state.py`: atomic portable ZIP projects, embedded/deduplicated LUT assets, SHA-256/path validation, legacy JSON compatibility, `basePictureStyle`, snapshots and Undo/Redo.

Runtime storage is portable and rooted beside the executable (or beside the source tree in development): `app_data/` and `exported_styles/`. Camera-preparation artefacts are never automatically pruned or overwritten; microsecond timestamp plus style name gives each attempt a distinct folder. Legacy AppData settings are copied forward without deleting the source.

The working path is deliberately:

`Canon RAW → DPP4Lib selected Canon base → full-precision LUT stack → cached 33³ Creative Color stage`

The Canon 33³ path is:

`Canon RAW → DPP4Lib selected Canon base → LUT stack + Creative Color recomposed to 33³/12-bit`

The base style is never applied a second time to the DPP image.

## PF3 generation

PF3 export remains separate from RAW controls. Exposure, WB, WB Shift and Eyedropper are preview-only. The selected validated local PF3 base is copied through EdsCFParse, Basic/Sharpness fields are written, and the LUT stack followed by Creative Color is composed into `0x40001070` and `0x40001071`.

Public releases contain no Canon PF3. A local template must match the validated hash and the expected `0x00000114` Style ID. The generated PSE/EdsCFParse fallback is explicitly experimental because it does not preserve every property of the validated base.

## Camera installation boundary

The Canon-native camera workflow is coordinated by the editor UI but remains isolated in `camera_install/`. It discovers the compiler and camera inputs at runtime through EOS Utility, without external Manual Loader fixtures. Camera installation is not equivalent to PF3 generation:

`PF3 → EOS Utility/EdsCFParse live camera compiler → Canon-selected representation → unchanged EDSDK 0x01000203 transaction`

The exact selected PF3 is tracked inside EOS Utility. Its two 33³ tables must pass semantic conversion validation, and the resulting compiler output must match the outgoing EDSDK buffer byte-for-byte. Canon Style Studio never chooses a carrier or changes the EDSDK pointer/size. EOS Utility remains transaction owner and no GUI auto-click path is used.

Camera-registration property `0x00000115` is a binary state/control blob. Its pointer, size and contents must never be patched or used for an ASCII style name. Style names belong only in the two known EOS RP payload fields. This rule is scoped to the EDSDK registration transaction: it does not remove or reinterpret a historical PF3 property merely because it has the same numeric ID.

No carrier, descriptor, captured payload, Canon PF3 or compiler reference is distributed or required. `camera_install/eos_hook.py` manages Frida and EOS Utility; `camera_install/ui.py` captures immutable editor state and coordinates the user workflow.

Send to Camera has been physically exercised on EOS RP and EOS R8. RAW compatibility with another Canon body does not imply installation compatibility. The UI advises closing/reopening EOS Utility between successive registrations until its state-related reliability is better understood.

## Accuracy labels

- Canon-native path with pixel-change validation: DPP RAW base render, Exposure, fixed/Kelvin WB, WB Shift, Contrast, Saturation, Color Tone and the six tested base render IDs. This label does not claim pixel identity with every camera body or PSE/DPP version.
- Approximate preview: Sharpness and imported PF3 preview.
- Experimental LUT-baked controls: Tone Curve, Six Color-Axes and both Chrome-style effects. Their Working Preview/PF3 composition is tested, but they are not claimed manufacturer-native.
- `.canonstyleproject` is a portable ZIP containing sanitized project JSON, a manifest and all current/snapshot LUTs. Photos and Canon-derived binaries stay external; reference filenames are preserved only as reconnect hints.
- Experimental: generated PF3 base fallback, untested Canon bodies, cross-camera WB fidelity.
- Ground truth for camera calibration: actual EOS RP output after the loader-assisted installation path.
