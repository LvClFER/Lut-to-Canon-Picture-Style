# Compact16752 dispatch regression

The offline `compact16752_plan` joins the independently reconstructed
first-pair descriptor gates, serializer classes6/7 and pixel-scale policy.
Class6 requires explicit evidence that its base-reference second-pair callback
is the verified no-op; unknown reference subclasses are not inferred.
Class7 repeats the descriptor-gated parameterless builder for the second pair.
Integer interpolation remains visible in the plan, not silently converted to
cache or pixel processing; the whole-carrier compositor rejects that
unimplemented route.

Private lab verifier: `verify_compact_dispatch_plan.py`.
Private result: `COMPACT_DISPATCH_PLAN_20261010.json`.
The script verifies original source/payload/descriptor hashes and the static
compiler-revision evidence. Camera model names do not select numerical paths.
Captured grids and payload bytes are comparison targets, not numerical inputs.

Result:36/36 entire16752-byte carriers match (603072 bytes total):

- Class7 / selector0x412: pixel,pixel,pixel,pixel; scale256;12 cases.
- Class6 / selector0x80000289: cache,cache,cache,cache; scale256;12 cases.
- Class6 / selector0x80000382: pixel,pixel,cache,cache; scale255;12 cases.

Scope: retained normal base-reference PF3s and the retained borrowed descriptor.
This does not establish arbitrary-LUT acceptance, all descriptor combinations,
all reference subclasses, installation authorization or physical camera support.
No DLL execution, camera access, installed DLL modification or production UI
change was required. Older8528/16720/16744 headers and other serializer classes
remain separate reconstruction work.

## Older prefix follow-up

`verify_older_compact_headers.py` reconstructed36/36 archived prefixes from
source records, without copying prefix bytes from comparison carriers.
Sizes8528/16720 remove the32-byte Basic/markers/detail region at76..107
from the368-byte compact prefix, leaving336 bytes and envelope marker0x28
at76. Size16744 removes detail100..107, leaving360 bytes and marker0x40
at100. The duplicated size fields are updated to total minus40.
Static disassembly of known-hash serializer branches54fd6/5513c/553a1
shows envelope stores at76/76/100 respectively (constants28/28/40).
The retained vectors require complete controls through the reused constructor;
this proof does not establish missing-control defaults, all styles, whole
older carriers or arbitrary-LUT preservation. The production exporter is unchanged.

Subsequent whole-carrier test supersedes the header-only limitation above:
all36 older carriers match with source-derived compact caches, alternating
seeds0xb8ed/0x33137 and the previously established selector/coefficients.
There are two blocks for8528 and four for16720/16744. Captured numerical grids
are not inputs. This proves the explicit cache-copy hypothesis for retained
vectors, NOT automatic body dispatch for all descriptor combinations.
`build_older_compact_prefix` now exposes the checked layout in the offline
reference; the verifier cross-checks it against an independent construction.
The12 vectors per layout and all510 unit tests pass. Production registration
and exporter behavior remain unchanged.

## Older serializer topology

`extract_older_compact_dispatch.py` now hash-gates the DLL, extracts aligned
instructions from54cd0, checks18 specific instructions and verifies class3/4/5
jump-table targets54fd6/5513c/553a1. Class3 reads1022/102a directly and has no
derived processing calls in its serializer branch. Class4 preloads four cache
blocks, invokes4c610/4c770 and overwrites only the first pair. Class5 likewise
processes the first pair but invokes virtual slot38 twice for the second pair;
its callback subclass cannot be inferred merely from matching output bytes.

`older_compact_plan` captures that topology and requires explicit no-op callback
evidence for class5. It preserves integer paths instead of quietly treating
them as pixel/cache. Synthetic tests verify bypass of first-pair gates for
class3, first-pair-only processing for class4, and rejection of missing class5
callback evidence.511 tests passed. Whole-carrier automatic-plan validation
and class5 dynamic callback observation are still pending; the36 whole matches
above used an explicit cache-copy hypothesis.

The subsequent owned offline class5 observation resolves that pending callback
for the retained normal base reference: calls556c1 and556f3 both dispatch through
vtablebf0d4 to53250 (verified no-op). Identity output matched the archived hash.
Owned hidden hostPID9232 was cleaned in the driver's finally block; no EDSDK
or camera APIs were used. Observation is inCOMPACT_M3_OBSERVATION_20261010.json.
The older verifier now computes class3/4/5 plans from static family rules and
the normalized descriptor, requires all selected paths to be cache, and
reconstructs36/36 whole carriers exactly. Callback observation provenance is
hash-linked in its result. No model-name switch selects body processing.
This still covers only the retained normal reference subclass/descriptors;
other styles, changed gates and reference subclasses remain open.

