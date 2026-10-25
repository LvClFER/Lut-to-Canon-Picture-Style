# Android RAW: verified sensor decode and remaining Canon rendering work

The Android editor now decodes the RAW sensor plane with LibRaw 0.22.2. It never
substitutes an embedded JPEG if decoding fails. This matters because that JPEG
may already contain an arbitrary in-camera Picture Style, which cannot safely
be used as the input to another style.

## Evidence

The native decoder was built for ARM64/x86-64 with NDK 28.2.13676358 and tested
inside an Android 15 x86-64 emulator. The fixture is an existing downloaded EOS R
CR3, kept in the private development cache rather than bundled in the APK.

Two equal-length inputs were compared:

- Original SHA-256: `bbd1db83469504e8fde76a61c28c2670216b13b3841cd6cc4b0d104092a2ce42`.
- Mutant SHA-256: `cc58cff06110595a11dd24f243a9e56098b21c71cf73ea8ca53fdb2f0452e99c`.
- Only the largest embedded JPEG range, bytes 403296 through 2831885 inclusive,
  changed; its replacement is a red JPEG with the same 6720 × 4480 dimensions.
- All bytes outside that range, including the compressed sensor payload, matched.
- Both native developments returned 3371 × 2249 RGB pixels with SHA-256
  `c3b0375ba4736dd86c4a8bf7a59ce935342848afcaea7fc91a72ebe45204429b`.

The harness also rejects invalid RAW input and checks ordinary portrait rendering,
PF3 export, portable project/photo preservation and private-session recovery.
An emulator test is not ARM64 execution or physical USB validation.

## What this does not establish

The six bundled PF3 `0x1071` tables are all mathematical identity tables,
SHA-256 prefix `7a5c2f3fc6aefc9c`. Their base selectors tell the Canon camera which
built-in style to use. They do not supply that style's full standalone RAW colour
pipeline. Importing them into an independent RAW engine cannot, on its own,
reproduce Canon Standard, Portrait, Landscape, Neutral, Faithful or Fine Detail.

Canon DPP references for all six selections were produced locally from the RAW,
using an isolated process and the installed Canon runtime. Initial small-canvas
references were rejected after a geometry check showed a cropped field of view.
The subsequent references use a 1680 × 1120 native canvas before reduction to
672 × 448; matching full field of view was also checked at 3360 × 2240.

A direct-ICC shortcut was evaluated using the installed SS/PS/LS/NS/FS/FDS input
profiles. Thirty fixed LibRaw colour-space/gamma/brightness configurations were
compared across the six references. The best tested combination still had a
mean absolute RGB error of 14.23 on the 0–255 scale. This is not an exhaustive
proof of impossibility, but it is sufficient to reject that shortcut as a
validated Canon renderer. No inferred correction fitted to this single scene
and no Canon ICC resource was added to the app.

The remaining independent-rendering task is to reconstruct or calibrate the
Canon camera-to-working-space transform and base-style processing, then check
it against separate RAW scenes and camera models. Decoding real RAW and matching
Canon rendering are separate acceptance criteria. Current UI metadata explicitly
sets `canon_base_render_verified` to false.

## Native colour-stage trace, 21 October

An isolated, bounded Python child was instrumented locally; no camera session
was opened. The six style selections generated six distinct 217,828-byte ICC
profiles, in addition to the installed Neutral input profile and Canon's sRGB
output profile. These are private research captures, not application resources.

`UCSMatchPixmap` was observed processing three planar, little-endian RGB16
buffers in place. The main frame had 1,753,920 pixels, a 3,248-byte row stride
and inferred dimensions 1,624 × 1,080. The dimensions describe this intermediate
buffer, not a verified sensor crop or the requested final output dimensions.
Before/after planes were captured for all six styles without instrumentation
errors. The input planes already differed between styles: the significant
RAW development and some style processing happen upstream of this call.

A separate LittleCMS/Pillow experiment applied each captured style profile to
its captured input, using the captured Canon sRGB output profile. Inputs were
rounded from RGB16 to RGB8; output error below is measured against the native
RGB16 result scaled to 0–255. This tests only the isolated colour stage and
includes quantization and potentially different profile-chain/CMM behaviour.

| Style | Mean absolute error | 99th percentile | Maximum |
| --- | ---: | ---: | ---: |
| Standard | 1.0623 | 3 | 15 |
| Portrait | 0.9779 | 3 | 15 |
| Landscape | 1.0582 | 4 | 13 |
| Neutral | 1.1102 | 4 | 18 |
| Faithful | 1.0775 | 4 | 18 |
| Fine Detail | 0.9421 | 3 | 15 |

These results do not establish equivalence, even for the isolated stage. The
native caller can combine two or four profile transforms; replacing that chain
with one input/output pair is not yet validated. A native backtrace located the
colour-stage wrappers in this installed DppCore binary at RVAs `0x159fc0`,
`0x15d8d0` and `0x15d9c0`. These version-specific research addresses are not
portable APIs and must not become production assumptions.

The generated profiles use `mft2` tables with three input/output channels,
a 33-point cube, 16 input-curve entries and 256 output-curve entries. Profile
differences span the colour tables rather than just an identifying name. Neutral
captures from separate processes differed only in the last two bytes of the
profile; raw file hashes must therefore not be treated as stable style IDs.

Changing the order of setting the base selector and the user profile produced
identical reference renders. Returning to Neutral after the other five styles
also reproduced the first Neutral render exactly. That rejects stale style
state or setter ordering as the explanation for the missing Android base look.

Private reproducibility data lives under the development cache's
`raw-validation/ucs-planes-20261021` (capture script, metadata, planes and
`icc-stage-evaluation.json`), with bounded backtrace and profile-chain probes in
the adjacent `ucs-backtrace-20261021` and `ucs-chain-20261021` directories.
Next acceptance work is the exact profile chain and upstream tone/colour
processing, followed by independent scenes and models. No application behaviour
or verified-render flag was changed on the strength of this experiment.

## Profile-chain and native sampling follow-up

Following the profile data from the live handles confirmed the warm-up uses
two transforms, while the measured main frame uses four:

`generated style → Canon sRGB → installed Neutral → Canon sRGB`.

The profile-map trace is in `ucs-chain-profile-map-20261021`. Directions `2` and
`3` are recorded native values; their broader API semantics have not been
established. A Java/LittleCMS RGB16 raster experiment sampled 109,620 pixels per
style, avoiding an RGB8 intermediate. A direct input/output pair still gave
mean errors of 0.949–1.142 levels; two sequential profile-pair conversions gave
1.144–1.352. A four-profile Java transform was rejected by LittleCMS, so the
sequential result must not be called an exact reproduction of the native chain.
The earlier discrepancy is therefore not explained solely by RGB8 input rounding.

The live native transform was also sampled with a synthetic 33³ RGB grid, using
an owned child and bounded allocations. All six calls in `ucs-cube-20261021`
returned success. NumPy interpolation then used only those sampled values,
without calling Canon during evaluation. Against the captured photo pixels,
tetrahedral interpolation plus flooring gave mean error 0.354–0.374/255 and
maximum error 3/255. This is an isolated-stage approximation on one scene,
not a validated general RAW renderer or an asset approved for distribution.

Every captured colour-stage output value, including the synthetic cube, was a
multiple of 257. The input planes contain many nonmultiples. In this observed
configuration, the RGB16 output thus stores replicated RGB8 codes; RGB16 storage
does not prove 16-bit colour precision. This explains why precision and rounding
must be measured rather than inferred from the descriptor.

An additional flags-preserving sampling run returned native error 1430 for
Landscape. Its missing cube was not substituted or included in the successful
six-style benchmark. Re-entrant sampling remains a research probe rather than
a reliable production extraction interface. No sampled cube or Canon ICC has
been added to the app, and the upstream RAW tone/colour stage remains unresolved.

## Upstream recipe and curve evidence

Live dispatches and RTTI identified the observed processing stages as
`CDppInterpolateFullLowQualityProc`, `CDppRGBWbProc`,
`CDppVignettingCorrectionProc`, `CDppRawRecipeProc`, `CDppProfileProc`,
`CDppRGBRecipeProc`, `CDpp8AxisProfileProc`,
`CDppActualColorSpaceProfileProc` and `CDppColorMoireReductionProc`.
This is an observed dispatch sequence, not proof that every stage changes pixels
or that there are no other processing paths. The recipe stage in this binary
enters at `0x1e0410`; the observed numerical branch enters at `0x1e9d30`.
The branch's parameter block contains style-dependent integers as well as table
pointers. Their mathematical meaning is not inferred from their values alone.

A recipe buffer feeding parameter offset `0x108` declares 8,192 bytes. Reading
that declared allocation yielded 2,048 little-endian signed 32-bit entries,
monotonic and ranging from 0 to 1,023. In the first fixture:

- Standard, Portrait and Landscape shared SHA-256
  `711441f815cf5f71eea1c41dbd9e40f8424cfffb2907113a67e3028a059ad51c`.
- Neutral, Faithful and Fine Detail shared SHA-256
  `0ee79da2ddac583855c65070ddfa20afe9d1ca2319ade056770219000115935a`.

These are live recipe curves, not curves read from the bundled identity PF3s.
Forty-eight actual native lookup instructions were observed. Each table prefix,
index and returned value matched the captured Standard curve exactly. The
one-shot instruction hooks detached after their first hit to avoid instrumenting
the entire pixel loop. Live lookups were checked on Standard only; the other
styles have buffer-capture evidence rather than equivalent instruction checks.

Three existing local EOS R RAWs, plus -2 EV and +2 EV developments of the first
RAW, were then checked with Standard, Neutral and Fine Detail: 15 curve cases.
No new network sample was downloaded. Curves changed slightly between scenes,
so two captured files must not be hardcoded as universal Canon curves. The
diagnostic resampling `base_curve(x * 2**EV)` predicted +2 EV within one code
value (mean 0.0015–0.0034 on the 0–1,023 scale), and -2 EV within 1.5 values
(mean 0.155–0.170). This supports input-domain exposure scaling but does not
establish the remaining normalization, rounding or camera-specific generation.

