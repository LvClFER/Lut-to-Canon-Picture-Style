# Isolated compiler math progress

No camera access, no production transport changes, no on-disk Canon DLL changes.

- Independent forward/inverse color math matches 256 synthetic cases per direction, including inverse clipping return codes.
- Actual compiler color calls: 208 sampled calls across nine representative routes match within 1e-14. Four older routes do not call these helpers and are not covered by this claim.
- Correction after complete-table verification: source data starts at offset **12**, not 20; compact destination starts at offset **16**. The earlier offset-20 match on 0x1070 was an identity-grid false positive, not a channel conversion.
- Both 0x1070 and 0x1071 enter 0x196a0 as sequential float64 values equal to decoded BE disk words divided by 4095, without channel/axis permutation.
- Complete validation: 26 table captures (12 unique fixtures plus duplicate identity), 2,803,086 values, maximum absolute error **0**. Captured sources are hash-checked before comparison.
- Static 0x196a0 also reads source at `[ebx + eax*8 + 0xc]` and writes destination at `[edi + eax*8 + 0x10]`, independently supporting the observed header distinction.
- This establishes source loading for the observed compact conversion, not complete independent interpolation or camera acceptance.

Private evidence under workspace tmp/PF3_FIELD_EXPERIMENTS_20261004:
NINE_ROUTES_COLOR_TRACE.json, NINE_ROUTES_COLOR_CHECK.json,
NINE_ROUTES_GRID_SAMPLES.json, RP_GRID_LAYOUT_CHECK.json, RP_GRID_SOURCE_CHECK.json.
Superseding complete evidence: RP_ALL_VECTORS_DENSE_TRACE.json, RP_ALL_VECTORS_DENSE_CHECK.json, RP_GRID_LAYOUT12_CHECK.json.

## Subsequent independent math validation

The isolated direct-call ABI matched the stock compact converter byte-for-byte.
The destination is planar `(channel, R, G, B)`, with its data at offset 16.
All 54 synthetic/captured null-curve cases match the independent reference:
162,000 values, maximum floating error 5.684341886080802e-14.
This includes identity, constants, channel swaps/gains, products, squares,
impulses and irregular modular grids, both converter options and flags 0/1/2.

Flag 2 samples coordinates `min(i*32/255,1)` and scales by 255.
Flag 1 extrapolates diagonally from A (coordinates capped at 224/255) to B
(coordinates capped at 1), as `(32*B-A)/31`, then scales/clamps.
Flag 0 uses a distinct boundary formula `(32*B-1.1*A)/30.9`, followed by
integer truncation. Interior values are simply truncated. It is not rounded
flag-1 output. The last two nodes duplicate the extrapolated endpoint.

The 240-byte 0x1021/0x1029 records are three rows of 20 signed 16.16 words:
19 cubic coefficients and one padding word per row. The basis has no constant:
R,G,B,R²,RG,RB,G²,GB,B²,R³,R²G,R²B,RG²,RGB,RB²,G³,G²B,GB²,B³.
Modern conversion truncates coefficients to six decimal places after decoding.
416 basis/real-call/coefficient-origin checks pass, maximum error 5.55e-17.

Controlled single-coefficient mutations, 27 compilations across nine routes,
show both records affect M50, 5DS, R5, 1DX III and C50 outputs. They do not
affect the tested M3, 1D III, 450D and 7D II paths. Those paths may use already
baked tables; this does not establish that their rendering is incorrect.

The finalized cached-curve evaluator uses adjacent Y values indexed by
`position*(count-1)`, ignoring the cached X coordinates. 84 direct evaluations
match exactly; negative positions are deliberately excluded.

Modern output headers are independently observed: 17-node flag 2 uses scale
255.75; 33-node flag 3 uses scale 32768 and integer-valued stored doubles.
These observations do not yet reproduce the complete modern conversion.

The RGB/Lab helpers at 0xf070/0xee40 are also independently reproduced:
768 direct cases at 8/12/16 bits and numeric modes 1/2 match exactly in both
directions. Lab is signed fixed 16.16 in ordinary L/a/b units, with D65-like
white constants X=.9505 and Z=1.089; profile names remain unasserted.
The implementation preserves Canon's approximate thresholds/constants rather
than replacing them with an idealized textbook formula.

Private superseding evidence: COMPACT_ALL_FLAGS_REFERENCE_CHECK.json,
POLYNOMIAL_BOTH_TABLES_QUANTIZED_CHECK.json,
NINE_ROUTES_MATRIX_SENSITIVITY_CHECK.json,
CACHED_CURVE_REFERENCE_CHECK.json, LAB_HELPERS_EXPANDED_CHECK.json.
All remain research artifacts, not redistributable Canon fixtures.

Next: trace the ordering of curves, polynomial stages and gamut mapping in
modern conversion; identify sector/parameter records and remaining payload
packing. No camera transport, installed DLL or public build was changed.

## Boundary policy investigation (negative evidence retained)

Read-only nine-route tracing found no calls to 0xf730 for the baseline fixture.
Doubling only the first 0x1021 or 0x1029 coefficient changes 37,124 / 34,148
bytes respectively in the tested R5 route, but still does not call 0xf730.
Static 0x11220 distinguishes policy 1 (component clamp to 0..1) from policy 2
(call 0xf730 only when polynomial output leaves the gamut). Policy argument
6 is observed as 1 in the successful modern calls. This explains why merely
increasing coefficients did not exercise compression.