## Six-base regression found a genuine gap

`verify_compact_dispatch_plan.py --five-bases` reproduces all five traditional
base carriers exactly on the retained class7 route. `--six-bases` explicitly
checks the selector set81/82/83/84/85/88 and FAILS:5/6 whole carriers match;
Fine Detail88 differs in6178 bytes. The result is preserved in
COMPACT_SIX_BASE_DISPATCH_PLAN_20261010.json with region-level differences.
This negative regression must not be relabeled as a passing six-style proof.
Next investigate Fine Detail descriptor-grid preparation and source metadata,
comparing initialized native intermediates rather than modifying packed bytes
to make the comparison pass. The general511 unit tests still pass but do not
cover this native equivalence gap. No production behavior changed.

Fresh Fine Detail isolated observations changed the next diagnostic action:
same source and descriptor hashes, known DLL revision, unchanged compile,
but output differs from the earlier Fine Detail archive. Owned hosts28568
and12692 were both cleaned. The second run retained full diagnostic metadata
inCOMPACT_M50_FINE_DETAIL_OBSERVATION_20261010.json and intentionally returned
failure for archive mismatch. Do not silently replace that expected carrier.
`compare_fine_detail_arguments.py` compares the first two initialized14bd0
calls: all descriptor arguments and numeric modes match the portable reference.
Remaining questions: old fixture generation provenance, process state/order,
and comparison of fresh packed outputs with the portable result. The initial
6178-byte mismatch is not yet evidence of a mathematical defect.

Fresh-stage comparison now proves the portable Fine Detail carrier matches
the fresh native whole-output SHA2567b2150189e11a5ee8b99bf977646eb91b0b87a37156e478cb36b967baa323a3e.
The four observed49e00 blocks, with the independently verified header, rebuild
that exact whole hash. Old expected hash remains9d4650946a724ca34ad78fcb548b4ccec46b25553a2bc10a2ff4e45dd6ab02e5;
the old archive is retained, not silently overwritten. A second isolated
compile without the MLib observer was run in ownedPID10772 and cleaned; its
result is retained separately. This control separates observer effects from
unresolved historical compilation provenance/state. No production changes.

Sequential control in ownedPID19676 (cleaned) compiled all five traditional
styles then Fine Detail twice, without MLib observation. All five traditional
outputs equal historical hashes; both Fine Detail outputs equal the fresh
portable hash7b2150... and not the old9d4650... hash. Thus simple same-process
style order and MLib observer initialization are excluded for this sequence.
`COMPACT_STYLE_ORDER_20261010.json` retains each source/output hash. The argument
comparison verifier now hash-links both controls and requires these independent
fresh checks to pass. The old carrier remains an unresolved historical fixture,
not a reason to alter otherwise exact portable math. Next compare historical
generation code/descriptor application and extend fresh controls to other
families; neither universal support nor a complete independent compiler is proven.

## Expanded style gates and lab interruption

Hybrid selector80000382 fresh sequential run printed seven exact portable/native
hash comparisons (six bases plus repeated Fine Detail). Driver cleanup then
stalled; its tool session was interrupted. A scoped elevated CIM audit confirmed
neither owned hostPID14784 nor the matching Python driver remained. The final
JSON was not reached, so console observations are not promoted to a completed
persisted regression. Driver now checkpoints each row withcomplete=false and
setscomplete=true only after cleanup. Historical comparisons across different
selectors are nownull rather than misleadingfalse.

The attempted80000289 run stopped during pure prediction before spawning:
Standard selects integer/integer, Landscape integer/cache, Faithful integer/cache;
Portrait and Neutral select cache/cache. Fine Detail has the independently
known early rejection. The missing integer compositor is therefore now tied
to concrete non-Neutral styles, not a hypothetical unused branch.
`inventory_compact_style_gates.py` records18 style/selector combinations.
These gates use a borrowed R8 descriptor, including a compact-prefix reader of
that normalized modern store; this is not a valid native descriptor assertion
for those bodies and does not establish physical availability of the branches.
Next obtain/read-only observe the exact compact reader arguments and integer
grid intermediate for one selected Standard branch before adding composition.

