# Normal compact source replay — 2026-10-10

## Application-generated empty axes,2026-10-16

The source decoder now accepts the exact owned padded axis form
`kind2/count0 +504 zero bytes` as well as canonical six-group axes. This retains
a nonnull axis block rather than replacing it with a null optional stage.
The pixel evaluator skips axis adjustments for count0 but preserves both mode1
24-bit color round trips. Mode2 takes the helper's unchanged-RGB branch.

Read-only hash-gated instruction proof is retained in
`EMPTY_AXIS_PIXEL_STATIC_PROOF_20261016.json`:11 assertions show fa40's initial
RGB copy, count test and direct return;10 assertions show the pixel caller
branches on pointer presence/mode, not group count. No DLL was loaded/executed.
The verifier is `verify_empty_axis_pixel_static_20261016.py` in the private lab.
This is static attribution, not a new native empty-axis numerical capture.

Tests check actual round-trip arithmetic, preserve the distinction from null
axes, reject nonzero padding/truncated records, and compile an owned generated
PF3. The complete bundle test now exercises both explicit cache and dense/pixel
routes through the real marshalling/session code with fake COM, including
opaque state, UI lock/unlock and requestedD171 content comparison. No real
camera operation, route auto-selection or write authorization is implied.

## Independent dense10 override replay,2026-10-16

`build_accepted_compact16752` now reproduces all12 whole carriers from the
archived `RP_LEGACY_GATE_12_VECTOR_VALIDATION.json` experiment. The first pair
uses source1070/1071 -> flag1 dense10 sampling -> existing source-derived pixel
processing -> normal integer packing/encryption. The second pair retains the
normal parameterless pixel construction. No table pair is swapped. Exact
16752-byte digests match identity, gains, channel swap, gray, local changes,
Superia and Aerochrome. This is a different route from the previous all-cache
experimental candidate.

Private reproducible verifier `verify_rp_dense_pixel_20261016.py` hashes sources
against retained RP dense trace metadata, checks the genuine descriptor hash,
recovers equivalent keys from an owned generated PF3, forbids EdsCFParse loading
and compares only against the historical output digests. Its report is
`RP_DENSE_PIXEL_SOURCE_PROOF_20261016.json`:12/12 exact. No captured output
bytes or numerical intermediates enter compilation.

The pure offline planner accepts this explicitly named
`compact16752-dense-pixel` route only with an explicit normalized14796-byte
descriptor and checked pixel policy. It does not negotiate routes or enable
physical access. The physical Err70 guards and editor fallback remain intact.
Synthetic integration confirms a1070-only change affects only the first user
block and reaches a slot3/9110 packet plan.

At that checkpoint, the existing pixel settings decoder accepted only
canonical six-group source axes. Application-generated empty kind2 axis records
were still rejected. The follow-up above attributes and implements their
zero-count processing; the twelve historical vectors alone do not cover it.
No new physical acceptance,
fresh-state or build-release claim follows from the archived digest matches.

## Actual RP registration corpus follow-up,2026-10-16

`compare_rp_archived_pixel_route_20261016.py` and private report
`RP_ARCHIVED_PIXEL_ROUTE_WIRE_VERIFIED_20261016.json` expand the source-only
comparison to the original V25 registration corpus using its genuine RP
descriptor, hash-checked before normalization. Keys are recovered in memory from
an owned generated PF3; Canon discovery/loading is forbidden during evaluation.

The archived Standard Emerald source uses kind2 axis counts8/7 (680/596 bytes)
for its first pair. The existing count-driven circular math reproduces both
complete packed blocks exactly; all four4096-byte blocks match registration3.
The typed research evaluator now accepts these two observed counts under its
existing experimental-geometry opt-in, retaining exact length/header/tag/bounds
validation. Tests cover circular first/last neighbors, neutral arithmetic,
missing opt-in, truncated/oversized blocks and mismatched counts.

Original Superia also reproduces all four blocks in its attributed registration5.
Both source-derived complete9110 data packets match the actual archived WPD
input hashes exactly. Neutral control additionally matches registration1, whose
source attribution was not recorded; coincident bytes do not prove attribution.
The desktop carrier differs only in its external caption bytes8..39: native
caller captions are zero-padded while the source record preserves trailing
bytes. These bytes are excluded by the independently verified send serializer;
the inner name and all actual transmitted bytes match without any patch-up.