The two words of 0x1023/0x102b are not established as that policy selector.
Changing their first word from 1 to 2 preserves the payload in the tested
R5 route and leaves the observed argument at 1. Changing their second word
from 0 to 2 produces a Canon access violation, reproduced without any MLib
observer. These are unsupported private research fixtures, not usable styles.
No assertion is made that these records contain two independent enum flags.
The harness records a failed-not-validated result and continues in a fresh
isolated host rather than losing the remaining experiments.

Evidence: NINE_ROUTES_GAMUT_TRACE.json, MATRIX_GAMUT_R5/FIELD_EXPERIMENTS.json,
POLICY_R5_COMPLETE/FIELD_EXPERIMENTS.json and
POLICY_R5_NO_OBSERVER/FIELD_EXPERIMENTS.json.

## Ordered modern stages and six-group parameters

Nine-route caller/phase tracing validates 316 sampled polynomial/Lab stages
exactly, plus 320 RGB/XYZ helper calls within their established tolerance.
Curve calls record caller/cache identity, not SSE input/output registers:
those are deliberately not claimed as captured by Frida's CPU context.
Separate direct curve-evaluator tests remain the numeric authority.

The observed modern sequence includes per-channel cached curves, polynomial
transform, post-polynomial curves, optional profile conversion through Lab,
six-group processing at 0xfa40, and subsequent RGB/XYZ profile conversion.
The Lab roundtrip can use different mode numbers in each direction, so it
is also a profile-conversion step, not proof of an adjustment in Lab space.
Actual Lab inputs use 24-bit RGB precision. The expanded independent probe
now passes 1,024 synthetic cases exactly both ways at 8/12/16/24 bits.

0x1061 and 0x1062 are separately matched byte-for-byte (after BE->LE word
conversion) to initialized 512-byte parameter blocks passed to 0xfa40 in
different phases. Each has header words (2,6), then six 21-word groups with
centres 0,60,120,180,240,300. This is no longer merely an appearance-based
guess about similarly sized records.

Single-field +10 mutations at absolute words 16/17/18 change the tested
modern payload, and direct 0xfa40 measurements identify respectively hue,
saturation and lightness adjustments for the first/red group. Hue +10
shifts red by exactly 10 degrees in the measured samples. Saturation and
lightness effects vary with input lightness/saturation; their full weighting
and sector-boundary formulas are not yet independently reproduced.
Green, blue and neutral-grey test inputs remain unchanged for these red-axis
mutations. The direct native return register is unspecified, not a status.

Evidence: NINE_ROUTES_STAGE_ORDER_LAB_TRACE.json,
NINE_ROUTES_STAGE_ORDER_CHECK.json, LAB_HELPERS_24BIT_CHECK.json,
AXIS_PARAMETERS_R5/FIELD_EXPERIMENTS.json and SIX_AXES_DIRECT_PROBE.json.
All probes remain isolated; no production UI/transport/build changes.

## Independent six-axis and 17-node packing

Default six-sector geometry is now independently reproduced, including
neighbor weighting, the logistic blend, asymmetric positive/negative
saturation response, cone coordinates and gamut compression. All 13,545
direct cases pass (maximum error 8.89e-16), covering all six axes, combined
adjustments and equal softness values 0/5/10/20/30/60 degrees. Nondefault
sector bounds and unequal softness remain explicitly unsupported.
The one endpoint discrepancy was caused by colorsys hue normalization:
native sector arithmetic must be preserved at strict branch endpoints.

EdsCFParse 0x4bb40 packs planar 17-node floats through two observed
luminance/chroma coefficient sets, scale 4, signed chroma clipping and
10-bit fields. The output word is Y:Cb:Cr (bits 20:10:0), with R/B grid
axes transposed. Eight exact packer captures across R5 and 1DX III match
the independent implementation and all four final decoded blocks per
payload byte-for-byte. Upstream intermediate grids are not necessarily
the final packer input; initial unmatched intermediates remain recorded.

Evidence: SIX_AXES_SOFTNESS_CHECK.json, NINE_ROUTES_FINAL_PACKING_TRACE.json,
FINAL_PACKED17_CHECK.json. Stock payload captures remain private workspace
research fixtures. This is mathematical/compiler evidence, not physical
validation of additional cameras or a complete independent compiler.

Expanded packing evidence:
- 17-node: 96/96 final blocks across 12 PF3 vectors and two virtual routes.
  The first run recorded two redundant identity capture errors; case
  deduplication now prevents that, and those original errors are retained.
- full33: 24/24 final blocks across 12 vectors; initialized integer-valued
  planar doubles map directly to LE uint16 at offsets 372/215994.
- compact: 144/144 direct float packer captures across six virtual routes.
  Final 8192-byte blocks contain two separately encrypted 4096-byte regions,
  with seeds 0xb8ed and 0x33137; decoding the entire 8192 bytes continuously
  was not the correct containment test. Five old routes match both regions.
- M50 uses a later integer packer, 0x49e00, with planar Y/Cr/Cb input.
  All 72 captures pass, including its 48 final blocks across the 12 vectors.
  Earlier float-packed intermediates are discarded/changed by this branch,
  so their lack of final containment is not a packing-math failure.
