# EOS RP Manual LUT Loader v2.3

v2.3 is the current practical experimental build.

## Changes

- General-purpose `.cube`, Hald TIFF, and `.pf3` workflow.
- Removed hard-coded film-simulation/recipe use cases from the UI.
- Added generic optional LUT adjustments:
  - Highlight
  - Shadow
  - Color
  - Color Chrome-style
  - Blue Chrome-style
- Adjustment settings can be saved/loaded as reusable JSON presets.
- Adjusted LUT exports use `<source>_ADJUSTED.cube`.
- `0x00000115` remains diagnostic-only and is never patched.
- EOS Utility restart between successive preset registrations is now the recommended reliability workaround.

## Important limitation

The generated PF3 is a working carrier for the loader-assisted RP registration path. Arbitrary LUTs are **not claimed to work as stock standalone RP PF3 files** without the loader active during registration.

## Requirements

- Windows 10/11
- EOS Utility 3 installed
- EOS RP over USB
- Current release bundle / dependencies

Canon DLLs are not redistributed.