This proves normal parameter-based compilation and framing for these archived
inputs. It does not make the normal pixel branch consume arbitrary dense1070/71
tables, establish fresh state, or authorize a new camera session/write.

Offline verifier: `../tmp/PF3_FIELD_EXPERIMENTS_20261004/verify_rp_compact_source.py`.
Report: `RP_COMPACT_SOURCE_PROOF_20261009.json` in the same laboratory folder.
Source, descriptor and archived output hashes are checked against the retained
original experiment metadata. Captured grids are comparison targets only.
No Canon DLL execution, camera access or production-path changes.

The actual RP descriptor contains a six-sector lower hue bound of -10 degrees.
The existing circular helper already handles that interval; its decoder guard
incorrectly rejected signed lower bounds. The guard now permits one negative
turn and a test compares -10 with the equivalent wrapped 350-degree interval.

Results for one normal identity-source 16752-byte carrier:

- Source-derived 368-byte prefix: exact.
- Blocks 0, 2 and 3: exact, zero differing bytes in each 4096-byte block.
- Block 0 upstream floating grid maximum error: 2.842170943040401e-14.
- Parameterless upstream grids for blocks 2 and 3: exact.
- Block 1 remains unsupported: the descriptor supplies a 260-byte kind-2
  three-group axis block, whereas existing reference dispatch supports only
  two-group global or six-group processing. Do not substitute either shape.

Next: trace the kind-2 three-group dispatch and combination semantics before
implementing it. Whole-carrier equivalence is not established. This normal
compiler control is not proof of arbitrary-LUT acceptance or physical support.

Verification: py_compile passed; complete unittest discovery passed 492 tests.

## Three-group follow-up

Static fa40 consumer inspection confirms count-driven circular neighbors:
fb5d/fb66 choose previous index (count-1 at index zero); fb7b/fb86/fb8f
choose next index (zero at final group); fbb6 calls the same 10a00 helper.
The hash-gated `extract_axis_consumer.py` now asserts those instructions.
The research geometry reference accepts the observed count 3 as well as 6,
requires the exact header/length and retains per-group layout/range checks.
Legacy grid opt-in dispatch now recognizes the corresponding 260-byte block.

Rerunning the source-only verifier reproduces **all four blocks and the entire
16752-byte archived normal control exactly**. Block 1 upstream floating grid
also matches exactly. Block 0 retains only the stated sub-quantization floating
residual; its packed bytes remain exact. No captured pixel values are inputs.
This supersedes the unsupported-block result above, not its scope limits.
Added three-group neutral arithmetic and truncated/oversized-layout tests.

## Reusable reference extraction

`camera_install/compact_carrier_reference.py` now exposes an explicitly named
pixel-route reconstruction, separate from route selection and the alternate
integer-grid path. It takes typed host-order source records, normalized modern
descriptor bytes and caller-supplied cipher keys. No archive reads or captured
pixel inputs occur in the module. The external verifier independently checks
its complete output against the retained 16752-byte payload: exact.

Boundary tests reject wrong descriptor lengths, invalid block indices and
unknown style selectors, including the parameterless pair. Complete unittest
discovery: 495 passed; py_compile passed. Production registration is unchanged.
Cipher keys are still obtained by the external laboratory verifier from the
installed DLL; this extraction does not establish a redistributable key source
or a fully dependency-free application.

Next scope expansion must preserve the dispatch distinction: the retained
36-vector compact-prefix archive includes other camera policies, so its exact
headers alone do not justify using this pixel builder for all of its bodies.

## Cross-route counterexamples

`verify_compact_pixel_candidates.py` checks hashes and compares identity and
Aerochrome sources from PACK10_ALL_VECTORS_TRACE using that archive's borrowed
R8 descriptor. It tries explicitly supplied pixel scales 255 and 256, not an
automatic camera rule. All twelve comparisons are retained in
COMPACT_PIXEL_CANDIDATES_20261010.json, including failures.

- M50/Kiss M: both complete carriers exact at256; at255 both differ4141 bytes.
- 7D II: identity differs6102/4910 bytes at255/256; Aerochrome15262/15246.
- 5DS: identity differs3091/4074 bytes; Aerochrome7633/9666.

The M50 result does not prove native arbitrary-LUT acceptance: both source
files produce the same result under this normal pixel-route reconstruction.
The 7D II policy belongs to the known coefficient-policy set; 5DS does not.
Therefore coefficient-policy membership alone cannot explain both failures,
and changing only pixel normalization is explicitly falsified for these
archived cases. Need inspect object flag and alternate/native call provenance
before selecting another builder. These archives capture float packers, not
enough upstream stages to infer the complete route solely from their absence.