- 0x47af0 fixed-point tetrahedral interpolation is independently reproduced
  for 5,280 synthetic cases: all six fraction orders, ties, signed tables,
  impulses and modulo-32-bit overflow. It drops four coordinate low bits,
  uses weights summing to 64 and returns channel order 0/2/1. Negative or
  out-of-domain coordinates are deliberately not called or claimed safe.

Evidence: PACK17_ALL_VECTORS_CHECK.json, FULL33_ALL_VECTORS_CHECK.json,
PACK10_ALL_VECTORS_CHECK.json, M50_FINAL_PACK_CHECK.json and
INTEGER_TETRAHEDRAL_EXPANDED_CHECK.json. Captured stock payload hashes are
checked before final-payload comparisons. No production path was replaced.

## Integrated modern conversion and endpoint investigation

The initialized 0x11220 argument layout has been resolved and replayed
through a caller-cleaned x86 adapter: two complete 17-node native grids
are byte-identical. The additional empty legacy list is only an eight-byte
header (1,0); earlier 512-byte reads included unrelated heap bytes and are
superseded by the bounded observer. Nonempty legacy lists remain unsupported.

Independent floating XYZ/Lab helpers 0x1470/0x1600 pass all 256 direct cases,
separate from the fixed-point RGB/Lab helpers. Their reference white is D65
in mode 12 and D50 otherwise. The integrated modern reference now connects
identity cached curves, polynomial coefficients, fixed RGB/Lab profile
roundtrips, default-geometry six-axis processing, luminance XYZ/Lab and
output scaling. It does not invoke native helpers during calculation.

Both complete full33 identity grids match all 215,622 integer components
exactly. Initial mode-1 endpoint discrepancies (up to two output levels)
were caused by incorrect boundary assumptions in the reference: Canon
passes 2**24, not 2**24-1, at unit inputs; its fixed RGB/Lab roundtrip can
slightly overshoot 1 and then enters cone gamut compression rather than
premature channel clipping. Native green endpoint samples and a permanent
unit regression cover this correction. Wider out-of-gamut domains are not
claimed validated.

Fourteen complete 17-node grids across identity and six single-axis scratch
mutations pass within 2.17e-12. Independently packed output is byte-identical
to packing the native grids, and the appropriate coefficient mode matches
an observed final Canon packer block in every case. The 1061 mutations do
not alter this modern 1062 stage; they must not be counted as six distinct
nonneutral modern controls. Only identity curves/default axis geometry are
currently supported by the integrated reference.

Evidence: FLOAT_LAB_CHECK.json, MODERN_DIRECT_REPLAY.json,
MODERN_FULL33_GAMUT_CHECK.json and MODERN_NONNEUTRAL_AXES_CHECK.json.
Earlier failed comparisons are retained as negative evidence, not erased.
All work remains private offline research, not universal camera validation.

The curve integration has since expanded beyond identity: five nonlinear
1018 scratches (three/four/five/six control points, including nonmonotonic
curves) pass both full33 modes, 12/12 complete grids including the baseline.
Zero-count channel records use a native 301-sample identity fallback, not
the explicit 256-sample identity. B-spline sampling and finalization are
computed independently. The exact stage order is ECX/1018 pre-RGB,
EDX/1065 post-RGB and stack0/1019 luminance; initial identity-only comparisons
could not distinguish the latter two. Targeted END230 mutations resolve
the ambiguity: all eight 17-node stage cases pass numerically and packing
remains byte-exact. Nonidentity chromatic curves in the luminance group
remain deliberately rejected until their behavior is mapped.

Evidence: MODERN_FULL33_NONLINEAR_ZERO_FALLBACK_CHECK.json and
MODERN_17_CURVE_STAGES_ORDER_CHECK.json. The initial swapped-stage report
is retained. Reference unit suite: 120 passing tests at this checkpoint.

## Preceding selective-color branch and compact boundaries

The 0x14bd0 argument ABI also replays exactly (two 17-node grids and one
10-node grid). Its kind-2 neutral block has two five-point groups (176
bytes); kind-1 profile lists contain five/six four-point groups (348/416
bytes). fa40 derives each group stride as 4+16*points. The observer now
captures these bounded initialized blocks, rather than treating all lists
as modern 512-byte six-sector records.

Ten distinct captured kind-1 groups were independently reproduced on a
9x9x9 synthetic RGB grid: 7,290/7,290 exact matches, including all 350
actually affected samples. The selector combines triangular H/S/L weights;
the measured power-1 composition adds the weighted group deltas. Stronger
composition gamut branches remain explicitly unsupported. Captured groups
do not exercise those branches. In the actual compiler, input/output RGB
alias each other, so groups operate sequentially in-place; the disjoint
synthetic helper buffer alone does not establish multi-group ordering.

Integrated independent 0x14bd0 math now passes all eleven observed contexts
in the nine-route baseline: M50, 5DS, R5 and 1DX III use this stage; the
other routes do not call it in this baseline. The 17-node grids are exact
floating matches; compact 10-node error is at most 5.69e-14 and all tested
packing coefficient modes are byte-exact. Null luminance pointers bypass
XYZ/Lab entirely. Compact flag1 extrapolates the two diagonal points with
32/31 and clips only afterward: premature clipping of a negative profile
intermediate incorrectly removes valid positive boundary values.