Standard was freshly observed with the actual archived compact1300D descriptor
and selector80000289 in owned hiddenPID15628, cleaned by finally. This is still
a borrowed descriptor experiment, not a physical-body assertion. One4a3b0
integer conversion occurs. `verify_standard_integer_capture.py` proves its
3000-component table is the source-derived1070 cache (not captured table input),
then independently reproduces all output integers and the linked49e00 bytes.
The converter's input float grid remains captured, so whole independent replay
is still incomplete. The experiment originally compared against a donor
M50/R8 carrier and reportedfalse; that comparison is inapplicable because the
selector/descriptor changed. Driver now recordsnull for this new experiment.
The native observation remains retained unchanged as a diagnostic artifact.

Static tracing48d10 resolves the compact reader: matrix offset104 + ordinal*5d8
+ index*f0, parameter block offset2d0 + ordinal*5d8 + index*104; expands eight
four-point groups to32-bit words. Unlike modern descriptor processing, it calls
469f0, whose pointerd11d0 binds via46881/46894 toMLIBcalcLuckyEx (MLib export1b610),
then internalb280. It is NOT the modern14bd0 argument interface. Both binaries
were verified against known hashes before static disassembly.
`probe_compact_legacy_grid.py` tested reusing the modern selective-block paths;
those candidates are rejected by geometry guards. This is useful negative
evidence: do not force the compact block throughmodern_grid_arguments or bypass
the kind/count checks. Next decodeMLIBcalcLuckyEx/b280's legacy block semantics.

A useful compact-kind0 breakthrough: b280 checks block kind==0 atb7be and
callsfa40 atb7d2; fa40's non-kind2 branchff3f calls the sameff60 selective
group helper. The kind0 groups are applied AFTER the polynomial/post stage,
not as modern pre-groups. A laboratory-only semantic adaptation to the
existing selective math reproduces the captured Standard mode1 input grid
with maxError0 across3000 components. The pre-group candidate fails; mode2
candidates do not match that mode1 capture and are retained as negatives.

Source-derived grid + original1070 table conversion + cache mode2/pair + source
header produces the whole16752-byte SHA256d4294ac0fbc7045bc3962bb72cb0f23cbf4f64a9ffbb873a7258c4720f665cff,
exactly equal to the fresh native output. No captured grid/table bytes are
numerical inputs to this whole-carrier hypothesis. Source/descriptor files are
hash-checked, and native intermediates are comparison targets only. The result
is inCOMPACT_LEGACY_GRID_HYPOTHESES_20261010.json. This is one Standard vector;
the kind adaptation remains laboratory-only pending dedicated typed decoding,
static instruction assertions and more styles/vectors. Do not generalize the
modern public block decoder or claim a complete independent compiler yet.

The semantic adaptation is now isolated incompact_legacy_grid_reference:
strict7492-byte normalized input, five observed styles, indices1/2, native
kind0 only, at most8 groups, signed16→32 expansion. It returns both semantic
arguments and ORIGINAL native block; no input bytes are rewritten. Synthetic
tests check kind separation, signed values and rejection of unsupported input.

`verify_compact_legacy_styles.py` independently reconstructs all four table
blocks for10 archived vectors (five styles × two selectors), all exact, using
only original PF3/descriptor numerical inputs. Important provenance correction:
PRIVATE_GEOMETRY_MATRIX_RESULTS contains ALTERNATE00FF0001 outputs16728/16744,
NOT normal01000203 carriers16744/16752. Initial whole-header comparison failed;
the verifier now explicitly identifies outputProperty00ff0001, compares only
the16384-byte bodies at344/360, and does not build or validate alternate headers.
Do not merge those geometries into camera transport. Normal Standard whole
proof above remains separate. Next expand the NORMAL carrier compositor's
integer path with this typed compact reader, preserving descriptor-kind and
callback preconditions.513 unit tests pass.

### Explicit normal compact integer compositor

Added research-only `build_observed_compact16752_integer`: requires an explicit
normalized compact7492 store, established coefficient/reader policy, traditional
style and integer/cache first pair with cached second pair. It does not select
a route from model name or store length and does not support alternate headers.
Caller still establishes class6/base callback provenance independently.
The integrated implementation matches the independent Standard normal assembly
and the fresh native whole SHA256
`d4294ac0fbc7045bc3962bb72cb0f23cbf4f64a9ffbb873a7258c4720f665cff`.
514 unit tests pass. No camera access, DLL execution or production path change.
Remaining: fresh normal multi-style integer vectors and static binding assertions;
the alternate ten-vector body evidence cannot substitute for normal headers.

### Static compact-reader binding proof