No camera access or Canon DLL execution. 496 unit tests and py_compile pass.

## Float-output attribution across 72 archived sources

`attribute_compact_archive.py` checks source/payload hashes, independently
recalculates all144 retained 4b760 float packer outputs and searches complete
decoded blocks under both known cipher seeds. Results are retained in
COMPACT_ARCHIVE_ATTRIBUTION_20261010.json, including unmatched outputs.

- M50: neither retained float output appears intact in any final block,
  across12 sources. This is consistent with its exact pixel reconstruction,
  not evidence of missing or failed compilation.
- 5DS: first/second float outputs match only final blocks2/3 respectively,
  offsets8560/12656, seedsb8ed/33137, across12 sources.
- 7D II: first float output matches blocks0/2, second matches1/3, all12.
- M3 and450D also duplicate the corresponding outputs across both pairs.
- 1D III8528 layout contains each corresponding output once.

All144 float outputs themselves reproduce exactly;120 have at least one
complete decoded final-block match. Membership in the coefficient-policy set
correlates with the captured float coefficient choice in these six cases,
but this does NOT establish the upstream object-byte flag or dispatch.
In particular, the 5DS intact user pair versus M50 transformed pair explains
why applying a common pixel post-stage to all four blocks is insufficient.
Next isolate source-table fallback and first-pair integer composition; retain
the archive's borrowed-descriptor limitation throughout.

## Source-table presence check

The attribution verifier now inventories original compact records before
attempting any direct-copy comparison. Important correction to the next
hypothesis: these12 source vectors have NO1022/102a/1f00/1f01/1f02 records.
The source contains dense1070/1071 and curve/matrix/axis records instead.
Across72 archive entries there are therefore zero compact source candidates,
not72 failed byte comparisons. Any compact records observed inside the native
compiler must be synthesized/default-initialized, not copied from these PF3s.
The missing-record count is explicitly retained to prevent interpreting an
empty match list as evidence that a candidate transformation was tested.
Next trace creation/population of the compiler's compact cache and eligibility
flags. No production code or installed binaries were changed in this step.

## Compact decoder semantics

Read-only hash-gated `extract_compact_cache.py` retains function-entry windows
46f50,4a5e0,4c770,4d660 in COMPACT_CACHE_STATIC_20261010.json.
46f50 chooses1022 for mode1,102a otherwise and requests4096 bytes through
46de0. This describes retrieval, not the missing source records' producer.
4a5e0 extracts Y from bits20..29, Cr0..9, Cb10..19. Chromatic bit9 is sign
extended via ORfffffc00 and conditional moves. Output planes are Y,Cr,Cb.
The extractor asserts the signed operations and output offsets.

`packed10_reference.unpack10_integer` independently implements the octant
layout and signed channels. Tests cover all1000 grid locations, signed
boundaries-512/-1/0/1/511, ignored padding/high bits, strict input geometry.
499 unittest cases and py_compile pass. No native execution or camera access.
This decoder is statically grounded plus synthetic round-trip tested; it is
not yet a complete source-derived alternate-route carrier reconstruction.

## Partial integer-stage hypothesis — falsified as common route

`verify_compact_integer_stage.py` uses each retained float packer's output
as an explicitly declared intermediate INPUT, independently decodes its signed
channels, computes the first-pair grid from the borrowed descriptor and applies
the known integer tetrahedral converter with the camera coefficient policy.
It compares each predicted first-pair block to the decoded final output.
COMPACT_INTEGER_STAGE_20261010.json retains all72 comparisons: none exact.
Identity differences for blocks0/1: M50 277/1999 bytes,7DII907/952,
5DS1161/2073. These are partial hypotheses, not source-derived proofs.

Static extraction of the intervening helper4c340 proves it is just `ret0xc`
in the hash-verified revision. Thus a numerical adjustment hidden in that
particular call does not explain these divergences. The extractor now checks
that exact single-instruction body. Remaining alternatives include bypassing
grid composition at the descriptor gate, selecting a different internal
table than the retained float packer output, or different upstream dispatch.
Do not infer that4a3b0 executes merely because it is a possible static branch.

## Descriptor-disabled fallback