Evidence: LEGACY_DIRECT_REPLAY.json, LEGACY_SELECTIVE_COMPOSITION_PROBE.json,
LEGACY_SELECTIVE_INDEPENDENT_CHECK.json, LEGACY_COMPACT_DEFERRED_CLIP_CHECK.json
and NINE_ROUTES_LEGACY_INDEPENDENT_CHECK.json. Earlier failed integrated
comparisons remain retained. No live camera or installed DLL was modified.

## Direct nonneutral preceding vectors and strong selective gamut

PF3 curve field mutations do not change the preceding 0x14bd0 grids in the
R5 route: this branch receives its existing parameters. Those unchanged
captures are not evidence that nonneutral curves work. Direct initialized
function inputs now exercise four nonlinear curves separately in pre-RGB,
post-RGB and luminance, on both 17-node modes and compact flag1. All 39
grids pass independent math and byte-exact packing. With a nonnull luminance
curve, RGB is clipped before XYZ/Lab; null pointers bypass this clipping
along with the Lab stage. Disassembly confirms this conditional clamp.
The initial 12 failing luminance comparisons are retained.

Six nonneutral polynomial variants plus baseline pass all 21 direct grids,
including cross-channel, quadratic, cubic and positive/negative terms.
These are isolated function vectors, not physical camera tests or proof of
PF3 field acceptance in every route.

The four-point kind-1 composition boundary branch has now been translated:
it intersects the adjustment ray with the triangular S/L boundary, adjusts
the shared amount (including hue), then clamps final S/L. Deltas are bounded
by selector extent (centre to lower/upper bounds), not global constants.
The broad synthetic S/L centre .5 and bounds 0..1 happen to yield +/-0.5;
their hue bounds instead allow +/-3. Disassembly resolves this distinction.
Twenty-four captured/synthetic groups on a 9-cube RGB grid pass 17,496 of
17,496 cases (9,268 affected; maximum error 5.56e-17). Strong behavior still
requires explicit research opt-in. Failed preliminary clamp hypotheses
remain retained.

Evidence: LEGACY_DIRECT_CURVE_CLIP_CHECK.json,
LEGACY_DIRECT_MATRIX_VECTORS_CHECK.json and
LEGACY_STRONG_HUE_UNCLAMPED_CHECK.json. No production install path changed.

## Five-point selective target colors

The fifth point (tag4, not modern tag5) is an absolute target color, not a
softness/power control. It overrides deltas with target-minus-original-
centre and quantizes the reference centre toward each RGB sample. Native
quantization uses 256 units and steps 40/32/16/8 for node counts 9/10/17/33.
The resulting centre moves while the selector widths retain their original
extents. Unsupported node counts bypass this target path. Four-point
groups and the measured five-point groups keep composition power1.

Independent selector math passes 40,095/40,095 cases across those four
geometries and a 25-node negative control, including off-grid references
and 16,233 affected outputs (maximum error 1.12e-15). Evidence:
LEGACY_FIVE_POINT_NODE_MATRIX_CHECK.json. Integrated chain testing is
tracked separately; helper agreement alone does not prove chain order.

Integrated four/five-point selector chain: all 21 direct 10/17-node grids
pass, with both candidate packing modes exact. Evidence:
LEGACY_INTEGRATED_SELECTIVE_CHECK.json.

## Preceding global axes and emitted bytes

The captured kind2 two-group geometry has a degenerate neutral group plus
a full-hue global group. On this exact geometry, hue adds globally;
positive saturation and luminance weights depend on cone saturation,
negative saturation uses its direct gain. Composition/gamut math is shared
with the verified modern cone compressor. Independent helper comparisons
pass 5,103/5,103 cases, including 4,272 affected outputs. Full-chain tests
pass all 21 10/17-node grids and byte-exact candidate packing. Other kind2
geometries remain explicitly rejected. Evidence:
LEGACY_TWO_GROUP_AXIS_CHECK.json and LEGACY_GLOBAL_AXIS_INTEGRATED_CHECK.json.

The nine-route capture now retains private final payloads with hashes.
Independent modern math -> packing -> actual payload passes all six grids:
full33 words at 372/215994; modern 17-node outputs in blocks2/3. Each profile
selects one coefficient matrix; testing both candidates does not mean both
are emitted for each profile. Eight final 17-node packer calls also match
their emitted payload bytes. Nineteen compact packer calls match the native
helper exactly, seventeen occur in the payload. The two unmatched M50 float
calls are intermediate computations; later integer packers match emitted
bytes. A 83076-byte modern carrier appends a compact 4096-byte representation
at 78980 encrypted with seed b8ed, independently confirmed on this capture.

Evidence: NINE_ROUTES_SELECTED_PACKING_END_TO_END_CHECK.json,
NINE_ROUTES_FINAL_PACK17_CHECK.json and NINE_ROUTES_FINAL_PACK10_TAIL_CHECK.json.
The earlier verifier that incorrectly required both candidate matrices in
the payload remains retained. Camera ground truth is not implied.

## Unused modern luminance-record chromatic slots

Explicit endpoint and nonlinear mutations of slots1/2 in the luminance
curve record produce byte-identical baseline grids in both profiles of
the R5, 1DXIII and full33 C50 routes: 30/30 isolated replay checks. This is
evidence about these verified MLib routines, not a global claim about all
PF3 chromatic curves. The reference parser still rejects such settings by
default rather than silently accepting them in an unrelated path.
Evidence: NINE_ROUTES_MODERN_CHROMATIC_SLOT_PROBE.json.

