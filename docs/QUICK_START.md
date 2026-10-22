# Quick start

1. Download the Windows x64 ZIP from the [v1.0.0 release](https://github.com/LvClFER/Lut-to-Canon-Picture-Style/releases/tag/v1.0.0).
2. Extract the entire ZIP and run `CanonStyleStudio.exe`. Keep its `runtime` folder beside it.
3. Open a photo or supported RAW file. RAW Development is the first adjustment panel. Standard is the starting base style.
4. Import a `.cube`/Hald LUT or create a look under **LUT GENERATOR · COLOR GRADING**. Use **Split** for before/after and **Compare LUTs…** to compare imported LUTs separately.
5. Use **Save Project** / **Save style** for an editable `.canonstyleproject` and PF3 export. Use **Export .cube…** in the LUT generator for a generic sRGB colour LUT.
6. Projects and styles default to **Documents / Canon Style Studio PF3**. Opening a style preserves reference photographs already loaded in the editor.

## RAW rendering

The app includes LibRaw. Exact Canon base-style RAW rendering additionally uses Picture Style Editor's local DPP4Lib; use **Locate PSE…** if needed. No Canon DLLs are distributed. An embedded camera JPEG may already carry a look and is not a neutral RAW reference.

## Camera installation

Read [camera compatibility](../CAMERA_COMPATIBILITY.md) first. Connect a supported Canon camera by USB, close other camera applications, choose **Send to Camera**, find the camera and select User Def. 1, 2 or 3. Review the name and destination before installing. The app saves the existing style before writing and only reports success after its required verification/cleanup checks. The independent workflow has physical evidence on EOS RP only; other models are experimental. Conflicting Basic settings are blocked. A backup is not an automatic restoration transaction.

## Reporting a problem

Use **Create Test Report** and review the contents before sharing it. Include the app version, Windows version, camera model/firmware, selected slot and steps to reproduce. Never post raw USB identifiers or private photographs unintentionally.
