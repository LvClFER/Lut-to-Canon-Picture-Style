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
