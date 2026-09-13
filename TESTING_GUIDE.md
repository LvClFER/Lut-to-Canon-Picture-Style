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
9. Expand **Tone Curve · Color Axes**. Drag all five curve points; tune every Red/Yellow/Green/Cyan/Blue/Magenta axis; compare Weak/Strong Color Chrome-style and Blue Chrome-style. These changes must reuse the current Canon development.
10. Compare Working Preview with Canon 33³ Preview, export PF3 and verify the project/manifest retains the complete Creative Color state.
11. Import one `.cube` of size 17, 33 and 64 plus a 16-bit Hald. Export PF3 and confirm validation succeeds. Note whether the export used a hash-validated local Canon base or the clearly labelled experimental generated fallback.
12. Test Undo/Redo and snapshots A/B/C. Save a `.canonstyleproject`, copy it to another folder/computer, remove or rename the original LUT files, reopen it, and confirm every setting plus every current/snapshot LUT is restored. The photo must be requested separately and the previous viewer image must not remain visible.
13. Open JPEG and TIFF references and confirm LUT/Creative Color editing still works.
14. Resize the left sidebar wider and narrower. It must extend beyond 390 px and must never show a horizontal scrollbar.
15. Without copying or importing support files, prepare a style and verify a new persistent folder appears under `exported_styles/`; a second preparation must create another folder and preserve the first.
16. Move the complete extracted application folder to another writable path/user. Settings and locally generated runtime data must remain available without relying on the original Windows username; no support-file import may be requested.

## Compatibility matrix

Please cover, where possible:

- Windows 10 and Windows 11.
- A standard and a custom Picture Style Editor install location.
- Canon camera bodies other than EOS RP. Unknown Canon model names are accepted and identified as experimental for RAW rendering.
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

## Camera-install boundary

This Public Alpha integrates the loader-assisted EOS RP workflow under **Send to Camera**. Successfully opening a CR2/CR3 still validates only RAW compatibility with the locally installed DPP4Lib; it does not validate a camera-registration payload for that model.

The arbitrary-LUT installation path has been physically exercised on EOS RP and EOS R8. It requires EOS Utility 3 but no external Manual Loader fixtures. Other bodies remain experimental until a real camera confirms the result; RAW compatibility alone does not validate camera installation.

EOS RP physical test:

1. Close EOS Utility completely, connect the EOS RP and open **Send to Camera**.
2. Do not add any support folder. Confirm the same public build reaches the ready state using only the locally installed Canon software.
3. Click **Prepare / Capture** and wait for the target-PF3 hook to arm.
4. In EOS Utility choose User Def. 1, 2 or 3 and select the generated PF3.
5. In EOS Utility, perform a normal Picture Style registration using the PF3 opened by the app.
6. Confirm the log reports semantic table validation, an exact compiler-to-EDSDK buffer match, `rc=0`, and that `0x00000115` was untouched.
7. Close/reopen EOS Utility before another registration.

For serious colour calibration, keep these comparisons distinct:

- Canon Base Render: selected Canon style developed by DPP4Lib.
- Working Preview: Canon base render plus the full LUT stack.
- Canon 33³ Preview: Canon base render plus exactly the quantized transform stored in PF3 tables.
- Camera Ground Truth: an actual camera file after a physically validated installation workflow.

## Report a bug

In the app choose **Create Test Report** and attach its ZIP. The RAW is not included unless you deliberately enable and confirm it.

Include:

- A short title and exact steps to reproduce.
- What you expected and what happened.
- Whether it reproduces after relaunch.
- Camera body and lens, if relevant.
- The control, WB mode, Picture Style and LUT sequence involved.
- A screenshot or short screen recording for viewer/zoom/flicker problems.
- A camera/PSE comparison image only when judging colour fidelity; identify which of the four preview/ground-truth stages it represents.

Do not send private RAW files unless they are genuinely necessary and you have checked their metadata.