## Preceding six-axis transition arithmetic

Feeding the verified modern six-axis parameter layout through the preceding
fa40/10a00 path exposes a small but real difference at transition endpoints:
the wrap sector subtracts six before comparing against low/high bounds.
The modern nearest-sector local subtraction is not bit-equivalent there.
Owned sectors blend their own and neighboring adjustments; they do not
independently accumulate two overlapping selectors.

A separate preceding reference now passes 4,374/4,374 grid cases and
10,146/10,146 extended cases (deterministic random RGB plus transition
neighborhoods at +/-1e-10 and +/-1e-14). Uniform widths0/5/10/20/30/60 pass
11,664/11,664 cases. Modern math was not changed to conceal the discrepancy.
Initial 18/11/6-case failures and their hypotheses are retained. Evidence:
LEGACY_SIX_AXIS_WRAP_ARITHMETIC_CHECK.json,
LEGACY_SIX_AXIS_DENSE_TRANSITION_CHECK.json and
LEGACY_SIX_AXIS_WIDTH_MATRIX_CHECK.json. Unequal widths now pass
10,206/10,206 cases: the owning sector selects its own width, not its
neighbor's. Evidence: LEGACY_SIX_AXIS_UNEQUAL_WIDTH_CHECK.json.

The independent preceding grid chain now accepts canonical six-sector
blocks as well as the separately validated two-group global block.
55 initialized replay cases across eleven captured contexts pass, with
both packing candidates byte-exact. This is synthetic argument testing,
not proof that those PF3 fields are accepted or camera installation works.
Evidence: LEGACY_SIX_AXIS_INTEGRATED_CHECK.json. Nondefault sector geometry
remains a separate research target.

## Preceding axis interactions and nondefault bounds

187 replay cases combining six-sector axes with nonlinear curves pass,
as do 143 replay cases combining all three curve stages, a nonneutral
matrix and strong/target selective color. Both packing candidates remain
byte-exact. Evidence: LEGACY_SIX_AXIS_CURVE_COMBINATIONS_CHECK.json and
LEGACY_ALL_STAGE_INTERACTIONS_CHECK.json. These are initialized argument
vectors, not assertions of PF3 field acceptance.

An experimental independent 10a00 helper now decodes nondefault hue,
saturation and lightness bounds. Rotation +/-15 degrees, half-spans20/40
and saturation/lightness gates20..80 pass 52,488 native helper calls with
zero numerical error and 8,748 composed RGB cases (max2.22e-16).
Adjacent sector extents cap each transition width; overlapping active
sectors accumulate through the original fa40 composition. Evidence:
LEGACY_NONDEFAULT_AXIS_GEOMETRY_CHECK.json and
LEGACY_NONDEFAULT_AXIS_FINAL_RGB_CHECK.json. Larger boundary coverage
and arbitrary geometries remain separate validation tasks; public paths
are unchanged.

The larger geometry batch exceeded the instrumented process budget and
was rerun as six isolated single-case batches. All 60,876 helper calls and
10,146 final RGB samples pass. The complete-chain geometry replay also
passes121/121 with both packing candidates byte-exact. Evidence:
LEGACY_DENSE_GEOMETRY_ROTATE15_CHECK.json, LEGACY_DENSE_geometry_*_CHECK.json
and LEGACY_NONDEFAULT_GEOMETRY_INTEGRATED_CHECK.json.

## Pre-axis selective block and unsafe cached-curve domain

The preceding chain's first optional kind1 block runs after polynomial
gamut policy and before post-RGB curves. Injecting four/five-point groups
reproduces55/77 cases completely, both packed byte-exact;22 are explicitly
unsupported because they feed negative values beyond the zero-index
subsample into cached curve lookup. The read-only fa40 output observer
confirms negative native RGB (up to -0.12490337025780718 in retained2000
observations), not merely an independent-reference artifact. Do not
silently clip these inputs or claim a stable independent memory-dependent
result. Evidence: LEGACY_PRE_AXIS_RGB_OBSERVER.json and
LEGACY_PRE_AXIS_GUARDED_CHECK.json. Mid-function observation caused an
instrumentation access violation; it is not evidence of an uninstrumented
native crash. The successful observer instead uses the function boundary.

Bounded negative curve inputs with trunc(position*(count-1))==0 are
independently reproduced in112/112 native evaluations, error0. Larger
negative indices remain rejected. Evidence:
CACHED_CURVE_NEGATIVE_SUBSAMPLE_CHECK.json. This opt-in does not change
the default safe-domain parser or any public editor behavior.

99 safe pre-axis/nonlinear post-curve chain cases now pass, packed exactly.
Sequential two/three selectors in both orders also pass77/77 after an
explicit0.25 in-place research margin (the default remains0.05). The first
guarded rejection report is retained. Evidence:
LEGACY_PRE_AXIS_SAFE_CURVE_INTERACTIONS_CHECK.json and
LEGACY_MULTIPLE_GROUP_WIDE_MARGIN_CHECK.json.

## Polynomial gamut policy2

An independent f730 reference reproduces172/172 bounded positive-gain
vectors with zero numerical error. Native behavior uses a normalized ray
toward centre=(max+min-1)*0.25+0.5, sign-switching steps and an endpoint fade.
The initial step-branch interpretation failed74 cases; the corrected
branch passes all172. Evidence: POLYNOMIAL_GAMUT_POLICY2_FINITE_INTERVAL_CHECK.json
(failed hypothesis) and POLYNOMIAL_GAMUT_POLICY2_STEP_BRANCH_CHECK.json.

