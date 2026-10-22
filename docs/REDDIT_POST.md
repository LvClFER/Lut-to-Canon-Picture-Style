# Reddit announcement draft

## Title

I made a Windows app for creating Canon Picture Styles and LUTs — v1.0.0

## Post

I've been working on Canon Style Studio, and the first stable Windows editor release is ready.

It lets you import LUTs, build a colour look with RGB gamma, curves and colour controls, compare before/after, save editable projects, and export Canon PF3 styles or regular .cube LUTs. The Windows download includes the core dependencies, so you can extract it and run it.

Full disclosure: I developed this with extensive help from **OpenAI Codex**, including coding, reverse-engineering research, debugging, tests and documentation.

A few limits worth being clear about: direct USB installation is still experimental and has only been physically tested on the EOS RP. Other Canon models are not guaranteed. Exact Canon RAW rendering needs a local Canon Picture Style Editor installation; the bundled LibRaw fallback is different. Nikon NP3 conversion isn't ready, and Android/macOS aren't part of this release.

The attached screenshot and before/after images show the app's desktop colour processing, not photos taken with a style installed in a camera.

Download and source: https://github.com/LvClFER/Lut-to-Canon-Picture-Style/releases/tag/v1.0.0

Feedback is welcome.

## Attachments

1. `images/editor.png` — actual editor screenshot.
2. `images/demo-before.jpg` — source JPEG, oriented and resized.
3. `images/demo-after.jpg` — same JPEG processed by the app.

Photo: Jojovavasasa, [Forest walk 05.jpg](https://commons.wikimedia.org/wiki/File:Forest_walk_05.jpg), CC0. [Complete media notes](images/CREDITS.md).

This is a prepared draft, not a record of a Reddit publication. Check the chosen community's rules/flair before posting.