Extended static windows now include the complete normal success path and
fallback blocks. Both4c770 and4d660 test4b4f0 first. When disabled, they retrieve
1022/102a via46f50; on failure they call the object's first virtual function,
then retry. If retrieval succeeds, they pass4096 bytes to4a2b0 targeting
1f00/1f01. If the second retrieval fails, that iteration is skipped rather
than executing the pixel/integer branch. This is a separate fallback path,
not a numerical identity of those processing algorithms.

Hash-gated assertions retain both branch targets, retry calls and destination
record selection. `compact_builder_path` represents only the static precedence
of descriptor gate, coefficient policy and object byte. It neither predicts
the gate from model name nor reads camera state. Truth-table/type tests added;
500 unit tests and py_compile pass. The virtual initializer and4a120 storage
semantics remain to be independently traced before source-only fallback replay.

## Virtual initializer to compact-cache producer

Known vtable slot0 links are now hash-gated in the cache extractor:
bb5e4 ->494d0 (base), bc544 ->4cd00 (derived). These agree with the earlier
constructor/vtable observations; no new class identity is inferred.
In the derived10-node branch, instructions establish this dataflow:

46fd0(mode,source pointer) ->46a50(source,0,mode,grid) ->4b760(grid,packed)
->4a2b0(record1022 for mode1 /102a for mode2,4096 bytes,mode0).

The writer uses the SAME1022/102a selection formula as46f50's later reader.
Both virtual initializers have the float packer then1022/102a writer sequence.
Derived initialization additionally has distinct9-node and17-node branches;
do not apply its10-node sequence indiscriminately. Assertions retain the
derived source/converter/packer/writer call sites and destination calculation.

This closes the static missing-source-record provenance gap: these records can
be synthesized by virtual initialization before fallback retrieval. It does not
prove which initialization branch each archived compile executed, the exact
source returned by46fd0, or46a50 equivalence. Existing typed-record reference
already covers4a120 copying; no second copy implementation was added.

## Source-derived cache conversion:144/144 explained with explicit flags

46fd0's function-entry window selects1070 for mode1 and1071 otherwise,
allocates the stored record size and copies it with byte-order mode0.
46a50 is an indirect trampoline throughd11e0, not the converter body itself.
Previous MLib observations identify the dense converter; this static window
alone does not resolve the runtime pointer.

`verify_compact_cache_source.py` parses/hash-checks the original12 PF3 vectors
across six archived routes and computes dense33 ->compact_flag1 ->pack10.
It uses each observed coefficient choice as an explicit discrete input;
captured numerical grids/tables are comparison targets only.
120/144 packed caches match exactly. The24 remaining1DIII cases all match
compact_flag0 ->pack10 EXACTLY, including every floating input component
(maximum error0). Thus144/144 packed caches are reproduced with explicit
flag1/flag0 hypotheses, but automatic selection of that flag is not yet proven.
Full evidence, including initial flag1 failures, remains in
COMPACT_CACHE_SOURCE_20261010.json. Syntax checks pass. No new native execution.

This expands source-derived mathematics, not complete carrier support: final
descriptor composition, headers for other sizes and physical registration
remain separate obligations. Next derive initializer flag selection from the
static dispatch and connect the matching cache to the fallback reconstruction.

## Derived10-node flag lookup

470b0 reads internal record1001, defaulting its local value to zero before
lookup/copy. Within the derived10-node branch,4ce94 bounds the selector bycd,
4ce9c indexes the206-byte table4d080, and4cea3 uses jump table4d078:
tag0 ->4ceaa sets flag0; tag1 ->4ceae sets flag1. Out-of-range usesflag1.
Static extraction yields flag0 selectors0,39,170,172,201,203,205.
Both jump targets, the table hash and all206 tags are checked in the extractor.

`derived_compact_grid_flag` independently represents that lookup, with tests
over every table index, the upper boundary and invalid types/ranges. Important:
its input is INTERNAL1001, not a blindly substituted public camera ID. The
raw public1DIII ID80000169 would select1 here, whereas its archive numerically
matches0. Thus resolving public-ID normalization/context initialization is
still required; the numerical matches do not yet prove that selector mapping.
The function also does not select preceding9-node/17-node special branches.
501 unittest cases and py_compile pass; static checks pass, no DLL execution.

## ID-storage cross-check: no demonstrated normalization

