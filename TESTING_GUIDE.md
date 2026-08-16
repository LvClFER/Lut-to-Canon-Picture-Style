# Public Alpha Testing Guide

Thank you for testing Canon Style Studio. Use copies of important work and compare exported styles on a real camera or in Canon software before production use.

## Quick smoke test

1. Launch `CanonStyleStudio.exe` directly. Python must not be required.
2. Press **Test** beside RAW engine. Confirm `Canon DPP4Lib · READY`.
3. Open one landscape and one portrait CR3/CR2. Verify correct orientation, no stretched bands and no viewer jump when the final render arrives.
4. Test **Fit**, 100%, 200%, pan and side-by-side view. The centre, zoom and split should remain stable during renders.
5. On a daylight photograph, compare **Daylight** and **Tungsten**. Tungsten must become strongly blue. Try every WB mode, both WB Shift axes and Eyedropper WB.
6. Verify Standard, Portrait, Landscape, Neutral, Faithful and Fine Detail produce distinct images.
7. Drag Exposure and the Canon controls quickly. Obsolete results must not replace the latest setting.
8. Add at least two LUTs, change opacity and order, then enable Canon 33³ Preview. LUT-only edits should update without another RAW development.
9. Import one `.cube` of size 17, 33 and 64 plus a 16-bit Hald. Export PF3 and confirm validation succeeds.
10. Test Undo/Redo, snapshots A/B/C and save/reopen a project.
11. Open JPEG and TIFF references and confirm LUT editing still works.

## Compatibility matrix

Please cover, where possible:

- Windows 10 and Windows 11.
- A standard and a custom Picture Style Editor install location.
- Canon camera bodies other than EOS RP. Unknown Canon model names are accepted and identified as experimental.
- Landscape and portrait RAW files; high ISO, clipped highlights, mixed light and fluorescent light.
- Display scaling at 100%, 125%, 150% and 200%.
- LUT stacks with disabled layers, zero/partial/full opacity and reordered layers.

Source-build developers can additionally run:

```text
python SELF_TEST.py
python -m unittest -v REGRESSION_TESTS.py
python PUBLIC_ALPHA_REGRESSION.py --test-dir <folder-containing-test-files>
```

The regression matrix scans the supplied folder recursively and writes `PUBLIC_ALPHA_REGRESSION_REPORT.json`. Test RAW files are never copied into the public package.

## Report a bug

In the app choose **Create Test Report** and attach its ZIP. The RAW is not included unless you deliberately enable and confirm it.

Include:

- A short title and exact steps to reproduce.
- What you expected and what happened.
- Whether it reproduces after relaunch.
- Camera body and lens, if relevant.
- The control, WB mode, Picture Style and LUT sequence involved.
- A screenshot or short screen recording for viewer/zoom/flicker problems.
- A camera/PSE comparison image only when judging colour fidelity.

Do not send private RAW files unless they are genuinely necessary and you have checked their metadata.