An earlier candidate lookup generator at `0x59f30` produced a constant 128 table
in this configuration. It is not the captured tone curve and was excluded from
the curve proof. Its broader purpose remains unverified.

Private evidence: `upstream-stage-types-20261021`,
`raw-recipe-curves-20261021`, `raw-curve-live-lookups-20261021`,
`curve-validation-20261021.json`, `curve-exposure-scaling-20261021.json` and
the assert-based `verify_curve_lookups.py` / `curve-proof-20261021.json`.
The numerical input normalization, preceding white-balance transform and
style-dependent coefficients still need reconstruction and cross-model checks.
These findings have not changed the Android verified-render flag or shipped data.

## White balance and descriptor normalization

The observed `CDppRGBWbProc` pixel loop uses unsigned RGB16 input, Q10 integer
gains and a bounded integer result:

`output = min(limit, ((input * gain) & 0xffffffff) >> 10)`.

The installed loop also tests signed negativity before writing the unsigned
word. The observed and synthetic unsigned inputs/gains never produce a negative
shifted result; general signed-input or arbitrary-gain behaviour is not validated.
The two observed gain triplets, `[2162,1024,1319]` and `[2040,1024,1475]`, match
the three RAWs' camera-WB metadata normalized to green = 1024.

The descriptor helper at RVA `0x561e0` scales six input doubles with
`f = 2**(12 - descriptor[0])`, returning three integers in pointer-argument order:

`[int(descriptor[1]*f), int(descriptor[3]*f), int(descriptor[2]*f)]`.

All three EOS R fixtures report descriptor precision 14. For the first RAW at
zero exposure, the first four values are
`[14,0,20508.181382128383,1200]`, returning `[0,300,5127]`.
At -2 EV, the third/fourth descriptor values are four times larger; at +2 EV,
they are four times smaller. The precision field remains 14. The last returned
integer is used by the observed WB clipping calculation, with the additional
exposure-dependent calculation below:

```python
adjusted = int(returned_white / max(0.1, min(1, 2**exposure)))
limit = max(16383, min(32767, adjusted * 16383 // 4095))
```

This describes the observed helper and WB loop, not a rule for applying exposure
twice in the independent renderer. The descriptor values themselves already
depend on exposure; their upstream generation is still to be recovered.

Five fixture/settings cases (three scenes and the first scene at ±2 EV) checked
the normalization and WB loop. An additional five isolated child runs injected
synthetic values into the child's pixel buffers only, spanning 0–65535. They
did not write the source RAWs; before/after SHA-256 checks confirmed this. These
synthetic runs establish arithmetic and clipping behaviour, not photographic
reference renders. The clipping limits observed were 20511, 20631, 32767 and
16383. Replaying the recorded observations with Python's standard library,
without loading Canon code, matched:

- 40 descriptor-helper results;
- 320 natural RGB pixel triplets;
- 320 synthetic RGB pixel triplets, including 315 clipped channel results.

Private evidence is in `wb-validation-*-20261021`, `wb-boundary-*-20261021`,
`validate_wb.py`, `validate_wb_boundaries.py` and the independent replay
`replay_wb.py` / `wb-independent-replay-20261021.json`. The normalization helper
and WB arithmetic are now reproduced for these observations. This does not
establish how LibRaw's developed pixels map to the loop input, how Canon builds
the descriptor, or the remaining colour coefficients. No partial WB stage is
applied on top of the already white-balanced Android preview.

## Active-area geometry correction

LibRaw metadata for the EOS R fixture reports a 6742 × 4498 development area,
but the camera's default inset is 6720 × 4480. Its absolute origin is (156,58),
relative to LibRaw sensor margins (146,48): the development crop therefore starts
at (10,10). The Android decoder now uses this bounded metadata crop before
half-size development. This is a geometry fix, independent of the unresolved
Canon base-colour pipeline.

On Android 15 x86-64, the original and red-embedded-JPEG mutant both developed
to 3360 × 2240 with RGB SHA-256
`f602d256af0e499a81c8eee6cc71c97cbc334ae71710190e153b4363adebfc26`.
The earlier 3371 × 2249 / `c3b0375...` result remains evidence for the previous
uncropped decoder, not the current output dimensions or hash.

Two further private CR3 mutants alter only the original two-byte CMT1 TIFF
orientation field at file offset 386: 1→6 and 1→8. Their developed pixels exactly
matched Pillow's clockwise/counterclockwise rotation of the cropped horizontal
development. Fixture hashes and the unchanged-outside-field proof are recorded
in `portrait-fixture-proof.json`; the native test result is
`crop-native-result-20261021.txt`. These tests cover two portrait metadata cases
on one sensor payload, not all Canon models or real-device execution. No RAW
fixture is packaged in the app.

## Reference independence and linear sensor-input comparison

The original EOS R fixture contains three decodable JPEGs: 160 × 120,
1620 × 1080 and 6720 × 4480. A second private mutant replaced all three with
solid red images of the same respective dimensions, preserving each byte range's
length and every byte outside those ranges. Its SHA-256 is
`ad98a635b619d4e8de74614fd3c78a557877205495733c3a078d90160cfd0b6b`;
the ranges and unchanged-outside proof are in `all-preview-fixture-proof.json`.

Fresh, bounded Canon worker children rendered Standard and Neutral from the
original, largest-JPEG mutant and all-JPEG mutant. For each style, all three
1680 × 1120 RGB outputs had identical hashes:

- Standard: `62ea4c006baac8fe8a7a5101e81779ad34999913821e4d52ba2a11af386c255b`.
- Neutral: `085ce1bafdb782735790bd3371a4a40841ea6362822099dcecf979e4a920a7d7`.

This strengthens the reference's sensor-origin evidence beyond replacing only
the largest JPEG. It covers these two settings and this sensor payload, not all
possible DPP modes. These tests did not change the reference worker or app.

The live WB loop's full main input planes were then captured: 1620 × 1080
usable pixels, RGB16 planar, with 1624-pixel row storage. The extra four storage
pixels were excluded from comparisons. LibRaw camera-RGB development was
configured with linear gamma, unity WB, RGB16 output, fixed nominal saturation
and disabled automatic maximum adjustment. The vendor inset was respected;
float planes were bilinearly resized to the observed Canon dimensions.

Two explicit scale hypotheses were compared without fitting image coefficients:
`RGB16 * (white-black)/65535` and `RGB16 * white/65535`.
The latter tracks the observed Canon nominal-range normalization more closely:

| EOS R scene | Subtracted-capacity MAE | Nominal-white MAE | Nominal MAE normalized to 0–255 |
| --- | ---: | ---: | ---: |
| Original | 24.609 | 18.419 | 0.287 |
| Scene 2 | 38.595 | 18.586 | 0.289 |
| Scene 3 | 161.809 | 35.033 | 0.545 |

Errors in the first two numeric columns are linear 14-bit code values, not
perceptual or final sRGB errors. In the third scene the recorded black level is
2047, versus 510/511 in the others. This helps distinguish the two scale rules.
The comparison is still not exact: edge/resampling/demosaic errors include much
larger individual differences, and only one camera model is represented.

Applying only the observed WB arithmetic and per-channel recipe curve to the
captured Canon linear input was also tested. It still differed from the native
pre-profile pixels by about 9.6–10.2/255 mean absolute error across the six
styles. That shortcut was rejected: the recipe's remaining colour transforms
cannot be omitted. No per-image fitted correction was installed in the app.

Private evidence: `canon-sensor-proof-20261021`, `sensor-before-wb*-20261021`,
`sensor-linear-normalization-20261021.json`, `sensor-wb-tone-only-20261021.json`
and the assert-based `verify_sensor_input.py` / `sensor-input-proof-20261021.json`.

## Remaining recipe transfer tables

Two additional live recipe buffers were captured using their declared lengths,
not an assumed prefix size. For each of the six styles:

- Parameter `0x138`: 524,288 bytes / 131,072 signed 32-bit entries.
- Parameter `0x140`: 262,144 bytes / 65,536 signed 32-bit entries.

The active numerical path uses the first as a direct transfer lookup, with a
separate negative-value branch. Another active path sign-extends a 16-bit value,
adds 32,768, bounds the resulting index and reads the second table. The broader
colour meaning of that signed quantity is not established; assigning it a hue,
chroma or noise-reduction label would be premature.

Twelve live lookup values and their table prefixes exactly matched the captured
buffers when replayed independently. This verifies these sampled reads, not the
entire signed transfer path, all lookup indices or the complete recipe formula.
An assert-based replay also checked all 12 declared buffer lengths against their
saved payloads. Evidence: `raw-recipe-aux-lookups-20261021`,
`raw-recipe-aux-tables-20261021`, `verify_aux_tables.py` and
`aux-table-proof-20261021.json`.

All decoded fields of the six bundled basic PF3s were compared. Only `0x1002`
(name) and `0x1009` (base selector) differ. The other 24 payloads are identical,
including the 512-byte `0x1061`/`0x1062` fields and both 215,628-byte identity
table fields. Therefore those files do not contain six different complete base
rendering pipelines hidden outside `0x1071`. This rules out another shortcut;
the live recipe transforms still need reconstruction. The captures remain
private research data and are not packaged as app resources.

## Pixel data flow and exact profile lattice

A bounded Stalker trace recorded 888 scalar-body instruction snapshots, including
registers and memory operands, for one main-request pixel. Standard and Neutral
full-render hashes were checked against uninstrumented children and remained
identical. The trace is a concrete path, not a complete implementation for other
pixel values or settings. A one-shot CPU data watchpoint then showed the pixel
being changed again before `UCSMatchPixmap`, by the function at RVA `0x157550`
called through `0x159f10`. This additional stage explains the discrepancy
between the recipe's immediate output and the colour-profile input.

Captures are now gated by the public render request dimensions to exclude the
480 × 320 warm-up. Repeating the six recipe curves and 12 auxiliary buffers
under the 1680 × 1120 request reproduced all 18 earlier payloads exactly. Thus
the warm-up sampling ambiguity was real in the probe selection but did not
change those table values in the tested settings. Private evidence:
`raw-scalar-main-values-20261021`, `raw-scalar-render-proof-20261021`,
`raw-scalar-write-watch-20261021` and `raw-main-tables-20261021`.