Synthetic rays without a feasible gamut interval can leave the native
routine running; the harness now protects this probe with a15-second
own-host watchdog and a last-vector report. No production compiler or
camera workflow is changed. Full-chain preceding replay with policy2 and
six matrix perturbations passes88/88, both packing candidates exact.
Evidence: LEGACY_GAMUT_POLICY2_INTEGRATED_CHECK.json. Modern17/full33
policy2 chain validation passes48/48 (nine completed prefix cases plus an
explicit39-case suffix). Full33 integer words match exactly and17-node
packing is byte-exact. A harmless negative RGB subsample before post curves
required the already-validated zero-index opt-in; larger negative values
remain rejected. Evidence: MODERN_GAMUT_POLICY2_INTEGRATED_CHECK.json
(retained partial prefix) and MODERN_GAMUT_POLICY2_SUBSAMPLE_SUFFIX_CHECK.json.

The policy0 bypass also passes88/88 preceding chain cases, packed exactly.
Evidence: LEGACY_GAMUT_POLICY0_INTEGRATED_CHECK.json. Modern policy0 has27
passing cases (nine retained prefix plus18 guarded suffix) and21 unsupported
negative-index cases. The validator now records those domains explicitly,
continues independent cases, and exits unsuccessfully if any are unsupported.
Evidence: MODERN_GAMUT_POLICY0_GUARDED_SUFFIX_CHECK.json. No camera acceptance
claim follows from any of these policy tests.

## Preceding grid header flags

Independent14bd0 sampling now matches44/44 baseline flag0/1/2 cases, including
both10/17 packing candidates byte-for-byte. The boundary path activates when
any index reaches nodes-2; it evaluates two RGB points capped at nodes-3 and
nodes-2, then extrapolates along that shared diagonal. Flag0 uses32/1.1/30.9
and truncation, flag1 uses32/1/31. The two final planes are not independently
extended on each axis. Flag2 on10 nodes retains axis overshoot up to288, not
255; the mistaken clipping hypothesis is retained in the first check report.
Evidence: LEGACY_GRID_FLAGS_0_1_2_FIXED_CHECK.json. Nonlinear verification now
passes341/341 for10/17 nodes and341/341 for9 nodes, including the distinct
nine-node8/5.2/2.8 and8/5/3 branches. Synthetic nine-node grid checks deliberately
make no camera-payload packing claim. Native polynomial factors are multiplied
sequentially, not grouped powers:1008 boundary basis vectors are exact. That
order resolves a one-ULP discrepancy which changed flag0 integer truncation.
Evidence: LEGACY_GRID_FLAGS_NONLINEAR_EXACT_BASIS_CHECK.json,
LEGACY_NINE_GRID_FLAGS_EXACT_BASIS_CHECK.json and
POLYNOMIAL_BASIS_COMPACT_BOUNDARY_EXACT_CHECK.json. Modern policy2 replay also
passes248/248 after the basis-order correction.

The research regression suite previously passed175 tests; the newer pixel
boundary and replay-vector tests are also included in the subsequent run. Public UI,
camera transport, installed Canon binaries and public releases are unchanged.

## Structured PF3 selectors and compact per-pixel branch

PF3 records0x1023/0x102b are bounded variable-length selective group lists,
not merely two policy words. The baseline1,0 means kind1/count0. Native getter
471c0 selects1023 for profile1 and102b for profile2 and copies the actual record
length. Do not edit count without supplying complete groups.

Complete four/five-point H/S/L/combined/target groups affect stock compiler
output without compiler acceptance patches. The modern17 reference passes
24/24 extended cases including final packed payload bytes. Full33 passes8/8
initial cases including final table bytes. Nonempty selectors remain an
explicit experimental reference option; no production behavior changed.

Compact intermediate14bd0 grids stay unchanged by these records. The missing
stage is EdsCFParse475c0 ->46a70, dispatch slotd11fc -> MLib1cab0 ->a7f0.
Read-only captures now persist bounded settings and module-relative callers,
never transient heap addresses. The wrapper splits the selector groups at
splitCount into pre/post lists. Its argument52 is an axis pointer, not a flag.
The preliminary mislabelled capture is retained only as a failed hypothesis.

Unlike the modern grid wrapper, a7f0 uses fixed16.16 polynomial coefficients
directly, without six-decimal truncation. It clamps after the polynomial,
applies preselectors, postRGB curves, optional axes, postselectors, optional
Lab luminance, and final clipping. Both selector stages use33-node geometry.
Its luminance RGB/XYZ matrices are10/11, with floating Lab mode12. Fixed-point
profile calls pass10/11, both resolving to helper profile2; they are not the
modern1->2->1 conversions. The output conversion uses scale256 except camera
IDs80000382 and80000401 which use255, clips at288, and packs octant Y/Cr/Cb.

The independent compact pixel reference passes48/48 complete contexts,
48000 pixels, maximum error1.04e-14, with packed4096-byte blocks matching both
the native packer and decoded final payload. The255-scale branch passes8/8
contexts,8000 pixels, max1.44e-14, and exact final blocks. Evidence:
COMPACT_PIXEL_COMPLETE_END_TO_END_CHECK.json and
COMPACT_PIXEL_5DS_END_TO_END_CHECK.json. Representative M3/1DIII stock paths
never call this wrapper and ignore these two records; no cross-family claim
is inferred.

