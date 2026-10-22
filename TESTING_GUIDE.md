# Testing Canon Style Studio

## Automated checks (no camera access)

Install the source dependencies, then run from the repository root:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest REGRESSION_TESTS.CoreRegressionTests
```

The test suite lives in `tests/`. USB tests use injected transports and synthetic data; automated passing results do not establish physical camera compatibility. Source packaging is audited for missing runtime modules and excluded private/native artifacts. Legacy entry points such as `SELF_TEST.py`, `REGRESSION_TESTS.py` and `UI_SMOKE_TEST.py` remain at the root for compatibility.

## Editor smoke check

1. Extract the entire Windows ZIP. Run the EXE without a separate Python/Java/Node installation.
2. Confirm Standard is the default, RAW Development is first/expanded, and the camera menu has a white arrow on the same red background.
3. Open portrait and landscape references. Check Fit, zoom, pan and the before/after divider.
4. Use the LUT generator, import two LUTs, compare them independently, change layer strength/order, and test undo/redo plus A/B/C snapshots.
5. Export a PF3 and .cube LUTs at 17/33/65 points. RAW development, camera base rendering and sharpening are excluded from .cube export.
6. Save/reopen an editable project. Loading a different style must preserve photos already loaded in the editor; saved references are used when no photos are loaded.
7. Verify exports appear directly in Documents / Canon Style Studio PF3 and duplicate names receive a numbered suggestion.
8. If PSE is installed, test its RAW renderer with portrait/landscape CR2/CR3 files, exposure/WB and native basic controls. Without it, check the clearly distinct LibRaw fallback. Do not treat a camera's embedded JPEG as a neutral RAW reference.
9. Optionally use RAW samples to open a DPReview gallery and download an available RAW. Any site verification is completed by the user. Confirm source and author credit remain visible.

## Camera tests

[Compatibility and safeguards](CAMERA_COMPATIBILITY.md) describe current scope. The independent route has physical EOS RP evidence; other camera identifiers are not physical validations. Physical tests require a deliberately selected body, style and destination slot. A baseline backup and required readback/cleanup checks must succeed. No automatic retries or rollback are provided. Driver failures can need USB/power recovery.

## Platform scope

The v1.0.0 release ships Windows x64. macOS and Android source/status documents describe development candidates, not additional stable downloads or physical USB validation.