The additional stage is fixed-point tetrahedral interpolation over nine active
nodes per axis, stored as three padded 10³ planes of signed 32-bit values
(12,000 bytes). For unsigned RGB16 input, it discards seven low input bits,
uses six fractional bits for tetrahedral weights totaling 64, multiplies the
weighted sums by four with signed 32-bit wrap, then clips each channel to
0–65535. This reuses the already reconstructed compiler interpolation kernel;
`camera_install.integer_tetrahedral_reference.profile_rgb16` supplies the
profile-specific input shift, channel-order restoration, final shift and bounds.
The legacy compiler helper's input/output contract remains unchanged.

The adapter was checked against 516 native outputs across the six style
selections, including cube corners, cell boundaries, all six fraction orders and
deterministic random points: every output matched exactly. A further 344 native
cases used entirely synthetic identity, modular, signed and overflow tables;
all matched, including signed overflow and clipping. The synthetic pixel buffers
are private allocations, never substitutions in the photographic reference.
Selected native synthetic vectors are now regression tests without Canon data
or a Canon runtime dependency. The relevant reference/compiler/mobile suites
passed 49 tests.

All six style selections used the same captured lattice in this fixture and
profile setup, SHA-256
`dcfd684e571ccc007df27956e654a09dc89992493255fecb6d027400852dfeec`.
This does not establish equality for other cameras, profiles, WB or exposure.
For Standard and Neutral, a blockwise integer NumPy replay also reproduced every
usable image pixel: 1,749,600 pixels each, zero mismatches and zero maximum error.
The replayed output was exactly the previously captured colour-profile input.
Both full photographic render hashes remained unchanged by instrumentation.

Private evidence: `profile-lattice9-20261021`,
`profile-lattice-synthetic-20261021` and `profile-lattice-image-20261021`, each
with capture/replay scripts and proof JSON. No captured lattice or ICC resource
was added to the application. The full preceding recipe and final colour-matching
stage still need reconstruction; the offline reference adapter is not an Android
render backend and does not enable a verified Canon-look claim.

## Integer recipe colour and tone primitives

Three more observed operations now have independent references in
`camera_install.raw_recipe_reference`. They are not a replacement renderer.

For ordered RGB16 input, the measured chroma conversion is:

```text
Cb = trunc((2048*B - 1356*G - 691*R) / 4096)
Cr = trunc((2048*R - 333*B - 1714*G) / 4096)
```

The final luma/chroma-to-RGB branch truncates the following expressions and
clips each result to 0–65535:

```text
R = trunc((4096*Y + 5742*Cr - 2*Cb + 2048) / 4096)
G = trunc((4098*Y - 2925*Cr - 1412*Cb + 2048) / 4096)
B = trunc((4095*Y + 7254*Cb + 2048) / 4096)
```

Truncation is toward zero, including negative numerators. These are the observed
integer coefficients, not a claim that an arbitrary standard colour-space
conversion is interchangeable. The helper takes luma as a separate input; its
generation and intervening recipe adjustments are not assumed here. Input
bounds keep all these expressions within their observed signed 32-bit domain.

The measured tone branch linearly interpolates a 2,048-entry unsigned 10-bit
curve at step 64. The weighted result retains six fractional bits rather than
being divided by 64. The upper neighbour is bounded to entry 2047, so coordinates
up to 131071 never require padding. This corrects a possible interpretation of
the earlier curve capture as a direct nearest-index lookup.

An isolated child exercised the actual scalar instructions with private
synthetic register values. Aligned checkpoints checked 78 RGB-to-chroma vectors,
100 final RGB vectors and 83 tone coordinates, including negative chroma, full
unsigned endpoints, fractional curve positions and the final curve cell. All
261 outputs exactly matched the shared Python helpers. The first, unaligned
chroma checkpoint was discarded because it preceded the final signed shift;
only `raw-recipe-primitives-aligned-20261021` is used as evidence.

These synthetic runs intentionally alter the child's rendered pixel values;
their output images are not photographic references. The source RAW's SHA-256
remained unchanged. Replay uses the stored observations without loading Canon
code. Synthetic/observed regression vectors and validation tests passed alongside
the existing interpolation/compiler tests (29 tests), plus both source-package
and standalone-module checks. Private evidence: `verify_raw_primitives.py` and
`raw-recipe-primitives-aligned-20261021/shared-helper-proof.json`.

The profile lattice, these colour primitives and curve sampling still need to
be joined with the remaining coefficient-dependent and auxiliary-table stages.
No partial conversion has been applied to the already developed Android image,
and the independent Canon-base-render verification flag remains false.

## Positive channel gain, 25 October

A bounded isolated native probe checked 69 synthetic channel-gain vectors at
the scalar percentage/Q10 stage, including truncation boundaries, zero gain,
clipping and doubled RGB16 inputs through 131070. The independently replayed
expression is `min(maximum, (value * percent // 100) * coefficient // 1024)`.
All 69 outputs matched exactly. The reference helper limits percentage to 0–200,
coefficient to 0–8192 and cap to 0–65535; signed or overflowing domains are not
claimed. Regression tests cover intermediate truncation and invalid inputs.

The owned child restored the temporary coefficient fields after each measured
channel. Its synthetic output is not a photographic reference. The original RAW
hash remained unchanged, and no camera was accessed. Private evidence is in
`raw-channel-gain-20261025/trace.json` and `shared-helper-proof.json`.
This reconstructs one coefficient-dependent arithmetic stage; coefficient
generation, the remaining auxiliary stages and full Canon rendering are still
unverified. No correction was added to the Android preview from this result.

## Default auxiliary luminosity index, 25 October

The default scalar branch computes a bounded auxiliary-table index as
`min(1023, (2*R + G + B) // 128)` from the observed ordered channel registers.
This is a particular native lookup coordinate, not a claim that standard RGB
luminance has these weights. Two native mode checks can choose a different
branch; that alternate branch has not been reconstructed here.

An isolated owned child checked 81 vectors: channel corners, small integer
boundaries, neutral levels and deterministic random RGB16 values. Every native
index matched the independent helper, including the final 1023 cap. The source
RAW hash remained unchanged; synthetic output was discarded. Evidence is in
`raw-luma-bin-20261025/trace.json` and `shared-helper-proof.json`. Regression tests
cover the asymmetric channel order, truncation, saturation and invalid values.
The link from auxiliary lookup results to the later tone coordinate, and full
independent RAW development, remain unverified; production rendering is unchanged.

## Coefficient-weighted minimum index, 25 October

The alternate scalar branch computes each ordered channel times its Q10 gain,
truncates each result, takes the minimum, divides by 32 and caps at 1023:
`min(1023, min(channel * gain // 1024) // 32)`. Its gains are explicit inputs to
the reference helper; their camera/profile-dependent generation is not inferred.

An isolated native probe forced this branch for 82 bounded synthetic vectors,
covering zero and unequal gains, small boundaries, saturation and deterministic
random channels/gains. All outputs matched the independent helper. Original RAW
hash verification passed, synthetic output was discarded and no camera session
was opened. Evidence is in `raw-luma-minimum-20261025/trace.json` and
`shared-helper-proof.json`. Positive Q10 gains are bounded to 8192 in the helper;
signed/overflow domains and full rendering remain outside this evidence.


## Combined auxiliary indices, 25 October

The scalar lookup setup now has a combined reference: luma bin; magnitude of
trunc((G-B)/32), capped at 1023; positive part of trunc((G-R)/32), capped at 1023;
and the sign selecting the G-B auxiliary table. The sign is taken after integer
truncation: differences -1 through -31 select the nonnegative table, unlike -32.
An isolated native run checked all four results for 81 channel vectors with zero
mismatches. The unchanged RAW hash was verified. Evidence is in
`raw-aux-indexes-20261025/trace.json` and `shared-helper-proof.json`.
Regression tests cover sign boundaries and clipped indices. This does not yet
reconstruct auxiliary table contents or their use in the final tone coordinate;
the production Android renderer remains unchanged.


## Auxiliary lookup ordering and minimum, 25 October

Following the observed execution corrects an earlier working assumption: these
auxiliary tables are consumed after tone sampling, in the chroma-adjustment
stage. Their indices are prepared earlier, but they do not directly create the
preceding tone coordinate. The scalar code reads three unsigned 16-bit values
using the reconstructed indices and selects their minimum. For the nonnegative
G-B selector, the eventual lookup substitutes the separate positive-table
pointer; preserving that pointer substitution matters when joining the stages.

An isolated owned child substituted only private synthetic table allocations
and checked 71 triples, including ties, all orderings, unsigned 16-bit limits and
deterministic random values. Native selection equalled Python `min` in every
case. The source RAW hash remained unchanged. Evidence is in
`raw-aux-minimum-20261025/trace.json` and `shared-helper-proof.json`.
No wrapper around `min` or production correction was added. The next missing
operation is the sign-dependent chroma gain consuming this minimum; table
construction and full rendering remain unverified.


## Sign-dependent chroma gain, 25 October

The default post-tone chroma branch first truncates `chroma * amount / 1024`,
then multiplies by a sign-selected coefficient and truncates again by 128.
Each of the two chroma channels has separate positive and nonpositive gains.
The sign is tested on the original chroma value, and this stage precedes later
clipping. Combining the two divisions into one changes rounding and is incorrect.

The independent helper accepts signed RGB16-range chroma, Q10 amounts 0–1024
and Q7 coefficients 0–256. An isolated native child checked 92 vectors including
zero, signed limits, fractional boundaries, unequal gains and deterministic
random inputs: every pair matched. Private synthetic coefficient storage was
used, the original RAW hash remained unchanged, and no camera was accessed.
Evidence is in `raw-chroma-gain-20261025/trace.json` and
`shared-helper-proof.json`. Regression tests cover sign selection, two-stage
rounding and validation. This is the measured default branch only; downstream
clipping, alternate processing modes, table construction and full rendering
remain unverified. Production preview output is unchanged.


