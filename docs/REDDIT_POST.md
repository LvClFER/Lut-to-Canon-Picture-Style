# Reddit announcement draft

## Title

I made Style Studio, a Windows editor for Picture Styles, LUTs and RAW previews

## Post

Hello!

I wanted to share **Style Studio**, a Windows app I built for creating Picture
Styles and colour LUTs. It is an independent community tool: the name and UI do
not use Canon branding, while Canon is mentioned only where it describes
compatible PF3 files, RAWs or cameras.

### TL;DR

Style Studio is a standalone Windows editor for Picture Styles, LUTs and RAW
previews. The editor is ready for public testing; the official Canon workflow
is still the recommended way to install a style whenever it accepts the PF3.
There is an independent USB installer, but it remains explicitly experimental,
has been physically validated only on an EOS RP, and may require camera
recovery if it fails. The long version below explains exactly why.

### What it does

You can open a photo or supported RAW, import `.cube` LUTs/Hald images/PF3
styles, build a look with curves, colour controls and LUT stacking, compare
before/after, and save the whole editable project as one file. It exports PF3
styles and standard `.cube` LUTs. The Windows ZIP includes its runtime, so it
does not require Python, Java or Node to be installed.

There is also an optional USB camera-install path with explicit camera and
User Def. slot selection, backup/readback checks and a confirmation only after
verification. I also added a user-operated RAW sample browser that preserves
source and author credit.

### Why not simply send the PF3 with Canon's own app?

That is still the preferred route whenever Canon's software accepts the exported
PF3. Its workflow is camera-specific: it validates the file, compiles it and
serializes the resulting payload for the connected body and selected slot. A
PF3 created outside that workflow is not guaranteed to pass those proprietary
checks, even if it opens in another tool; the result can vary by camera family.

Style Studio therefore does not bundle or replace Canon software. The optional
direct USB route exists only for cases where an independently generated style
cannot be sent through that path. It is deliberately labelled experimental and
uses validation, backup and readback checks, but it is **not** safer than the
official workflow. If Canon's app accepts the PF3 for your camera, use it.

### Technical transparency: what I actually found and built

This did not start as a claim that a PF3 is “just a LUT”. I began by comparing
styles made through the normal Canon workflow with controlled changes: name,
Basic controls, LUT tables and target slot. The files contain both editable
style information and opaque camera-family-dependent data. The same visual look
does not necessarily produce the same transport representation on every body.

From those comparisons and local, user-owned workflow observations, I found
three relevant layers:

1. **PF3/style data.** The app can generate, inspect and preserve the known
   fields and LUT data needed by its supported style workflow.
2. **Canon-assisted send.** When the optional official path is used, EOS Utility
   still owns the camera session. It parses the selected PF3, builds the
   camera-native payload and performs the actual send. For a narrowly identified
   target style, Style Studio applies a temporary in-memory compatibility patch
   at the compiler's acceptance stage so the tables are not discarded. It does
   not modify camera firmware, replace the outgoing payload, write Canon files
   to disk, or ship Canon binaries. The generated payload is checked against the
   buffer produced by Canon's own compiler before the normal send proceeds.
3. **Independent USB send.** This avoids Canon software and DLLs. It uses a
   reconstructed serializer/slot grammar and Windows' portable-device layer,
   with capability checks, a backup/readback attempt and bounded timeouts. This
   is the riskier, experimental route.

### How the reverse-engineering process unfolded

The original question was deliberately small: could an editor create a useful
PF3 and then use the camera workflow without requiring users to hunt through
temporary folders or install a development environment? It quickly became
clear that a visual LUT and a camera-installable style are related, but not the
same thing.

I made controlled files from the normal workflow, changing one thing at a time
(base style, name, basic controls, a LUT, and destination slot) and compared
the resulting structures. That showed which parts behaved like ordinary style
data, which parts were 33³ LUT tables, and which parts were opaque or changed
with the target camera family. Next I traced the normal desktop workflow: EOS
Utility receives a PF3, invokes its own compiler/serializer and sends that
camera-specific result, rather than blindly forwarding the original file.

That led to two separate implementations instead of one overconfident claim:
the Canon-assisted route lets its installed software retain ownership of the
camera session and output buffer; the independent route was built read-first,
then with one-slot backups, bounded requests and readback attempts. Every
physical write was treated as a separate test. The EOS RP tests confirmed that
the approach can work, but also exposed a failure state that required
USB/power recovery. That finding changed the product decision: direct USB is
useful experimental engineering, not a feature I will market as universally
safe.

The independent route was developed in small, reversible stages: enumerate the
camera; read descriptors and a selected slot; test local serialization against
known structures; send one authorized style; read it back; then stop on any
unexpected state. During that work I did hit a camera error that needed the
usual USB/power recovery. That is exactly why the feature is not presented as a
universal, safe replacement for Canon's software.

The physical evidence I am willing to claim publicly is EOS RP installation and
readback/visual confirmation in User Def. 2 and 3. The code contains support
knowledge for additional serializer families, but that is **not** the same as
physical compatibility proof for every camera. I will not claim otherwise.

No Canon camera firmware, proprietary DLL, captured camera payload, or Canon
resource file is included in the release. The project uses only its own code,
the user's chosen files and, for the optional Canon-assisted path, Canon software
already installed by that user.

### Could Canon add this themselves?

Almost certainly. Canon already owns the format parser, per-camera serializers,
the desktop/mobile transport code and the validation rules. An official feature
could expose a documented import endpoint or accept a standard LUT/PF3 subset,
then run the exact same model-specific validation before sending.

I cannot know Canon's reasons for not exposing that as a supported workflow. My
best inference is that the hard part is not a single upload button; it is
maintaining compatibility, colour expectations, safety testing and support
across a large range of bodies and firmware versions. That is precisely the
burden an unofficial project cannot claim to have solved.

### Status

The Windows **editor** is the part I consider ready for public testing and
feedback. Direct USB/PTP installation is still experimental: it has physical
evidence on an EOS RP only, and it can fail on other bodies. It can require a
USB/power recovery and has no automatic rollback. Please do not use it on a
camera you are unwilling to recover manually.

Exact Canon base-style RAW rendering still requires the user's local Picture
Style Editor installation. The bundled LibRaw rendering is useful for editing,
but it is not an exact replacement. Android and macOS builds are in progress.

### Full disclosure

This was **100% vibe coded with OpenAI Codex**. I set the goals, supplied the
test files/hardware observations and reviewed the results; Codex did the
implementation, reverse-engineering research tooling, debugging, test work,
packaging and documentation. That assistance and the automated tests are not
independent certification, a security audit or proof of compatibility with
untested cameras.

### Links

Source and Windows build: https://github.com/LvClFER/Lut-to-Canon-Picture-Style

I do not want to write a giant wall of text here; the README and compatibility
notes explain the supported workflow and limits. Feedback, reproducible bug
reports and hardware-test results are welcome.

## Attachments

1. A current Style Studio editor screenshot, captured from this public build.
2. A source image and corresponding preview, labelled as desktop colour
   processing rather than an in-camera result.

Use only photographs you are entitled to share and credit them in the post.
This is a prepared draft, not a record of a Reddit publication. Check the
chosen community's rules and flair before posting.
