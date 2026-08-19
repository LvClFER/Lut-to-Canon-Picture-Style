# GitHub cleanup applied by this snapshot

This clean snapshot is intended to replace the old Canon Style Studio public-alpha tree.

Removed from the old repository:
- `CanonStyleStudio.exe`
- the bundled `runtime/` Python tree
- old `PUBLIC_ALPHA_RELEASE_NOTES.md`
- old `STANDALONE_MANIFEST.json`
- old `START_CANON_STYLE_STUDIO.bat`
- old `TESTING_GUIDE.md`
- the obsolete public-alpha README and other stale root files

Kept/added for the current project:
- current v2.3 source under `TOOLS/`
- current README / manifest / release notes
- usage, technical and research-status documentation
- bug-report issue template
- generated identity Hald TIFF under `assets/`
- no Canon DLLs

The ready-to-run v2.3 release bundle remains separate from the source repository because it contains compact runtime/validation fixtures used by the current experimental loader.