## Post-gain channel mix, 25 October

The following scalar stage caps each gained chroma only from above, forms a
Q10-weighted base from three ordered pre-tone channels, and produces
`base+first`, `base+second`, and
`trunc((8192*base - 1536*first - 4096*second)/8192)`.
Negative chroma remains negative here; symmetric clipping would be incorrect.
The outputs precede optional exposure scaling and later clipping/lookup stages.

The independent helper restricts positive Q10 weights to a sum of at most 1024,
unsigned channel inputs to RGB16, post-gain chroma to -65536–65535 and upper cap
to RGB16. These bounds keep the observed integer intermediates overflow-free.
An isolated native probe checked 77 vectors covering channel-only weights,
zero weights, unequal weights, signed chroma, upper clipping and deterministic
random inputs. Every output matched. The source RAW hash remained unchanged;
synthetic output was discarded and no camera was accessed. Private evidence:
`raw-chroma-mix-20261025/trace.json` and `shared-helper-proof.json`.
Regression tests cover truncation and upper-only limits. Full rendering and
coefficient generation remain unverified; no app preview change was made.


## Continuous post-tone chroma block, 25 October

A further native probe measured the entire instruction span from sign-dependent
chroma gain through the following channel mix, with no intermediate synthetic
replacement. It supplied 512 deterministic tuples of channel inputs, signed
chroma, Q10 amounts, separate sign gains and upper limits. Composing the two
independent helpers reproduced every native output, with zero mismatches.
This validates their connection rather than only isolated arithmetic. Selected
vectors are regression tests; all captures remain private. The source RAW hash
was unchanged and no camera was accessed. Evidence:
`raw-chroma-block-20261025/trace.json` and `shared-helper-proof.json`.
Optional subsequent exposure scaling, clipping, later lookups, auxiliary table
construction and the complete Canon render remain unverified. No production
preview or distributable was changed by this offline validation.


## Photographic post-tone block samples, 25 October

The same gain-plus-mix block was then observed without substituting any native
register, pointer, coefficient or pixel. All 2,048 sampled executions matched the
composed independent helpers exactly; there were 1,984 distinct input tuples.
Observed real coefficients included Q10 channel weights [450,464,110], sign
gains [163,162,167,164], auxiliary amount 1016 and upper limit 41024. These are
measurements for this fixture/settings, not portable constants.

An uninstrumented render from a separate owned process matched the observed
render's full RGB pixel hash, mode and dimensions exactly. The RAW source hash
also remained unchanged. Evidence is in `raw-chroma-observed-20261025`, including
both render-proof JSON files and `shared-helper-proof.json`. This establishes
sampled photographic-block parity and absence of observation-induced pixel
changes, not every pixel or the complete independent Canon renderer. No camera
was accessed and no application preview correction was added.


## Continuous block through exposure and signed clipping, 25 October

The photographic block replay now extends through the optional Q14 factor and
following signed channel bounds. All 2,048 observed tuples matched exactly.
The fixture used mode 1, factor 16384 and bounds -131071–131071; these are observed
settings, not universal camera constants. A separate synthetic native run tested
79 tuples with factors 4096, 8192, 16384, 32768 and 65536 and two bound pairs.
Every output matched truncation toward zero by 16384 followed by clipping.
The independent helper requires explicit factor and bounds.

Evidence is in `raw-chroma-clipped-20261025` and
`raw-mix-exposure-20261025`, each with `trace.json` and `shared-helper-proof.json`.
Both RAW source hashes remained unchanged; no camera was accessed. Regression
checks cover signed fractional rounding and clipping. This extends sampled
continuous-block parity; later lookup operations, table/coefficient construction
and the full renderer remain unverified. No production preview changed.


## Post-mix signed curve lookup, 25 October

The next observed channel branch supports a full 131073-entry table, a coarse
4097-entry table indexed by `(coordinate+1)//32` with output multiplied by 32,
or a linear fallback `2*coordinate`. A full table takes precedence. Nonnegative
input is capped by an explicit positive limit. Negative input instead reflects
lookup(abs(input)) about lookup(0): `2*lookup(0)-lookup(abs(input))`, without using
that positive cap. A nonzero table origin therefore matters.

An isolated native child tested 49 combinations across all three paths, signed
limits, coarse boundaries and positive caps. Every output matched the independent
helper. Synthetic full values were bounded to uint16 and coarse values to 12 bits;
these are the helper's verified table bounds, not a claim about every native
profile. Source RAW hashing passed and no camera was accessed. Evidence is in
`raw-signed-lookup-20261025/trace.json` and `shared-helper-proof.json`.
Regression tests cover reflection, nonzero origin, positive-only capping, coarse
rounding, priority and invalid inputs. Table generation and whole-render parity
remain unverified; production previews were not changed.


## Photographic block through all three signed lookups, 25 October

Observation was extended from the chroma gain entry through the common exit of
the three post-mix lookups. All 2,048 photographic samples matched the independent
composition of gain, channel mix, Q14 exposure, signed clipping and signed lookup.
The observed mode pair was (1,0), positive lookup cap 41024. The private full table
contained 131073 signed storage entries with actual values 0–39745, within the
reference helper's verified uint16 bounds. Its contents are not bundled or treated
as portable coefficients. Lookup arithmetic was cross-checked against the shared
helper on selected samples; the larger replay validates the full table once.

Evidence is in `raw-chroma-looked-up-20261025`, including the table capture,
`trace.json` and `shared-helper-proof.json`. The source RAW hash remained unchanged;
no native pixels or registers were substituted and no camera was accessed. This
validates a longer sampled block in the observed mode, not the subsequent colour
conversion, table generation, alternate modes or the full independent renderer.
Production rendering remains unchanged.


## Second chroma conversion after lookup, 25 October

A separate post-lookup matrix uses coefficients (2048,-1360,-688) for the first
component and (2048,-1712,-336) for the second, with truncation toward zero by
4096. These differ from the pre-tone matrix and must not be merged. One explicit
mode additionally multiplies the first truncated component by 9/8, truncating
again. Both components are then clipped to signed 16-bit bounds.

An isolated native probe checked 144 tuples across both modes, RGB corners and
deterministic signed lookup outputs: every pair matched. The reference helper
bounds each input to +/-262144, keeping its integer products overflow-free.
Selected native vectors are regression cases, including neutral white producing
zero in this matrix. Source hashing passed and no camera was accessed. Evidence:
`raw-second-chroma-20261025/trace.json` and `shared-helper-proof.json`.
Subsequent component corrections and final integration remain unverified; no
production rendering change was made.


## Dominant-chroma lookup and common gain, 25 October

The next signed-mode block selects the chroma component with greater absolute
magnitude, choosing the first on ties. The lookup index is that magnitude capped
at 32767, including abs(-32768). The selected signed component is retained for a
later correction. A uint16 table read at that index supplies a common Q7 gain
for both components, truncating each signed product toward zero by 128.

An isolated native run checked 100 index/dominant selections; another checked
100 complete selection-plus-gain outputs with a private synthetic table. All
matched. Selection uses ordinary `max(pair,key=abs)` (first tie wins), and the
gain reuses the existing independent gain helper with identity Q10 amount.
No redundant wrapper was introduced. The source RAW hashes remained unchanged;
no camera was accessed. Evidence: `raw-dominant-chroma-20261025` and
`raw-dominant-gain-20261025`, each with `trace.json` and
`shared-helper-proof.json`. Actual table construction, subsequent signed
corrections and whole-render parity remain unverified; production is unchanged.


## User RP scenes and portrait dispatch limitation, 25 October

The longer continuous block through common gain matched another 2,048 observed
executions from the EOS R fixture. On the user's RP landscape files IMG_2433.CR3
and IMG_2440.CR3, 2,048 executions per file also matched exactly, with respectively
2,045 and 2,036 distinct input tuples. Each file used its own privately observed
tables and coefficients; no EOS R constants were substituted. All RAW hashes
remained unchanged. Evidence: `raw-chroma-common-gain-20261025`,
`raw-chroma-rp-2433-20261025` and `raw-chroma-rp-2440-20261025`.
The dominant gain table was constant 128 for the initial fixture, so nonneutral
gain remains covered by the separate synthetic tests, not that photograph.

IMG_2408.CR3 (portrait) reached the colour-matching stage but none of the seven
observed scalar checkpoints. The same checkpoints were hit on both landscape
files. Consequently, no block-parity claim is made for that portrait. A different
size/orientation-dependent processing route (potentially vectorized) must be
traced; attributing the difference solely to camera model would be unsupported.
Evidence: `raw-rp-path-20261025`, `raw-rp-path-2433-20261025` and
`raw-rp-path-2440-20261025`. The failed initial portrait replay is an absent-route
result, not zero-error validation. No app build or camera session was performed.


## Scalar tail versus vector processing, 25 October

The portrait discrepancy is now explained by loop dispatch, rather than camera
model. The vector loop advances its column counter by eight. For IMG_2408,
the scalar gate observes width 1120 and start 1120: no scalar pixels remain.
For IMG_2433 it observes width 1620 and start 1616: four scalar pixels remain
per row. The scalar hooks cover those tail pixels, not the main vector block.
Thus earlier 2,048 photographic sample matches validate the scalar tail across
rows; they must not be described as vector/main-frame arithmetic validation.

All three captured row gates matched these widths/start positions, and scalar
entry was observed only for the landscape case. Both source hashes remained
unchanged. Evidence: `raw-rp-loop-2408-20261025` and
`raw-rp-loop-2433-20261025`, including `dispatch-proof.json`.
The next task is vector-path equivalence or an independently checked scalar
oracle for that path. Portrait rendering is not blocked on physical equipment;
its native processing route still needs software investigation.


## Native scalar-only versus vector loop on portrait, 25 October

An owned experimental child redirected each main recipe row at the existing
vector/scalar gate to the scalar loop, starting at column zero. This is a private
native-path comparison, not an independent-rendering implementation. A separate
unmodified child rendered the same IMG_2408 input/settings. Both produced RGB
1680x1120 output, but hashes differed. Across 5,644,800 channels, absolute error
was 0.1364622307 on the 0–255 scale, maximum 3, 99th percentile 1, with 730,327
changed channels. The paths are therefore close but not bit-identical; rounding
or other path differences still need localization. No exact equivalence claim
is made and the modified output is not a Canon photographic reference.

