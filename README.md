# LUT to Canon Picture Style

Experimental tooling and reverse-engineering for carrying full 3D LUT transforms into Canon Picture Styles, with a currently validated workflow for the **Canon EOS RP**.

## Current build: EOS RP Manual LUT Loader v2.3

The current practical workflow accepts:

- `.cube`
- Hald `.tif` / `.tiff`
- `.pf3`

For LUT/Hald input, v2.3 also provides optional, generic LUT adjustments:

- Highlight
- Shadow
- Color
- Color Chrome-style
- Blue Chrome-style

Adjustment sets can be saved and loaded as JSON presets and applied to any source LUT. The app is not tied to a specific film simulation or recipe.

> **Status:** experimental, but usable on the EOS RP in the tested workflow. This is **not** a stock standalone-PF3 solution: the loader must be active during EOS Utility registration.

## How the RP workflow works

```text
.cube / Hald TIFF / PF3
        ↓
Canon dense 33³ representation
        ↓
Canon compiler path
        ↓
validated legacy 8192-byte LUT block
        ↓
EOS RP 16752-byte carrier payload
        ↓
normal EOS Utility Picture Style registration
        ↓
intercept outgoing 0x01000203 payload
        ↓
EOS RP
```

The final camera registration intentionally uses Canon's normal EOS Utility transaction. Direct third-party writes to the protected RP `0x01000203` property are not the supported path.

## Requirements

- Windows 10/11
- Canon **EOS Utility 3** installed
- Canon EOS RP connected by USB
- Python 3 for the current development package
- Dependencies from `requirements.txt`

Canon DLLs are **not** distributed by this repository. The loader uses Canon components from the user's own installed Canon software.

## Recommended install workflow

1. Connect the EOS RP by USB.
2. Start the loader.
3. Select a `.cube`, Hald TIFF, or `.pf3`.
4. Optionally apply generic LUT adjustments.
5. Generate the working PF3.
6. Arm the chosen User Def. slot in the loader.
7. In EOS Utility open **Camera settings → Register Picture Style File**.
8. Select the same User Def. slot, open the PF3 shown by the loader, and confirm.
9. Wait for the loader to confirm the patched `0x01000203` write returned `rc=0`.

### Important reliability note

For repeated preset registrations, the most reliable workflow currently is to **fully close EOS Utility after each successful preset and reopen it before registering the next one**. The loader itself can remain open.

## Important safety fix: `0x00000115`

`0x00000115` is a **32-byte binary camera state/control blob**, not a Picture Style name string. It is observed for diagnostics but **never modified** in current builds.

The camera-facing name is handled through the validated name fields inside the RP 16752-byte payload.

## What is intentionally not in the adjustment UI

Camera-side settings such as Dynamic Range, White Balance, ISO, Noise Reduction, and Sharpness are not LUT-generation controls, so they are not shown there.

Spatial effects such as Clarity and Grain cannot be represented honestly by an RGB→RGB 3D LUT, so they are not approximated.

## Source tree vs. release bundle

This repository keeps the public source and documentation small. The current experimental loader also uses compact binary fixtures captured/generated during the reverse-engineering work. Those fixtures are **not committed to the source tree**; use the packaged release bundle for a ready-to-run build.

See [`fixtures/README.md`](fixtures/README.md) for the expected fixture names and hashes.

## Documentation

- [Usage / troubleshooting](docs/USAGE.md)
- [Technical notes](docs/TECHNICAL_NOTES.md)
- [Current research status](docs/RESEARCH_STATUS.md)
- [v2.3 release notes](RELEASE_NOTES_v2.3.md)

## Compatibility

The practical loader-assisted registration path is currently validated on **EOS RP**. Historical encoder research also used an EOS 1300D, but the RP and 1300D compiled payload formats are not the same and should not be conflated.

## Legal

This is independent experimental software and is not affiliated with or endorsed by Canon or Fujifilm. Canon, EOS Utility, Picture Style Editor, Fujifilm, and related names are trademarks of their respective owners.

No Canon proprietary DLL is distributed in this repository. Users must install and license Canon software separately.