The preceding proposed normalization is NOT established. In the public PF3
setter572d0,57360/57361/57364 pass the original input pointer/size and1001
to51500;57378/5737c also copy the original first dword into object+8.
`extract_base_alias_gate.py` now asserts those exact instructions and retains
them in BASE_ALIAS_PREPARATION_GATE_20261007.json. No arithmetic mapping is
present in that bounded storage sequence.57110 subsequently initializes absent
style records; its known common/legacy lists do not include1001.

Therefore do not invent a public1DIII->internal170 mapping to explain the
flag0 numerical match. Other initialization contexts, record storage semantics,
the base versus derived initializer, and numerical-path equivalence remain
possible explanations. This corrects the previous next-step wording:
resolve actual context/record provenance before claiming ID normalization.
The source-only144-cache arithmetic result remains valid with explicit flags;
automatic route selection remains unproved.

## Export binding: compiler46a50 ->MLib196a0

`extract_converter_binding.py` reads only the two hash-verified PE files.
It first inventories references tod11e0 using a section-linear skipdata scan,
then asserts the actual binding sequence from known468bf instruction entry:
push nameba738 (`MLIBcalcLuckyFromFileLUT`), call resolveresi at468cf,
store returned pointer tod11e0 at468dc. A unique bounded loader assignment
setsesi from the imported GetProcAddress address. Export-name lookup in the
known MLib identifies1c950, NOT a direct export at196a0.

Decoding from that confirmed export entry retains its complete wrapper through
ret1caae; call1ca9a targets196a0. The wrapper reads bit depth/channel/node words,
allocates a12-byte header followed by float64 samples, normalizes source words
by(2^bitDepth-1), then forwards the converted source and destination arguments.
For the validated12-bit sources this agrees with the existing /4095 decoder.
CONVERTER_BINDING_20261010.json retains hashes, resolver origin, pointer windows,
export identity and complete wrapper instructions. Static assertions and
py_compile pass. No DLL loading, function invocation or device operations.

This closes the previously unresolved indirect-call binding for the known
revision. It does not resolve the automaticflag0 discrepancy or prove execution
of any particular initializer in the archived1DIII case.

## Portable compact-cache reference

`camera_install/compact_cache_reference.py` now consolidates strict host-order
12-bit33-record decoding, null-curve flag0/flag1 conversion and compact packing.
It accepts ONLY explicit grid and coefficient policies; no model discovery,
camera transport, DLL execution or cipher keys are present in this module.
Existing math/packing helpers are reused rather than duplicated.

The external144-case verifier separately checks the reusable implementation
against both the previous mathematical expression and archived native bytes.
All144 reusable outputs match with the explicitly tested flag alternatives.
Originalflag1 failures remain visible; choosingflag0 after comparison is an
experimental hypothesis, not automatic dispatch. The verifier now fails on
any unexplained case and records the archive hash in addition to checking each
source hash. Tests cover both policies, zero-source bytes, malformed source,
unknown flags and bool/int confusion.503 tests and py_compile pass.

PF3 archive decoding in the lab still obtains cipher tables from the installed
Canon DLL; the numerical module's independence must not be described as a fully
Canon-independent application or a complete camera registration implementation.

## All twelve archived M50 pixel carriers

The explicit scale256 pixel reference reproduces all twelve retained M50
16752-byte carriers in full, including prefix and four encoded blocks.
COMPACT_PIXEL_M50_ALL_20261010.json retains source, payload, descriptor and
color-body hashes. The descriptor is still the explicitly borrowed R8 archive
descriptor, not independently captured M50 geometry.

Crucially, twelve distinct dense1070/1071 source hashes produce ONE identical
color-body hash after offset368. Whole-carrier differences are in the prefix.
This validates reproduction of the normal compiler pixel path, NOT arbitrary
LUT acceptance or physical M50 installation. The result reinforces why merely
matching the normal native output is insufficient for preserving custom LUTs.
The verifier passes py_compile; no DLL execution or camera access occurred.

## Correction: derived flag dispatch includes a subtraction

The earlier interpretation of the flag lookup above was incomplete and is
superseded here. At4ce77, `add ebx,0x7ffffe97` computes
`(internal1001 - 0x80000169) & 0xffffffff` BEFORE the unsigned205 bound and
206-entry lookup. The seven zero indices are offsets, NOT raw1001 values.
Thus1001=0x80000169 selects flag0 directly; no invented internal170 mapping is
needed. Static assertions now cover the subtraction, unsigned bound and branch.
The portable policy and exhaustive206-entry/boundary tests have been corrected.