The observed row width was 1120 and the original scalar start 1120; the private
redirect set the scalar start to zero and bypassed the vector body. The RAW hash
remained unchanged and no camera was accessed. Evidence:
`raw-force-scalar-rp-2408-20261025`, including both pixel buffers, render-proof
JSON files and `comparison-proof.json`. No native binary was patched on disk and
no production application code was changed.


## Localizing native scalar/vector differences, 25 October

Paired RGB16 captures place the scalar-only versus default-vector difference
before both the profile lattice and colour matching. For IMG_2408, the usable
1120x1080 area before the lattice had mean absolute difference 24.136738/65535,
maximum 193, p99 67. After the lattice the mean was 26.804674, maximum 308,
p99 156. The latter exactly matched the captured colour-matching input metrics.
After colour matching, RGB16 difference was mean 31.765152, maximum 514, p99 257;
these are RGB16 values and must not be reported on a 0–255 scale.

Padding was excluded from lattice comparisons using captured width and stride.
All paired source hashes remained unchanged. Evidence:
`raw-path-colour-{vector,scalar}-20261025` and
`raw-path-lattice-{vector,scalar}-20261025`; comparison-proof JSON files are in
the scalar folders. The error is therefore already present in the native recipe
output, rather than arising solely from final display or colour matching.
Rounding differences are a hypothesis, not yet a proven cause. The next useful
checkpoint is inside the vector recipe arithmetic. No camera or production
application was changed by this analysis.


## First vector gain checkpoint, 25 October

The initial vector gain was observed directly from its native spill buffer on
IMG_2408: 256 blocks, four blue-channel lanes each, all 1,024 values matched the
scalar expression `min(cap, 2*input*numerator//denominator)`. The observed ratio
was 512/512 and both optional preprocessing flags were zero. This excludes that
specific blue-channel operation in this configuration as the measured discrepancy's
origin; it does not validate arbitrary ratios, optional paths, other channels or
the complete vector loop. No floating-register substitution was performed.

Source hashing passed and no camera was accessed. Evidence is in
`raw-vector-initial-gain-20261025/trace.json` and `shared-helper-proof.json`.
The first differing downstream vector operation remains to be located. Production
rendering and the APK are unchanged.


## Vector percentage/Q10 gains across all channels, 25 October

The checkpoint now covers all eight lanes in all three channels for 256 vector
blocks (6,144 values) on IMG_2408. Initial gain, common percentage, Q10 gain and
individual channel caps all matched the independent scalar arithmetic exactly.
Observed settings were ratio 512/512, percentage 100 and coefficient 1024; this
is not arbitrary-gain vector validation. A preliminary blue-only checkpoint also
matched all 2,048 values. No native values were substituted.

The differing full-frame output therefore first diverges after this checkpoint
in the observed default configuration. Luma/chroma index generation and later
vector arithmetic are the next comparisons. Source hashing passed and no camera
was accessed. Evidence: `raw-vector-q10-gain-20261025` and
`raw-vector-q10-rgb-20261025`; the latter includes `shared-helper-proof.json`.
No production preview or APK change was made.


## Located vector/scalar auxiliary-index divergence, 25 October

Direct vector spill observations identified an actual arithmetic difference:
negative G-B differences use arithmetic shift by five (floor division by 32)
in the vector path, whereas the scalar path truncates toward zero. The vector
also chooses its table from the unshifted difference sign. For -1 through -31,
scalar chooses index zero/nonnegative table; vector chooses index one/negative
table. For other nonmultiples of 32, vector magnitude can be one greater.

Across 256 native blocks (2,048 pixels), all luma, magnitude, positive-difference
and table-sign outputs matched the vector-aware independent reference. The scalar
reference differed on 720 pixels. Thus at least one real source of path-dependent
output is established, not merely hypothesized. Other downstream differences can
still remain; this is not whole-vector equivalence or proof that this one change
explains the full-frame error. The observed mode was the default luma branch.

`auxiliary_indices(..., vectorized=True)` now expresses this measured distinction;
its default preserves the verified scalar contract. Boundary regression tests
cover -31/-33 and mode validation. Source hashing passed and no camera was
accessed. Evidence: `raw-vector-aux-indices-20261025/trace.json` and
`shared-helper-proof.json`. This reference change is not wired into production
rendering; the APK is unchanged.


## Counterfactual auxiliary-index rounding test, 25 October

A private scalar-only child was modified to use vector-style floor division for
the auxiliary channel differences across the full IMG_2408 recipe frame. A
retained native CModule callback counted 1,209,600 executions and 658,378 actually
changed index calculations. Nevertheless, the final RGB buffer was byte-identical
to the unmodified scalar-only result. Therefore this measured index discrepancy
does NOT explain the observed scalar/vector image error under these settings.
It can still matter for other table/settings combinations, but such an image
effect has not been established. No claim is made that all internal values stayed
identical: the measured equality is the final RGB buffer.

Evidence: `raw-force-scalar-vector-indices-20261025`, including counters in
`trace.json` and `counterfactual-proof.json`. The private callback module was kept
alive for the entire run; an initial run without this lifetime guarantee failed
and was discarded. The RAW hash remained unchanged; no disk binary or production
application was patched and no camera was accessed. Investigation must continue
at later vector arithmetic rather than attributing the raster error to these
indices alone.


### Vector first chroma matrix, 25 October 2026

The owned EOS RP IMG_2408 probe captured 256 eight-pixel blocks at the actual
vector matrix spills and after its Q12 shifts: 4,096 chroma outputs. Both
coefficient sets match the scalar reference, but arithmetic right shift rounds
negative numerators down rather than toward zero. The floor reference matches
all 4,096 outputs; truncation differs on 2177 outputs.
Inputs are RGB at paired spills 0x80/0x150, 0x160/0x170 and
0x130/0x240; outputs are Cr at 0xc80/0xc90 and Cb at 0xca0/0xcb0.
Private evidence: raw-vector-first-chroma-20261025/comparison-proof.json and
trace.json, with successful render and unchanged source hash. This is a
checkpoint result, not evidence that this rounding explains the final raster
difference. No production renderer, shipped build or camera state changed.


The full-frame counterfactual changed only the two scalar Q12 rounding biases,
while forcing scalar processing for every main-image pixel. The callback ran
2,419,200 times and removed 1,275,332 nonzero rounding biases. Final RGB8 changed
on 176,474 channels versus the original scalar frame. Against the unmodified
vector frame, mean absolute error only decreased from 0.13646223072562358 to
0.1363499149659864 /255 (maximum 3, p99 1). This proves a raster effect, but
not the main cause of the remaining scalar/vector discrepancy. Source CR3
hash remained unchanged. Private evidence: raw-force-scalar-vector-chroma-20261025.
The offline chroma reference now exposes the observed vector rounding mode;
its default scalar behavior is preserved. All 2,048 captured pixels match the
shared helper, and 17 reference tests pass. No production render path changed.


### Pre-tone RGB conversion rounding counterfactual

A second owned-process experiment also removed the scalar signed-division
biases at 0x1f3cd6, 0x1f3d03 and 0x1f3d26, immediately after the first chroma
matrix. Across the full RP portrait this added 3,628,800 callback invocations
but no additional nonzero bias removals: total calls 6,048,000, changed biases
still 1,275,332. Its final raster is byte-for-byte identical to the chroma-only
counterfactual. Thus these three additional rounding sites cannot explain
the remaining discrepancy in this scene and configuration. This does not
establish equivalence for negative pre-tone channels in other scenes.
The source hash was rechecked against IMG_2408.CR3. Evidence:
raw-force-scalar-vector-premix-20261025/counterfactual-proof.json.


### Vector pre-tone chroma round trip checkpoint

A fresh owned-process capture sampled native luminance directly from rax+r9*2
at 0x1ebe4e, the RGB matrix spills, and all six post-round-trip vectors at
0x1ece48 (RGB paired spills e00/e10, de0/df0, dc0/dd0). Reconstructed Q12
chroma and RGB equations match all 6,144 values across 2,048 pixels.
The new offline pre_tone_rgb16 helper reproduces the same capture exactly;
18 reference tests pass. Luminance is still supplied by the native pipeline,
so this does not reconstruct its origin or establish an independent renderer.
Evidence: raw-vector-premix-20261025/trace.json, comparison-proof.json and
shared-helper-proof.json, with successful render and unchanged source proof.
Production rendering and installed candidates remain unchanged.


### Independent pre-tone luminance, three RAW captures

The luminance plane used above matches `(306*R + 601*G + 117*B)//1024`
exactly on 2,048 captured pixels each from RP IMG_2408, RP IMG_2440 and the
original EOS R fixture. Q10 constants also occur in native RGB-to-luma code
(e.g. 0x250139..0x250156), although those separate routines were not proven
to generate this particular plane. The pre_tone_rgb16 reference now computes
luma from its RGB argument rather than accepting native luma. Its complete
pre-tone round trip matches all 18,432 output channel values in the three
captures. Evidence: independent-premix-proof.json in raw-vector-premix-20261025,
raw-vector-premix-rp2440-20261025 and raw-vector-premix-eosr-20261025.
This removes the native-luma input from this block only; upstream RGB
development, later tone tables and the complete independent renderer remain
unresolved. The 18 reference tests pass, and no installed build changed.


### Continuous vector pre-tone to tone output

The next capture checks the continuous path from RGB input through independent
Q10 luma/chroma round trip, neutral gain/limits and tone interpolation.
At 0x1ed58e the three paired planes 1440/1460/1480 match 6,144 predicted
values in RP IMG_2408 (gain 512/512, limits 131071/131072, optional exposure
plane absent, both pre-tone flags zero). Post-tone paired planes fa0/fc0/fe0
at 0x1ef021 match all 18,432 output values across IMG_2408, IMG_2440 and the
EOS R fixture, reusing sample_tone64 and pre_tone_rgb16. The tone table is
2048 uint32 entries, captured privately through rbp-0x30. It remains native
reference data, not reconstructed portable constants. No table was added to
the app. Evidence: raw-vector-tone-input-20261025 and
raw-vector-tone-output[-rp2440|-eosr]-20261025/comparison-proof.json.
This confirms continuity for the observed neutral branches, not arbitrary
exposure/optional corrections or a complete independent RAW renderer.


