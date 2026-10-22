# Canon Style Studio 1.0.0

First stable Windows editor release — 22 October 2026.

## Included

- Standalone Windows x64 application with its own icon and bundled core dependencies.
- Light editor layout; RAW Development first and expanded; unified red camera button with a white menu arrow.
- Standard default, six included generated PF3 bases, portable editable projects and reference-photo preservation when loading styles.
- Before/after divider, independent LUT comparison and snapshots.
- LUT generator with RGB gamma, colour, toe/midtone/shoulder, lightness and density controls; `.cube` export at 17/33/65 points.
- Independent PF3 generation and experimental Windows USB installation with slot selection and readback-gated success.
- Optional DPReview RAW sample browser with source/author credit.
- Fixes for export names containing the unsaved marker, PF3 contrast/sharpness mapping, and variable-length opaque PF3 properties. Thanks to kianimo for PRs #1–#3.

## Scope and limits

This stable label applies to the Windows editor. Independent USB physical validation covers EOS RP; other bodies remain experimental even when their compiler identifiers are catalogued. Existing slot Basic controls must match; unknown or conflicting formats are rejected. A failed driver session can need USB/power recovery. There is no automatic retry or rollback.

Exact Canon RAW base-style rendering still requires local Canon PSE/DPP4Lib; the bundled LibRaw fallback does not reproduce that renderer exactly. `.cube` exports exclude RAW development, camera base rendering and sharpening. Nikon NP3 colour conversion is unresolved. Android/macOS builds are not part of this release.

## Full disclosure

Developed by Filipe with extensive assistance from **OpenAI Codex** in code, reverse-engineering research, debugging, tests, packaging and documentation. Automated checks do not establish untested-camera compatibility. The project is independent of Canon, Nikon and OpenAI; these companies do not certify or endorse it.

Older alphas and RCs remain available as historical pre-releases. [Detailed compatibility](CAMERA_COMPATIBILITY.md) · [Pre-1.0 history](PUBLIC_ALPHA_RELEASE_NOTES.md)