Also, derived vtable slot0 at4cd00 is a tail dispatch through slot8 (+0x20),
whose known-revision value is4cd10, the concrete initializer. The base slot0
494d0 is direct. Reading only eight derived slots hid this additional dispatch;
neither distinction should be replaced with a blanket vtable assumption.

Re-running all144 archived compact-cache cases with the statically derived
flag (from recorded input cameraId) now matches144/144 packed caches. Selection
does NOT inspect the expected bytes or fall back after a mismatch. The earlier
forcedflag1 baseline remains120/144, retained as negative evidence. Coefficient
mode is still an explicitly observed route input, and this test does not prove
the initializer object lifetime or whole-carrier selection on every model.

## Compact cache without observed coefficient-policy inputs

The verifier now also derives coefficients using the existing independently
extracted4b290 ID policy. Static assertions connect packer4b760's call4b898 to
4b290, and4b290's call4b293 to internal1001 getter470b0. All144 observations
agree with that discrete policy; all144 packed caches remain byte-exact when
BOTH grid flag and coefficient mode are computed before comparing native bytes.
The captured coefficient mode is now only a comparison target for this path.
Baseline forcedflag1 and post-comparison alternatives remain separately visible.

This removes one archived-input dependency from the numerical cache proof.
It does not remove installed cipher-table discovery from PF3 archive decoding,
nor implement camera transport or establish physical compatibility.

## Source-derived caches located in final carriers

Archive attribution now computes both caches from original1070/1071 records,
ID-derived grid flag and coefficient policy. No captured numerical table or
coefficient choice feeds this computation.120/144 computed caches occur intact
in retained final carriers at exactly the same locations as the independently
observed intermediate caches. The24 absent cases are M50, whose pixel branch
has already been separately reproduced. Absence does not prove failure.

An explicit whole16752 duplicate-cache hypothesis was also tested on all36
eligible carriers, not selected after inspecting expected output. Source-built
prefix plus encoded cache pair repeated twice matches all12 7DII carriers in
full. It fails all12 M50 and all12 5DS carriers, retained as negative evidence.
The5DS parameterless pair matches the cache but its first pair is transformed;
therefore identical carrier length does NOT authorize a common copy builder.
This extends the independent full-carrier proof to another archived route,
without changing production dispatch or asserting physical compatibility.

## Integer-composition negative proof no longer consumes captured tables

verify_compact_integer_stage.py now independently derives1070/1071 caches with
both ID policies, verifies them against the archive, then uses only the computed
bytes for unpack/interpolation/repack. The borrowed descriptor is still explicit.
All72 first-pair hypotheses remain nonexact, so the old failure was not caused
by substituting the wrong captured intermediate cache. M50/7DII are negative
controls, not asserted integer routes.

For5DS identity, maximum signed planar errors are[2,1,2] in the first block and
[3,2,6] in the second (Y,Cr,Cb). Histograms include positive and negative errors
and a substantially larger mode2 Cb spread. A single constant output offset
cannot explain these results. This does not identify whether the remaining
cause is descriptor-grid provenance or integer composition; retain both as
unresolved rather than applying a cosmetic rounding correction.

## 5DS resolved: hybrid pixel/cache route, not integer composition

A fresh unchanged identity compile in an owned hidden x86 lab host reproduces
the archived5DS payload hash exactly. Hash-gated read-only observation records
TWO475c0 pixel calls and NO4a3b0 integer calls. Both observed objectFlagByte and
coefficientMode are zero/false at the relevant branch. The previous integer
candidate was therefore the wrong path for this case, not an interpolation bug.
COMPACT_5DS_OBSERVATION_20261010.json retains the native stage evidence.

The source-derived descriptor grids match both observed first-pair inputs
exactly. Pixel inputs divide by255 (including values above1); source settings
match every initialized argument. Pixel outputs agree within floating error.
Final pixel packing uses the existing STYLE/MODE policy, NOT the cache's camera
ID coefficient policy: Neutral mode1=false, mode2=true. These two coefficient
policies must not be conflated even within the same carrier.

verify_5ds_pixel_source.py now builds prefix + two source-derived pixel blocks
(input/output scale255) + two source-derived cache blocks. All12 whole carriers
match16752 bytes exactly. Native grids/settings/pixels are comparison targets
only; original PF3 and descriptor feed the independent computation. The earlier
all-pixel and all-cache-copy hypotheses failed because the second pair follows
a different branch. Explicit hybrid selection is still not automatic dispatch.