`extract_compact_legacy_binding.py` reads known-hash DLL images without loading
them and asserts24 instructions plus the LuckyEx string/export. It links48d10
compact reading (matrix104, kind2d0/count2d2, stride5d8, four-point expansion,
unsigned tags/signed values, 10-node flag1) through469f0/d11d0 toMLib1b610/b280.
The kind0 gate callsfa40, whose non-kind2 branch reachesff60. This supplies
reproducible static provenance for the semantic group adaptation, independently
of the numerical matches. It proves this revision only; it does not establish
camera registration, descriptor acquisition or other DLL revisions.

### Fresh normal compact five-style comparison

Owned compile-only hidden host3956, unchanged known-hash compiler/MLib, noMLib
observer, noEDSDK: five traditional source styles plus repeatedStandard all
match the portable normal16752 compositor whole SHA256. Persisted report
`COMPACT_LEGACY_NORMAL_FIVE_STYLES_20261010.json` has complete=true.
Inputs explicitly combine selector80000289 with the archived compact1300D
descriptor hash649693d6…; this is a borrowed-descriptor virtual experiment,
NOT physical7DII/1300D support. Actual gates differ from borrowedmodern-prefix
inventory: Neutral cache/cache; Faithful/Landscape/Portrait integer/integer;
Standard integer/cache, all with cached second pair.
Cleanup blocked in Frida unload until the owned host was externally terminated
after exact PID/name/hidden-command verification. Driver then exited0, marked
complete and host absence was verified. No camera process was touched.

### Normal compact integer route with modified LUTs —20261011

Extended owned offline driver with explicit in-memory EdsCfp114 style override
(81/82/83/85), leaving all original source files unchanged. Portable input
changes only corresponding host1009 style value; numerical LUT inputs remain
original12-vector identity/gains/swap/gray/local/Superia/Aerochrome corpus.
Borrowed compact1300D descriptor and selector80000289 remain explicit.
All48 unique style/LUT combinations match complete native16752 SHA256; final
Aerochrome repetition for each style also exact (52/52 total observations).
Standard paths integer/cache/cache/cache; Portrait/Landscape/Faithful paths
integer/integer/cache/cache. Every report has complete=true, native return
statuses, callback evidence and source/archive/descriptor hashes. This proves
numerical normal compiler behavior for these inputs, not physical installation
or a general arbitrary-LUT acceptance policy across all compiler families.
Reports COMPACT_LEGACY_NORMAL_LUTS_0x81/82/83/85_20261011.json.
Owned hidden hosts5936/3112/23568/1856 were destroyed; cleanup now kills its
owned process before Frida teardown, avoiding the earlier unload stall.
532 tests,py_compile andnode --check pass. No EDSDK/camera/production changes.

### Shared old compact integer composition —20261011

Generalized research-only integer compositor to explicit normal sizes8528,
16720,16744,16752. Existing16752 entry point delegates unchanged. Class3
geometry accepts ONLY direct cached pair; class4/5/6 accept explicit first
integer/cache pair and cached second pair. No size-based family selection;
caller still establishes class and callback evidence. Alternate sizes rejected.
Fresh borrowedcompact-descriptor comparisons,12 LUT vectors plus repeated
Aerochrome: class3 selector80000169 Standard13/13; class4 selector80000176
Standard13/13 andPortrait13/13; class5 selector03740000 Standard13/13 and
Portrait13/13. All65 observations match whole native output SHA256, covering
60 unique selector/style/LUT combinations. Callback reports retained.
Five hosts11244/20120/2740/3108/9028 cleaned; all reports complete=true.
533 tests andpy_compile pass. This is offline exact compiler equivalence for
borrowed inputs, NOT physical support or an independent installation proof.

### Automatic actual-compact-store dispatch —20261011

`compact_store_plan` now selects explicit class3..6 body topology from a
normalized compact7492 store, style/capability words, reader policy, object
flag and independently supplied callback evidence. It differs deliberately
from the existing modern-store-prefix planner: no padding or renormalization.
Rejects class1/2/7+, FineDetail, wrong store geometry, noncompact reader policy
and missing class5/6 callback evidence. It is not a model-support registry.
`verify_compact_store_dispatch.py` rebuilds117 complete outputs from original
12 source vectors and nine retained native runs; all117 whole sizes/SHA256
match. It re-extracts classifier rules from hash-known DLL, validates native
return statuses, checks callback target53250, source/report/descriptor hashes
and explicitly reproduces experimental in-memory style overrides.
No native code executed by this verifier; no captured numerical grids used.
534 tests andpy_compile pass. Classes1/2 still require unresolved genuine1007;
that boundary was not weakened to obtain more green cases.