### Tone-buffer allocation and copy provenance

To locate the generator rather than fit captured values, bounded owned-process
probes followed the actual tone allocation. A general JavaScript heap hook and
two enlarged heap-context experiments exceeded the 40-second deadline and
were terminated by their own cleanup. No evidence from those timed-out runs
is treated as a completed render. A compact native heap filter completed,
then a focused DppCore calloc return hook at 0x754b completed without global
heap overhead. The 8,196-byte allocation containing the 8,192-byte curve
comes through 0x3a420 / 0x3a4d3 and the object-copy path 0x60590.

A subsequent focused 0x60590 probe recorded 14 8,192-byte curve copies via
callers 0x6076e and 0x60787. Every source/destination pair has the same SHA-256
when the copy returns. The actual tone pointer at 0x1ed58e is among those
destinations; chronological sequence numbers are preserved because addresses
are reused. This locates a copying stage, not the original table generator.
The next investigation must follow the source object before that stage.
Evidence: raw-tone-dpp-allocation-20261025/allocation-proof.json and
raw-tone-copy-provenance-20261025/provenance-proof.json. Completed probes
record successful rendering and unchanged source hashes. No captured table
or installed Canon code was added to any distributable.


### Actual tone generator located

Following buffer construction removed the copy-path ambiguity. The two original
8,192-byte buffers are constructed by 0x39ea0 through factory 0x69d10, called
from 0x62a46 and 0x62a73 inside 0x61de0..0x64974. The first feeds tone; the
second has an identity prefix. The original first buffer is the source of the
subsequent copy chain (verified in raw-tone-buffer-constructor-20261025).

The observed branch fills that first buffer by calling 0xdc120 from 0x62bd1
(return 0x62bd6). A focused enter/leave probe captured the output pointer,
2,048-entry count, 112 parameter bytes and the complete generated uint32 table.
Its SHA-256 is a974f1a85e582ed3b79a9e6b81653a6104579b64fab8b85fb13d7b21002f5979,
exactly the table consumed by the RP IMG_2408 vector renderer. Thus 0xdc120
is a verified generator for this branch, unlike the previously excluded
0x59f30 or generic copy routines. Function bounds are 0xdc120..0xde6cc.
The alternate call at 0x62ad6 to 0xd6a30 was not exercised by this probe.

Evidence: raw-tone-buffer-factory-20261025/factory-proof.json and
raw-tone-generator-20261025/generator-proof.json plus 129_generated-tone_0.u16.
The original CR3 hash remains unchanged and rendering completed. Captured
stack arguments are raw words (upper bits of narrow arguments are not typed
values); their meaning remains unverified. The mathematical generator still
needs reconstruction. No native table or implementation was bundled.


### Tone-generator cubic spline evaluator

The confirmed generator invokes 0xdf420, a cubic-spline evaluator with
one-based native knot/value/second-derivative arrays and endpoint-interval
extrapolation. An owned-process NativeFunction probe evaluated 11 synthetic
queries from -0.2 to 1.2 over five supplied knots, including exact knots, both
endpoints, mixed second derivatives and extrapolation. The independent
sample_cubic_spline helper matches within 1e-14 (maximum error 0.0).
It uses ordinary zero-based arrays, validates finite values and increasing
knots, and adds no dependency. The actual RP generator hit return site
0xdcfca with 10 knots: 0,150,300,600,1200,2400,4800,9600,13200,16383.
This establishes the evaluator and its use, not the knot-value generation
or second-derivative solver. Native tables/knots are private evidence only.
Private evidence: raw-tone-spline-kernel-20261025/spline-proof.json and
shared-helper-proof.json. The 19 offline reference tests pass; no production
renderer or installed candidate changed.


### Independent spline second-derivative solver

The generator calls 0xdede0 to solve the tridiagonal cubic-spline system.
The observed endpoint convention is natural for a slope sentinel greater
than 9.9e29; otherwise the endpoint derivative is clamped to the supplied
slope. A NativeFunction experiment checked 12 combinations: 2, 5 and 10
nonuniform knots, each with natural/natural, zero/zero, 0.5/2 and
natural/-0.25 endpoints. The independent spline_second_derivatives helper
reproduces every derivative exactly in these cases.

A focused actual-generator capture also recorded solves returning to 0xdcecc
(10 knots) and 0xde108 (226 knots). Branch hooks confirmed both endpoints
natural in both calls. All actual second derivatives match the independent
solver exactly. Total verified: 304 derivatives over 12 synthetic cases and
two live solves; maximum absolute error 0.0. Native one-based buffers are
translated to ordinary zero-based Python arrays, without native data in tests.
None is accepted for natural endpoints; finite inputs, matching lengths and
strictly increasing knots are validated. The first quadratic unit check was
changed from exact integer equality to floating tolerance after ordinary
roundoff produced 2 +/- 4e-16; native-reference comparisons remain exact.

Evidence: raw-tone-spline-solver-20261025/solver-proof.json and
shared-helper-proof.json; 20 reference tests pass. This reconstructs the
solver, not the generator stages that select/transform the knot values.
No shipped renderer or installed build changed.


### Complete final-table resampling from intermediate knots

The 226-knot natural spline captured at 0xde108 reproduces every table entry
before final adjustment using sample(i*64)/64, add 0.5, truncate and clamp
to 0..1023. The four remaining differences in RP IMG_2408 are introduced
by 0xd8020, not the main spline: entries 24,63,129,153 each decrease by one.
That adjustment builds a secondary 1,024-entry spline lookup via 0xd85d0,
then maps entries 1..643 through it in this fixture. Its seven neutral control
pairs are identity points, but floating interpolation plus truncation still
changes certain integer codes. An identity shortcut would therefore be wrong.

The independent build_spline_lookup implements natural spline evaluation,
truncation/clamping and nondecreasing output. It matches all 1,024 native
lookup entries. Combining that lookup with the reconstructed main spline
resampling matches all 2,048 final tone entries. Fresh RP IMG_2440 and EOS R
probes also match both complete tables exactly (6,144 final entries and
3,072 adjustment entries across three RAWs). Evidence:
raw-tone-final-resampling[-rp2440|-eosr]-20261025/independent-final-table-proof.json.

The intermediate knots/values and adjustment controls are still native
reference inputs; this does not reconstruct the upstream mapping that creates
them. No captured arrays were bundled. The 21 reference tests pass, including
quantization/monotonicity and identity-roundoff regression checks. Installed
Windows/Android candidates remain unchanged.


### Source-knot expansion and initial normalization

The first generator spline expands each original interval using
`subdivisions = 251 // source_count`, preserving original points and
evaluating inserted points at `left + j*width/subdivisions`; inserted values
are capped by the last source ordinate. With 10 source knots this yields
226 points. The new independent densify_spline helper matches all 452
positions/ordinates exactly at 0xdd078. Tests cover control preservation,
strictly increasing positions and the knot budget (22 tests pass).

The following normalization at 0xdd3e4 also matches all 452 values exactly:
`(upper-lower)*value/4095 + lower*16383/4095`, independently for each axis.
The observed ranges in RP IMG_2408 are x=0..5157, y=0..4095. These are
observed parameters, not portable camera constants; later generator stages
still transform the normalized points before the final 226-knot spline.
A preliminary comparison incorrectly assumed denominator 16383; disassembly
resolved the actual denominator 4095 and separate offset multiplier 16383.
Only the corrected formula has zero-error evidence.

Private evidence: raw-tone-densification-20261025/shared-helper-proof.json
and raw-tone-normalization-20261025/normalization-proof.json, with completed
renders and unchanged source hashes. No installed candidate was modified.


### Intermediate-point warp equations verified

The next generator block at 0xdd730..0xde0a3 blends three affine coordinate
transforms around a pivot. Each transform is
`(input*span/4095 + offset)*output_scale/16383`. Below the pivot its edge
blend uses `1-(1-t)**left_power`; above it, the observed branch blends
linearly toward the right transform. The alternate upper power branch is
visible in disassembly but is not established by these neutral captures.
Ordinate scaling is `value*65535/16383` in the observed configuration.

Focused probes captured the scalar spans/offsets/pivot/powers, original dense
points and final points, and separately watched the nonmonotonic fallback.
Using those scalar reference parameters, independent arithmetic matches all
452 final coordinate/ordinate values per RAW exactly for RP IMG_2408,
RP IMG_2440 and the EOS R fixture (1,356 values total). None took the
fallback branch. RP IMG_2408 uses raw pivot 1200, plateau endpoint 13200
and coordinate output scale 32767. Those are evidence, not hardcoded app
constants. The origin of the scalar warp parameters remains unresolved.

Evidence: raw-tone-point-warp[-rp2440|-eosr]-20261025/
mathematical-warp-proof.json, trace.json and source/render proofs. No new
production API was added for opaque captured parameters; the next work is
the parameter derivation. Installed builds remain unchanged.


### Warp coefficients derived from generator entry arguments

The captured intermediate spans/offsets are now independently derivable for
the observed branch. Let L/U be the typed lower/upper entry bounds, P the
exposure-scaled integer raw pivot, T four times the exposure-scaled integer
target, and S the output scale (32767 in these captures). With
D=U-L, O=L*16383/4095, Q=P*D/4095+O and H=U*16383/4095:

- Aend=(T-O)*D/(Q-O)+L; A=Aend-L.
- Bstart=U-(H-T)*D/(H-Q); B=U-Bstart.
- Base offset is O; right offset is Bstart*16383/4095.
- The scaled pivot is S*T/16383; right threshold is S*Q/16383.