The lab host was cleaned; a subsequent scoped process audit found no matching
hidden lab PowerShell hosts. Initial sandbox attach attempts yielded no evidence;
the successful observation used only the owned host with the required permission.
No EOS Utility attachment, EDSDK session, camera access or DLL patch occurred.

## Shared explicit compact compositor

compact_carrier_reference.build_observed_compact16752 consolidates pixel and
cache composition with four explicit block-path inputs, explicit scale and
internal1001. There are NO model names or inferred camera support in its API.
The existing all-pixel wrapper delegates to it without changing its defaults.
Unknown/integer paths are rejected, not silently approximated. Cache blocks
reuse the source cache converter and ID policies; pixel blocks retain the
separate style/mode coefficient policy. Production dispatch remains untouched.

Tests cover route length/type/content, selector bounds, source pair reuse and
absence of any pixel-grid call on an all-cache route.505 unit tests pass.
The private whole-carrier verifiers independently compare the reusable result
against their separately composed formulas before checking retained payloads.

## First-pair automatic planning and serializer prefill

compact_first_pair_plan now combines the independently extracted4c3b0 prefix
policy, normalized descriptor capability words and4c770 branch rule. Static
extraction confirms4c3b0's41 compact-prefix IDs equal4b290's41 coefficient IDs;
that equality is asserted rather than inferred from model names. Legacy readers
use the7492-byte prefix of the NORMALIZED internal modern store, not a separately
renormalized raw prefix. Unknown geometry and non-byte object flags are rejected.

For the retained normalized R8 descriptor and Neutral source: M50 selector412
gets modern words(1,1) ->pixel/pixel;7DII80000289 gets compact-prefix words(0,0)
->cache/cache;5DS80000382 gets modern words(1,1) ->pixel/pixel. These predictions
agree with the source-derived first-pair proofs. Synthetic tests independently
exercise mixed gate words and enabled integer paths;506 unit tests pass.

Static serializer evidence explains why SECOND-pair selection cannot simply
repeat this result.55a11/34/58/7c prefill all four output blocks from1022/102a.
55ab9 constructs a fresh derived builder;55ac8 builds1f00/1f01 and55adc/af9
overwrite only the first pair.55b38 then invokes the serializer object's virtual
slot0x38 for subsequent pair handling. Its target/lifetime must be established
before automatic full-carrier planning can be claimed.

The fresh builder constructor46be0 explicitly writes byte+8=0 at46bf1;
derived ctor4c610 calls it at4c61d. This is NOT the PF3 reference object's byte+8
seen in the earlier5737c setter analysis. Conflating those objects led to the
incorrect expectation of a nonzero5DS flag. Both constructor instructions are
now hash-gated static assertions; native5DS observation independently confirms0.

## Second pair resolved for the retained base-reference compact routes

Owned offline observations reproduce the original identity carrier hash for
5DS,7DII and M50. For5DS/7DII the55b38 call uses vtablebf0d4 and target53250.
Static bytes at53250 are exactly `xor eax,eax; ret8`: it does not modify the
prefilled second pair. M50 never reaches55b38; absence alone is not the proof:
its metadata-read callers and derived-set callers identify5693d's separate
serializer branch, which explicitly calls4c770 at56d04 AND4d660 at56d4b.

54cd0 calls4eaf0, subtracts1 and dispatches through56e1c for classes1..10;
out-of-range goes5693d. The independently extracted family classifier returns
class6 for5DS/7DII ->556fe and class7 for M50 ->5693d. Both branches produce
the same16752-byte layout but have DIFFERENT second-pair semantics. These
instructions, table targets and no-op bytes are asserted in the new
extract_compact_dispatch.py / COMPACT_DISPATCH_STATIC_20261010.json.

Pixel scale is separately selected by4b250: default256 atbb6e0,255 atbb6d8
only for internal IDs80000382/80000401. Both double constants and comparisons
are statically asserted; compact_pixel_scale implements this bounded policy
with type/range/neighbor tests. It must not be inferred just from class6/7.

This closes the second-pair explanation for retained NORMAL base-reference
fixtures, not arbitrary PF3 subclasses or camera transport. Unknown serializer
classes/callbacks remain unproven. No installed DLL or Canon application was
modified; all owned successful observation hosts were cleaned in finally.