Nonneutral stock PF3 replay passes8/8 matrix contexts,20/20 nonlinear curve
contexts and24/24 axis contexts, all with exact final packed payload bytes.
The initial axis run had two intermediate precision failures despite exact
final bytes. A bounded stage trace isolated the cause: native divides the
axis adjustment by100 before multiplying by the sector weight. That operation
order restores the exact boundary and fixed-point integer conversion; do not
increase the tolerance to hide the old mismatch. Independent rechecks pass
6622/6622 six-axis samples,24/24 modern17 selective contexts and8/8 full33
selective contexts. Evidence: COMPACT_PIXEL_AXES_EXACT_ORDER_END_TO_END_CHECK.json,
COMPACT_PIXEL_MATRIX_END_TO_END_CHECK.json, COMPACT_PIXEL_CURVES_END_TO_END_CHECK.json,
SIX_AXES_ALL_GROUPS_EXACT_WEIGHT_ORDER_CHECK.json,
MODERN17_SELECTORS_EXACT_AXIS_ORDER_CHECK.json and
FULL33_SELECTORS_EXACT_AXIS_ORDER_CHECK.json.

An own-host direct1cab0 replay validates its ABI first against bounded actual
compiler samples, then independently tests group splitting, null stages,
target-color and nonlinear curves. Combined deterministic random replay passes
7744/7744 samples in42 cases, max error1.15e-14. This explicitly tests split0,
split=count and interior splits with complete group buffers, not malformed
PF3 counts. Evidence: COMPACT_PIXEL_COMBINED_RANDOM_DIRECT_CHECK.json.

The extended direct replay now covers84 cases and15808 requested samples.
With an explicit research-only0.25 in-place margin,15794 safe samples match;
14 inputs would address a negative cached-curve index and are rejected BEFORE
calling the DLL. The default reference margin remains0.05. Unsupported samples
are recorded as unsupported, never counted as passes or silently clipped.
Evidence: COMPACT_PIXEL_MAX_GROUPS_PREFLIGHT_GUARDED_CHECK.json.

Six existing private base-style fixtures (Neutral, Standard, Portrait,
Landscape, Faithful, Fine Detail) have now been compiled on compact, modern17
and full33 routes. For the first five, independent references pass25/25
compact contexts and20/20 modern contexts, including exact final bytes; overall
payloads differ for all five. Standard and Neutral share0x1021/0x1070 but differ
in0x1029/0x1071; full33 also shares its first block but differs in the second.
Do not interpret one shared table as ignored base selection.

Fine Detail uses PF3 base selector0x0088. Its official archived fixture
(SHA-256 126611fb855066506b4752c287d51d2c62f07349679280f7378206f44fc4dd02)
was accepted by the offline Canon compiler on compact, modern17 and full33
representative IDs, producing16752,83076 and431616-byte outputs respectively.
All compact four blocks, all modern five blocks, and both full33 blocks differ
from Neutral. This is compiler-path evidence, not camera acceptance. A second
generated-cache Fine Detail fixture has the same selector and28 records, but15
records differ from the official fixture, including both33³ tables and both
selective-color records; keep the assets distinct pending provenance review.
The generated cache's zeroed empty selector records0x1023/0x102b were changed
in Canon-serialized scratch copies to explicit kind1/count0 headers. Output
hashes stayed identical in all three routes; this only establishes that these
two empty encodings are equivalent in these tests, not that nonempty groups can
be re-encoded arbitrarily.
Evidence: FIVE_BASE_STYLES_COMPACT_END_TO_END_CHECK.json,
FIVE_BASE_STYLES_MODERN_END_TO_END_CHECK.json,
FIVE_BASE_STYLES_FIELD_BLOCK_COMPARISON.json and private
tmp/PF3_FIELD_EXPERIMENTS_20261004/FINE_DETAIL_BASE_STYLE_20261005/.

Expanded the six-style matrix to all nine route representatives. Strict API plus
route-acceptance validation passes44/54 virtual cells. Six failures (Faithful
and Landscape on M3/450D/7DII) return rcGet1 after the 10-node observer sees
only output index1 applied. Four Fine Detail cells (M3/1DIII/450D/7DII) return
rcId7 when setting the target camera ID; a carrier is returned and the observer
recognizes the legacy-direct route, but the target-scoped API gate is false.
These are two different unresolved causes, not proof of physical incompatibility.
All tests use one recorded R8 descriptor. Detail:
private tmp/PF3_FIELD_EXPERIMENTS_20261004/SIX_BASE_STYLES_NINE_ROUTES_20261005/.

Follow-up shows strong descriptor sensitivity in the 10-node branch. For the
M3 ID, substituting the recorded 1300D 7772-byte descriptor for the R8
15076-byte descriptor changed Faithful/Landscape from rcGet1 with only index1
applied to validated output with indices1/2; Standard changed the other way.
With the 1300D descriptor, M3 and 1300D IDs had identical pass/fail states and
identical whole-payload hashes for Neutral, Faithful and Landscape. Neither
fixture is asserted to be the M3's real descriptor.