The six scalar settings at generator entry are 1,2,3,2,4,0 in these runs;
only their roles in the observed formulas are established. The final value
scales P and target by 2**EV, with native integer truncation before subsequent
scaling. Settings slots 1..4 supply maximum span ratio, base power, transition
threshold and upper transition threshold. If A/B exceeds the maximum ratio,
the edge span/offset are limited around the raw-pivot anchor; otherwise the
edge span is A and its lower endpoint L. The power factor is the base power
below the transition, otherwise a linear interpolation toward 1, clamped
from below by 1. The native right exponent is max(1,edge_span*factor/B);
the observed left-exponent selection uses 1 when A*factor/edge_span<1,
otherwise that same right exponent.

Independent arithmetic reproduces all 12 recorded coefficient/metadata
values exactly in each of the three RAW captures (36 comparisons, max error
0.0), without reading intermediate native coefficients as inputs. Evidence:
derived-parameter-proof.json in raw-tone-point-warp[-rp2440|-eosr]-20261025.
This verifies the neutral branch/entry values, not arbitrary settings,
degenerate denominators, the nonmonotonic fallback or all exposure branches.

A separate read-only search decoded all 26 fields in each of the six bundled
PF3s and found no literal uint16 sequence matching these ten source knots
or Standard ordinates. This only excludes that literal storage representation;
it does not prove the absence of another encoded representation. Source-knot
selection and camera-specific entry bounds remain to be traced. No production
API or installed build changed during this step.


### Source tone descriptors across all six base styles

Six fresh RP IMG_2408 developments captured the generator descriptor directly
at entry (274 bytes). Its third uint16 is the source point count; point x
values start at byte 6 and y values at byte 134. All observed cases have
10 points. Standard/Portrait/Landscape share descriptor SHA-256
833a27cec33dd4ac07b747409d22226bff3cea4b9ffb176bc9b9cca5eab136bc;
Neutral/Faithful/Fine Detail share
defed157976179ee7c7666d31d6ce62bcfc34ef710138b1ea8156e07f2a883aa.
Their x positions coincide but ordinates differ. This is tone-only evidence;
it does not make the complete colour rendering equivalent within either group.
Private descriptors and full curves remain outside the tracked app assets.

The source component is resolved by the generic getter 0x60030, called from
0x62073. Runtime RTTI identifies its underlying object as CDppMemoryStream.
Virtual slot +0x130 dispatches to 0x54310, which returns the pointer at object
offset +0x70. Adding 0x40 to that returned buffer yields the exact descriptor
pointer passed to 0xdc120 (checked within one owned-process render). This
locates the source storage; how it is populated/selected remains unresolved.

Literal little/big-endian uint16 source-knot sequences were absent from the
two source RAWs. Literal uint16 sequences were also not found by the earlier
installed-file scan. These searches do not exclude compression, interleaving,
scaling or another representation and do not establish the source of the data.
Evidence: tone-descriptors-six-styles-20261025.json and
raw-tone-source-component-20261025/component-proof.json, with completed
renders and unchanged source hashes. No installed build changed.


### Model-provider provenance and packed-record decoder

The source memory stream is 352 bytes. Its construction/copy routine 0x60c90
receives a stack-built payload from caller 0x68d84. The builder at
0x68930..0x69096 first requests property 0x2e0f01 (1,918 bytes) through
CDppModelObject::dispatch at DppCore 0x129910. A focused registry trace
confirmed successful callback DppModel.dll+0x4ed40. The core callback receives
the source tone descriptor unchanged at property-block offset 0x224;
0x599b0 copies those 274 bytes into the 352-byte stream payload. Hashes match
from provider output through packing and final generator input.

DppModel.dll is in DPP4Lib/Model/. Its callback reaches the property case
at 0x1692d and, in the observed configuration, invokes the tone extractor
0x566f0 through 0x17002. The extractor selects a model record and style
subrecord (observed strides 0xe46 and 0x20a), then parses via 0x55090 ->
0x54e60. The actual Standard source begins at DppModel RVA 0x1f25356.
It consumes 58 bytes, and a PE RVA-to-file comparison confirms the packed
record exists byte-for-byte in the installed DLL. The earlier literal scan
missed it because it searched little-endian data; this record is big-endian.

The independent decode_model_tone_record reads bounded big-endian headers,
two point arrays, six trailing fields and any version extensions into the
padded 274-byte little-endian descriptor. It reproduces the native mode
override, 12-to-14-bit point scaling and optional range normalization.
Synthetic unit fixtures contain no Canon model records. A direct owned-process
NativeFunction comparison passes three cases (scaling, version extension,
normalization on/off) byte-for-byte, plus the real 58-byte Standard record
whose output matches the consumed descriptor SHA-256. All 23 tests pass,
including truncated/oversized/malformed inputs.

Evidence: raw-tone-stream-payload-20261025/payload-proof.json,
raw-tone-camera-provider-20261025/provider-proof.json,
raw-tone-model-dispatch-20261025/dispatch-proof.json,
raw-tone-packed-record-20261025/packed-record-proof.json and
raw-tone-record-decoder-20261025/decoder-proof.json. The dynamic block trace
is an investigation aid, not proof that every basic block was captured.
The original short-call interception failed; moving it to a preceding
instruction produced an error-free completed trace. Model/style record
selection and an independently distributable source of calibration data
remain unresolved; no model record or DLL was bundled, and no installed
app or physical camera changed.


### Model record and style-subrecord selection

The model tone extractor uses 0x57570 for its record index and 0x55440 for
its style index, then remaps Fine Detail index 6 to tone subrecord 3.
Static inspection finds 117 accepted model-group slots sharing 46 selection
paths; this is internal dispatch coverage, not 117 validated camera models.
Selection compares ISO, a float field (observed 0.00800000038 in the RP
fixture), a selector, flags and another narrow option. The float resembles
exposure duration, but its semantic unit is not independently established.
An early probe labelled the selector cameraId; it is now recorded as
selector because that meaning was not proven.

Seven completed developments cover all six styles on RP IMG_2408 and
Standard on the EOS R fixture. RP selects model group 93, ISO 100, selector
1, flags/option 0 and record index 55. EOS R selects group 91, ISO 250
and the same record index. Style indices are 0,1,2,3,4,6; Fine Detail's
final tone subrecord is 3. Selected packed-record RVAs match
Standard_RVA + final_style_index*0x20a in all seven cases. Matching is by
the actual generator descriptor hash, not the first parsed record: setup
also reads Standard before the requested style, so first-hit selection
would incorrectly report Standard for every case.

The independent model_tone_style_index reference handles all observed style
identifiers and rejects unsupported inputs. A NativeFunction comparison of
all 256 byte identifiers finds 12 supported identifiers, with exact mapping
after the extractor remap; unsupported native results are 32768 and become
explicit validation errors. This does not establish custom-style rendering
or replace the unresolved model/ISO/float/flag record-index logic.

Evidence: tone-selection-seven-cases-20261025.json and
raw-tone-style-index-oracle-20261025/style-index-proof.json. All 24 tests
pass. No model calibration records were bundled and installed builds did
not change.


### Full-table model tone decoding coverage

The selected source table at DppModel RVA 0x1ef4160 declares 96 records.
Its extent is 4 + 96*3654 = 350,788 bytes. Each record contains seven
522-byte style subrecords; each subrecord contains nine 58-byte curves.
The independent decoder consumes the entire declared extent exactly:
6,048 curves, no gaps or overruns. Packed headers are (10,9,active), with
active counts 6..10. Counts: active 10=4092, 9=1123, 8=467, 7=232, 6=134.

A fresh owned-process NativeFunction run decoded every curve using the
native parser with mode 1 and range normalization enabled. Its 6,048
274-byte descriptors match the independent decoder byte-for-byte across
all 1,657,152 bytes, SHA-256
d4fa85304c3dc916dbb2e590a05c78f7aad18efc0003c5560a21991842f5aa8b.
Every native invocation consumed exactly 58 bytes. The synthetic parser
checks already cover version extensions and the alternate scaling branch;
this full-table run specifically covers the observed version-9 table.

Evidence: raw-tone-model-table-20261025/table-decoding-proof.json and
raw-tone-full-table-decoder-20261025/full-table-proof.json. The private
probe verifies the table version before using its version-specific RVA.
This establishes decoder breadth, not the model/ISO selection rules,
96 physical camera validations or complete Canon RAW colour matching.
No captured model table or decoded descriptors were added to the app.
Installed candidates remain unchanged.


### Independent model tone-record selection

Added an offline Python reconstruction of the scalar record selector for
all 117 internal model groups. It uses ordinary branches, float32 input
quantization and the observed signed/unsigned integer semantics; it does
not load Canon libraries, interpret machine instructions or bundle model
calibration tables. No production renderer calls it yet.

The initial 9,977 defined random cases matched the native selector. A fresh
owned-process boundary run matched another 65,331 cases across all groups:
ISO thresholds and their immediate neighbours, signed uint32 boundaries,
float32 neighbours of 1/4/10/15, selectors, flags and option boundaries.
There were zero mismatches. Source hashing confirms the RAW was unchanged.
The first attempted probe exited without rendering because RAW_SOURCE was
missing; only the subsequent successful render is counted as evidence.

189 boundary combinations reach a native path that reads an unwritten
home-stack slot. The independent reference rejects these explicitly rather
than inventing a stable result; they were excluded from native comparison.
Tests preserve native-verified examples for every group and every observed
return value, reject invalid inputs and cover the undefined path.

Evidence: raw-model-selector-oracle-20261025/oracle-proof.json and
raw-model-selector-boundaries-20261025/{oracle-proof,source-proof,render-proof-observed}.json.
117 internal groups do not imply 117 physically tested cameras. This does
not establish the mapping from RAW metadata to groups, complete tone-table
generation or Canon colour parity. Installed APK/EXE builds are unchanged.


### Canon model identifier to tone-group mapping

The extractor resolves its input model ID through a bounded list of 118
identifier/group pairs. Reconstructed that metadata lookup independently.
An owned-process native comparison covered all 118 known identifiers plus
unknown probes (122 distinct inputs), with zero mismatches. The RP ID
0x80000433 maps to 93; EOS R 0x80000424 maps to 91, matching the prior real
RAW observations. Unknown identifiers become explicit errors in the Python
reference rather than a guessed camera fallback.