Four `0x0088` Fine Detail cases returned `rcId7`; changing only record1009 to
Neutral `0x0084` in a Canon-serialized scratch PF3 cleared that error on M3,
1DIII, 450D and 7DII, each producing a validated legacy-direct carrier. This
ties the error to the Fine Detail selector path in these virtual inputs but
does not prove physical style support. Replacing Faithful's 1070/1071 or
1021/1029 with Neutral values did not resolve the M3/R8-descriptor rcGet1.
Reports: `DESCRIPTOR_STYLE_SENSITIVITY.json`,
`FINE_DETAIL_NEUTRAL_SELECTOR_CROSS_IDS.json`,
`FAITHFUL_TABLE_DEPENDENCY_M3.json`, `FAITHFUL_MATRIX_DEPENDENCY_M3.json`.
Fine Detail selector0x0088 was then retried with both R8 and 1300D descriptors.
rcId7 persisted on M3, 1300D, 450D, 1DIII and 7DII; changing only0x1009 to
0x0084 had already cleared it. This supports a style-selector/model-route
capability limit on those virtual inputs, but remains unvalidated physically.
See `FINE_DETAIL_DESCRIPTOR_SENSITIVITY.json`.

A complete54-cell matrix with the recorded 1300D 7772-byte descriptor passes
35 cells. R5 and1DXIII fail all six PF3 styles with rcGet81, although all six
pass with the R8 15076-byte descriptor; the 1300D descriptor is not a viable
proxy for those modern routes. On M3/450D/7DII, Standard fails but
Faithful/Landscape pass, reversing some outcomes from the R8-descriptor sweep.
Thus a borrowed descriptor can flip style results or invalidate a route; only a
descriptor captured from the actual target can test it. Output:
private tmp/PF3_FIELD_EXPERIMENTS_20261004/SIX_BASE_STYLES_NINE_ROUTES_1300D_DESCRIPTOR_20261005/.
Detailed failure trace: R5 applies only 10-node index1 and sees no modern17
builder; 1DXIII takes an `unvalidated-no-grid-conversion` path. rcGet81 is
reported but its exact internal cause remains unknown. See
`MODERN_DESCRIPTOR_ERROR_DETAIL.json`.

All results are private offline compiler mathematics. They do not establish
physical camera acceptance or authorize redistribution of Canon fixtures.

### RP/R8 descriptor and physical evidence cross-check (2026-10-05)

The archived RP descriptor captures (13 files) are all 15,076 bytes with
SHA-256 `2bff34bc3d7cae7d6c65c5e930befe2e0d0920d725ca9fdb18acbb9c8a7aec60`.
The two R8 captures are also 15,076 bytes, but both have SHA-256
`27c7378123643a23c9d21d0ea00cc5ae734dc98415dfd60ec3935fd787665642`.
Comparing one RP and one R8 descriptor: 1,415 bytes differ (9.386%), 13,661
match, and differences occur from the header through offset 13,690. Same byte
length therefore does not mean the descriptor itself is interchangeable.
We have not assigned semantics to the changed bytes; repeated captures across
slots and firmware are required to distinguish model identity from session
state.

Separately, the archived R8 experiment report documents a live R8 ID
`87040080`, slot 1, an 83,076-byte carrier, and changes to PF3 ranges
`0x1f00`, `0x1022`, `0x1f02`; it records `rc=0`, patched outgoing data, and the
user's visual result “The Aerochrome look is correct.” That is one concrete
physical R8 result, alongside the EOS RP evidence; it supports the tested
R8 transaction only and does not make the route universal. The report and
captured binary artifacts remain private and must not be included in a public
release.

### Install-report provenance audit (2026-10-05)

The local generated install reports' `fixtureHashes.descriptor` value is
`649693d61f816ddeda7b1b2ee2ba1421a92d593efe96ed2f9ba218f162b6b3f0`, exactly
the SHA-256 of the bundled 1300D 7,772-byte descriptor fixture. It is not the
live descriptor hash. Those reports identify live camera ID `33040080` and a
15,076-byte descriptor but say `descriptorStored=false`; they do not record
the live descriptor bytes or hash. The `familyStatus` string in those reports
must not be treated as independent physical validation for a 1300D. The
RP-v-R8 descriptor comparison above comes from separate archived capture
fixtures, not this `fixtureHashes` field. This distinction should be
preserved in any future report schema: record `supportFixtureSha256` and
`liveDescriptorSha256` as separate, explicitly named fields, with the latter
only when the descriptor is safely captured.

All five complete local reports are successful transactions with live ID
`33040080`, native/outgoing size 16,752, `rc=0`, `patched=true`, and `0x115`
untouched. They corroborate repeated RP operation only. The R8 report resides
in the sibling workspace archive `../90_ARCHIVE/Research/R8_RESULTS_ANALYSIS_20260905/`,
rather than inside the Git checkout. It was reopened successfully in the
subsequent audit: COMPLETE, slot 1 physical result `correct`, PRIMARY regions
`1f00/1022/1f02`, 42,268 changed carrier bytes, `rc=0`, `patched=true`.

The checked-in standalone manifest's entries `EOS 1300D / 16744`, `EOS RP /
16752`, and `EOS R8 / 83076` are explicitly `offline_validated_transactions`
with `physical_revalidation_required=true`. The alpha.26 release note's 1300D
evidence is a 12-vector compiler-reference matrix. Treat that as offline
compiler validation, not evidence of a 1300D physically accepting an install.