Evidence: raw-model-group-map-20261025/mapping-proof.json, source-proof.json
and render-proof-observed.json. This lookup contains identifiers only, not
colour or tone calibration arrays. It is still offline research: the model
list includes groups 118 and 119 outside the selector's supported 1..117 range, and
resolving a model ID does not prove that its renderer is supported. The
metadata path from a RAW file to the extractor inputs remains to be traced.
All 28 reference tests pass. Installed builds were not changed.


### RAW metadata provenance of selector inputs

Fresh extractor-entry observations on IMG_2408, IMG_2440 and IMG_2134
match the CR3 CMT2 TIFF ExposureTime (33434) and ISO (34855) tags exactly
after the shutter value is quantized to float32. The CMT3 model ID tag
0x10 also matches the extractor model ID, 0x80000433. Each file supplied
five extractor and five selector calls; all agree with the independently
parsed metadata and resolve through group 93 to record 55.

Renamed the offline selector parameter from ambiguous exposure to
shutter_seconds: the observed argument is capture duration, not editor EV.
Three capture-metadata regression fixtures cover this distinction.
Evidence: tone-input-metadata-proof-20261025.json and the three
raw-tone-input-metadata-img_*-20261025 probe directories, each with source
hash preservation and successful render proof. No physical camera access.

Scope: these are three RP captures only. Selector/flags/option values are
observed as 1/0/0; their complete metadata provenance and alternate paths
remain unresolved. This does not supply model calibration curves or make
the independent renderer complete. Installed applications are unchanged.


### Independent dense-curve normalization chain

Added the bounded affine normalization helper to the offline RAW reference.
It preserves the native 4095 denominator and 16383-scaled lower offset,
including nonzero lower bounds. Chaining the existing natural spline
densification and this normalization from the captured source control
points reproduces all 226 X and 226 Y coordinates exactly in each of the
RP2408, RP2440 and EOS R references (1,356 scalar comparisons, max error 0).
The comparison uses source knots and scalar bounds, not captured dense
coordinates as inputs. Source model control points remain private fixtures.

Evidence: tone-dense-normalization-chain-proof-20261025.json. Synthetic
regressions cover identity, nonzero bounds and malformed coordinates or
ranges. This is an offline intermediate stage; the coordinate warp and
final resampling are not yet integrated into a complete generator API,
and no installed build has changed.


### Source-control-point to final tone table chain

Integrated offline coordinate warping and fixed 2048-entry resampling
with the existing spline/normalization primitives. Starting from source
control points, using observed scalar warp parameters and secondary
lookup control points, the independent chain reproduces all 6,144 final
uint32 entries across RP2408, RP2440 and EOS R exactly. No captured final
table, dense coordinates or final spline derivatives are used as inputs.

Evidence: tone-coordinate-warp-chain-proof-20261025.json (1,356 warped
coordinates, maximum absolute error zero) and
tone-source-to-final-chain-proof-20261025.json (three tables, zero unequal
entries). The source model curves and scalar observations remain private
research inputs, not bundled calibration assets. Synthetic unit tests
cover identity coordinates, clipping/resampling and invalid warp domains.

Limits: the scalar warp parameters still come from observations rather
than the integrated generator-entry derivation. These three references
exercise the linear upper blend; the alternate power branch follows the
observed instructions but is not native-oracle validated yet. The native
nonmonotonic fallback is explicitly rejected rather than approximated.
This is not complete Canon RAW colour rendering, and no installed build
was updated or published.


### Integrated generator scalar derivation

The offline derivation now computes base/right spans and offsets, limited
edge range, blend powers, scaled pivot/threshold and scale from six scalar
settings plus typed generator entry arguments. It reproduces 33 observed
coefficients exactly across RP2408, RP2440 and EOS R. Trailing nonincreasing
source values also yield the observed effective end coordinate (13200),
without taking that endpoint from the warp capture.

The full private chain now uses source control points, generator entry
scalars, range bounds and secondary adjustment control points. It no
longer consumes captured warp coefficients, dense/final coordinates or
final spline derivatives, yet all three final tables remain byte-exact
(6,144 uint32 entries). Evidence:
tone-parameter-derivation-integrated-proof-20261025.json and
tone-entry-to-final-chain-proof-20261025.json. Synthetic regressions cover
symmetric ranges, both scale flags and rejected malformed domains.

Scope remains neutral editor EV for these three references. Nonzero EV
preprocessing, alternate power/limited-range paths and the native fallback
still require targeted oracle validation. Static model curve provisioning
and complete sensor-to-colour reconstruction remain unresolved. No Canon
curve table was bundled; no APK/EXE update or publication occurred.


### Alternate warp branches and adaptive final sampler

Three fresh owned-process probes changed only temporary generator inputs:
upper-power target 450, upper-limited target 900, and lower-limited span
limit 0.4 with target 300. All used the RP2408 source and preserved its
hash. Derived coefficients and warped coordinates match exactly in all
three, exercising the previously unvalidated power and limited-span paths.

Initial final sampling disagreed in two entries of upper-limited and four
of lower-limited. The final generator calls a distinct cached evaluator
(DppCore 0xdf670), which uses linear interpolation if either endpoint
second derivative times 0.3 in absolute value is no greater than the
absolute difference of the two derivatives. Otherwise it uses the cubic
formula. This curvature guard was absent from the independent sampler.
It belongs only to this final sampler; the generic spline and densification
functions retain their existing cubic behavior.

After implementing the guard, all 6,144 pre-secondary-lookup entries in
the three alternate cases match exactly. The original RP2408/RP2440/EOS R
pre-lookup tables also remain exact. Evidence:
tone-alternate-warp-oracle-proof-20261025.json and
tone-adaptive-sampler-regression-proof-20261025.json, plus three
raw-tone-warp-*-20261025 probe directories with source/render proofs.
The failed initial comparison is retained in this account, not counted as
success. A synthetic sharp-curvature regression covers the interpolation
decision without bundling model curves.

Remaining limits: nonzero-EV preprocessing, nonmonotonic fallback, model
curve provisioning and complete sensor-to-colour reconstruction. Installed
applications are unchanged; no physical camera access or publication.


### Editor exposure coverage through core-entry scalars

Five fresh owned-process renders of RP2408 used editor compensation -2,
-1/3, +1/3, +1 and +2 EV. Source hashes remained unchanged. The six core
settings remain (1,2,3,2,4,0), and the raw pivot remains 1200; changes are
already encoded upstream in the core target/upper-bound arguments:
(1200,20630), (377,6498), (238,4093), (150,2578), (75,1289).

Using those typed entry scalars, the existing independent derivation,
densification, normalization, warp and adaptive sampler reproduce all
10,240 pre-secondary-lookup table entries exactly. Added five native-
verified scalar regression fixtures and corrected the helper docstring:
neutral core settings do not imply that editor EV was neutral.
Evidence: tone-editor-exposure-chain-proof-20261025.json and five
raw-tone-exposure-*-20261025 folders with source/render proofs.

This validates the downstream chain at these editor settings, not an
independent implementation of upstream EV preparation. In particular,
scaling an already rounded upper bound would lose information (20630 at
-2 EV cannot be obtained by multiplying the rounded neutral 5157 by four).
The unrounded upstream source still needs tracing. Static model curves,
nonmonotonic fallback and complete colour rendering remain unresolved.
Installed builds were unchanged and nothing was published.


### Unrounded range descriptor preparation

Traced the generator target/upper inputs to the six-double property
0x20302 range descriptor through DppCore 0x561e0. The factor is
2**12 / 2**descriptor[0]; each scalar is truncated only after multiplication.
Output order is fields 1,3,2,4,5 (lower,target,upper,y-lower,y-upper).
The five EV probes carry scale 14 and retain full-precision upper values:
82523.18838759397,25993.17553849245,16374.674507279571,
10315.398548449246,5157.699274224623.

The independent bounded helper matches 322 actually written output scalars
across 94 native calls. Calls with null optional output pointers are
compared only at outputs the native routine wrote. Initial comparison
caught a swapped target/upper output order, then corrected from the call
ABI; no mismatching comparison is counted as a successful proof.
Evidence: tone-range-preparation-proof-20261025.json and five
raw-tone-range-preparation-*-20261025 directories, each with render/source
proofs. Five complete native-verified descriptor fixtures are unit tested.

Chaining from these unrounded descriptors instead of captured generator
range arguments still reproduces all 10,240 pre-secondary-lookup entries
exactly: tone-unrounded-descriptor-chain-proof-20261025.json.
The descriptor itself is still observed input: its upstream sensor/EV
construction has not been independently reconstructed. The result must
not be described as complete EV or RAW rendering. Builds remain unchanged.


### Zero-lower-bound descriptor EV scaling

Traced the range getter through temporary wrapper DppCore 0xe60e0,
dispatch 0xe64d0, proxy 0x26540 and cached property getter 0x5c0e0. The
latter only copies an already computed range. An owned hardware write
watchpoint on the old cached upper field triggered during object cleanup
and copying (0xe331, through 0x5adb2/0x69fe4/0x6cc98); this is not evidence
of the upstream mathematical writer. A failed short-instruction hook was
replaced by a preceding instruction hook; its failed output is not proof.

Independently, baseline and EV descriptors captured in each of five
successful reference processes establish exact double-precision scaling
of fields 2 (upper) and 3 (target) by 2**(-EV), with the other four fields
unchanged, for the observed zero lower bound. All five reconstructed
descriptors match the observed doubles exactly and give identical integer
core-entry arguments. Evidence: tone-range-ev-scaling-proof-20261025.json.
The offline helper preserves the input and postpones quantization until
prepare_tone_entry_ranges. Tests cover all five cases and reject nonzero
lower-bound descriptors until that path has native evidence.

This removes the captured EV-adjusted descriptor as a necessary input,
but the neutral descriptor (especially its scene-dependent upper value)
is still observed input. Complete RAW rendering is not established.
No camera access, installed-build modification or publication occurred.
