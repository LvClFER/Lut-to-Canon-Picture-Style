# Offline legacy compiler failure map

Private research only. No camera access, compiler patch, or payload installation.
DLL SHA256: `7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0`.
All virtual IDs used the recorded R8 descriptor; this is not firmware emulation.

## Observed failures

`OLD_ERRORS_ALL_RAW_READ_TRACE.json` contains 14 failed PF3 compilations.
The read-only raw-property observer separates them into two causes:

* D30, D60, 1D, 1Ds, 10D, 300D, 1D II, 20D, 1Ds II, 350D:
  derived `1022`/`102a` reads of 4096 bytes return 80, despite observed
  compact/integer packer calls. A produced intermediate grid is not a
  successfully returned carrier.
* 5D, 1D II N, 30D, 400D: reads of `1007` (1460), `1004` (300),
  and `1005` (240 bytes) return 80 for the PF3 fixture.

Two PF2 fixtures tested across all 14 IDs also failed. Nine official PF2
fixtures tested on the 5D route supply enough source data for the compiler
to prepare `1004`/`1005`; only `1007` fails. Those two legacy IDs are not
literal records in the independently decoded Emerald file (see below).
Changing the file extension or assuming PF2 intrinsically fixes this is unsupported.

## Matched carrier import/export code

For family branch 1, the native setter at RVA `52110` requires 8164 bytes,
checks header words 1 and `1fbc`, and copies/imports fields through `51500`.
The getter branch at `54d18` uses the same offsets and lengths:

| Record | Carrier offset | Bytes | Setter call | Getter call |
| --- | ---: | ---: | --- | --- |
| `1007` | `4c` | 1460 | `5223e` | `54d9e` |
| `1004` | `600` | 300 | `52263` | `54dbd` |
| `1005` | `72c` | 240 | further setter branch | `54de2` |

These are observed byte ranges, not established semantic names. Importing
a complete carrier also changes other fields, including polynomial/LUT
representations. It must not be treated as a harmless metadata-only operation.

`GetPropertyData(01000203, index=-1)` delegates to `50c00`, which largely
zero-initializes family templates. Its first branch emits a zero header,
whereas the normal 8164-byte setter requires header value 1. Therefore this
template getter is not established as a source of valid missing legacy data.

## Reproducible diagnostic

`python -m camera_install.compiler_failure_research TRACE OUTPUT` produces
the compact causal summary, preserves model/source/return code and marks
every camera's physical compatibility `not-tested`. Output is exclusive-create.
Failed traces retain the observer results and print `FAILED`, not merely packer counts.

Next: identify who supplies `1007`, then characterize the 4096-byte derived
getter failure independently. Do not fabricate camera registration state,
reuse a foreign camera carrier, or interpret rc=0 alone as LUT correctness.

## Lookup/lifecycle follow-up

`OLD_10D_SOURCE_DESTINATION_TRACE.json` observes both source lookup `46c10`
and compiler collection lookup `4e160`: `1022`/`102a` return null in both.
The raw getter `4ef20` returns 80 for a missing node, distinct from its
buffer-too-small return 100. This rules out a size-only explanation for
this specific 10D trace.

`NINE_ROUTES_RECORD_LIFECYCLE_TRACE.json` compiles all nine representative
routes successfully with the same observer and source. M50/M3 raw reads
find `1022`/`102a` as type 4, size 4096. They also call `51500` with zero
length/null data for `1f00`/`1f01`, then later read those as populated type-4
4096-byte nodes. Such a zero-length call cannot globally be interpreted
as permanent deletion: subsequent processing creates/repopulates nodes.
10D also makes those two calls, but its earlier missing reads have already
contributed error 80 to the aggregate result.

The next investigation must locate derived-node materialization and its
camera-ID gate, not blindly copy source PF3 records or foreign payloads.

## Static record schema

Factory `4dee0` searches 50 entries of 12 bytes at RVA `cf5e0`.
Each entry is ID, storage type, size constraint. It initializes a node via
`4de70`, storing the constraint at node+14; actual data length is node+c.
`4a120` enforces exact input size for constrained numeric records, bounded
size for type-2 strings, and variable input length when the constraint is 0.
This is a size constraint, not an already-populated default value.

`1007` is type 3 (16-bit storage), exact 1460 bytes; `1022`/`102a` are
type 4 (32-bit storage), variable length. `1070`/`1071` are type 3,
variable length. The schema does not establish these fields' color meaning.
`pf3_schema_research` independently extracts only metadata after an exact
DLL hash check; an unknown DLL is rejected before using the fixed RVA.

## Derived-node initialization experiment

`DERIVED_RECORD_SET_CALLERS_TRACE.json` identifies the same generator's
write at `4cf30` in both 10D and M50. It calls `4a2b0` for `1022` and
`102a` with 4096 bytes. 10D returns 80 because the node lookup fails;
M50 returns 0 and reaches node-data writer `4a120`.

The private scratch serializer experiment attempted to add both records;
Canon omitted them from the file while preserving all other fields.
This failed persistence hypothesis is retained, not counted as a solution.

The separate `runtime_seed_probe.js` creates these two records by exported
Canon API **in memory before compilation**, without changing Canon machine
code, source PF3, registration transaction state, or camera installation.
Zero and FF initial contents test whether output is derived or seed-dependent.

* Identity, 10D and M50, 4 cases: all exact stock M50 Identity bytes.
* Aerochrome, 14 old IDs, 28 cases: 20 successful cases (the 10 earliest IDs
  with both seeds), all exact stock M50 Aerochrome bytes. Aerochrome reference
  differs from Identity only in header/name, not in the four color blocks.
  This is structural recovery, not arbitrary-LUT acceptance. The four
  metadata-dependent routes still fail 80.

Reports: `RUNTIME_NODE_SEEDS/RUNTIME_SEEDS.json`,
`RUNTIME_NODE_SEEDS_OLD14_AEROCHROME/RUNTIME_SEEDS.json`,
`AEROCHROME_M50_STOCK_REFERENCE_TRACE.json`.
These virtual routes share the recorded R8 descriptor. They establish a
compiler preparation mechanism, **not physical support for old cameras**.
No production installer change or build was made from this experiment.

## Metadata influence is not a fix

`LEGACY_METADATA_BYTE_INFLUENCE/RUNTIME_SEEDS.json` uses official Emerald
PF2, where only `1007` was missing. Inserting a zero/FF `1007` in memory
allows all four legacy getters to finish, but changes exactly 1460 bytes:

| Virtual route | Carrier bytes | Changed range (exclusive end) |
| --- | ---: | --- |
| 5D / 1D II N | 8164 | `4c..600` |
| 30D / 400D | 8168 | `14c..700` |

All other output bytes remain equal between those two seeds. The content
is passed through, not recomputed from the PF2's polynomial/LUT. **These
diagnostic payloads contain invented data and must never be installed.**
rc=0 demonstrates the missing-field dependency, not a valid camera style.
No genuine 8164/8168 carrier or standalone 1460-byte fixture was found in
the restored Research archive by file-size search.

## PF2 source versus synthesized legacy fields

Emerald's independently decoded PF2 has 11 terminated records, no leftover
bytes, and contains neither `1004`, `1005` nor `1007`. Its main mathematical
records are `1018`, `1019`, `1021` and `1029`; no compression hypothesis is
needed for this file. API/compiler-visible fields must not be conflated
with records physically serialized in the source file.

`LEGACY_FIELD_ALIAS_COMPARISON.json` checks all eight diagnostic outputs:

* Carrier `1004` is exactly source `1018` with 32-bit endian conversion.
* Carrier `1005`, after the observed XOR transform with seed `3f194`, is
  exactly source `1029` with 32-bit endian conversion.

Both aliases match in all four routes and with both diagnostic `1007`
seeds. This maps two missing legacy fields to existing source mathematics,
but does not supply or establish the semantic meaning of `1007`.

The eight official PF2 vectors were subsequently swept across these four
routes and both diagnostic metadata seeds: all 64 alias comparisons match.
Invented `1007` remains a diagnostic, never an installable solution.

## Source conversion versus final table selection

`DENSE_INTERNAL_SOURCE_AEROCHROME_CHECK.json` verifies 48 complete dense
captures against the source PF3: every value equals the decoded BE uint16
word divided by 4095. The parser does not substitute the source tables.
The direct private converter call is experimental runtime preconditioning,
not stock Canon behavior or a production installer change.

`DENSE_IDENTITY_AEROCHROME_FINAL_COMPARISON.json` then compares each native
color block, explicitly excluding names/headers, with identical route IDs,
descriptor and zero/FF seed coverage:

| Route | Changed bytes per final 4096-byte block (seed 0) |
| --- | --- |
| M50 | 0, 0, 0, 0 |
| M3 | 3825, 3804, 3825, 3804 |
| 1D III | 3809, 3787 |
| 450D | 3825, 3804, 3825, 3804 |
| 7D II | 3825, 3804, 3825, 3804 |
| 5DS | 0, 0, 3821, 3798 |

Seed FF gives the same differences. On M50, the intermediate `4b760`
packed Aerochrome blocks differ from Identity, but are absent from the final
payload. Later `49e00` blocks match that payload instead. Other routes retain
the intermediate packer bytes, fully or in the second pair. This localizes
the loss after correct dense conversion and before final payload assembly.
Same payload length is therefore not sufficient to infer table selection.
Neither byte differences nor these virtual routes establish physical image
appearance or camera compatibility. A shared recorded R8 descriptor is used.

`test_dense_acceptance_research.py` includes a header-only false-positive
regression, exact dense-source comparison and partial-capture rejection.

## Record initialization gate and reflection follow-up

The hash-checked static scan finds six literal `1007` instruction references:
four carrier readers (`4f399`, `4f52b`, `54d99`, `54f27`) and two carrier-import
writers (`52239`, `5241b`). No direct literal-ID generator was found. Generic
table-driven behavior is still possible; this is not proof no generator exists.

An archive survey covers 660 PF2/PF3 files, 231 unique SHA-256 identities.
After extending the private reader for two observed variants, all 231 decode
completely: 220 match the checksum, five have no checksum record, and six
have a mismatching checksum. None serializes `1007`. Some official PF2 files
have a complete terminated record list with no checksum; structural decoding
and integrity verification remain separate results.

The first variant accounts for 95 files previously classified as body-size
mismatches: envelope version `00002001`, physical size four bytes larger than
the declared body, and an encrypted trailing word that decodes to zero. Parsing
only the declared body yields a complete record list and a valid checksum in
all 95. The trailing word is preserved as opaque; its semantic name is unknown.

The second variant appears in two PSE-converted Emerald PF3s. Each contains
14 `90xx` records alongside `10xx` counterparts, with valid whole-body checksums.
The high bit must not be discarded: in the Saturation +1 file, `1032` is one
while `9032` remains zero. Both files have `9011=1` while `1011=0`. This supports
distinct active/reference values, but complete bank semantics are unresolved.
The research parser permits these records only with an explicit option and
retains both IDs independently.

The exported `EdsCfpReflectProperty` was tested on scratch copies of official
Emerald PF2 and Superia PF3 for 5D, 1D II N, 30D, 400D, 10D and M50, using
both recorded R8 and 1300D descriptors (24 compiles). Reflection returns zero
in all 24, but the five old IDs still fail `rcGet=80`; both M50 cases with each
descriptor compile. Reflection leaves all source copies byte-identical.

Before and after reflection, the four metadata-dependent IDs expose `1007`
as type 3 with size zero, while `1022/102a` are populated to 2,916 bytes.
The observed 9-node writer at `495fa` fills those two fields successfully.
The 10D exposes none of the three; the M50 exposes 4,096-byte `1022/102a`.

The node factory trace locates initialization at `53b40`, with the factory
return site `53bac`. Static branches and tables establish three paths:

| Path | Recorded IDs | Initialization |
| --- | --- | --- |
| Skip | D30, D60, 1D, 1Ds, 10D, 300D, 1D II, 20D, 1Ds II, 350D | Return before the record-list loop |
| Legacy list | 5D, 1D II N, 30D, 400D | `1009,1002,1007,1004,1005,1003,100b,1022,102a` |
| Common list | Other IDs in this baseline | `1009,1002,100c,1022,102a` |

The eight explicit skip IDs plus two switch-table skip IDs exactly match
the ten missing-derived-node failures. Four switch-table legacy IDs match
the four empty-`1007` failures. The extracted classification agrees with
87/87 outcomes in the recorded Neutral/R8-descriptor baseline (73 common
list successes; 14 old-path failures). This explains that compiler matrix;
it does not predict every source/style/descriptor or physical body behavior.

Private evidence: `LEGACY_1007_STATIC_REFERENCES_20261005.json`,
`LEGACY_SERIALIZED_RECORD_INVENTORY_V3_20261005.json`,
`LEGACY_REFLECT_API_20261005/REFLECT_RESULTS.json`,
`LEGACY_REFLECT_API_1300D_DESCRIPTOR_20261005/REFLECT_RESULTS.json`,
`LEGACY_NODE_CREATION_TRACE_20261005/REFLECT_RESULTS.json`, and
`LEGACY_INITIALIZATION_GATE_BASELINE_20261005.json`.

## Independent9-node packer

Static writer494d0 selects a9-node RGB double grid for the four legacy-list
IDs, then calls4bea0 and writes2916-byte1022/102a. The raw packing routine:

-Truncates each planar RGB double to integer before4abb0.
-Uses the observed coefficient-mode1 RGB-to-Y/Cb/Cr constants.
-Applies the CRT floor helper separately to each weighted component.
-Quantizes by2 with the observed negative chroma wrap at512 and masks10bits.
-Traverses output in b,g,r order; each word is(Y<<20)|(Cb<<10)|Cr.
-Contains729 words, no10-node octant padding or header.

New `packed9_reference.py` implements these steps independently. Own hidden
host native comparison directly invokes only4bea0 on scratch arrays/context,
without references, PF3s, EDSDK or cameras. Black, white, coordinate ramp and
deterministically seeded random vectors each match all2916 bytes exactly.
Thus9-node packing is mapped independently, while missing1460-byte1007
metadata remains unresolved. A correct packer does not clear the legacy
compiler failure or establish any camera-install compatibility.

Private evidence: PACK9_INDEPENDENT_20261005.json. Unit tests cover bounds,
negative chroma wrap, truncation, output traversal and invalid inputs.

##1460-byte origin versus729-node packing (2026-10-06)

A hash-gated static scan for1460/730/729 finds six1460-byte read/import
sites for1007 and two729-count loops. The latter belong to4bea0 (planar
double RGB input) and4c1d0 (planar int32 RGB input), both writing2916-byte
9-node packed grids. They do not establish1007 as a730-word color grid.
In particular,4c1d0 is an integer-input packer, not an unpacker: it calls
4abb0 and assembles the same three10-bit components into each32-bit word.

The independent9-node reference now compares both known native entry points
on own scratch arrays. Four integer-input fixtures (black, white, coordinate
ramp, seeded random) match every2916-byte output exactly, after explicit
input truncation. The revised report records functionRva and inputRepresentation
so double and integer evidence cannot be conflated.269 tests and py_compile
pass. No camera API or Canon reference is involved in these helper calls.

No actual8164/8168-byte binary carrier was found by size in the private
Research archive. The installed Canon search found only the already known
EU3 EdsCFParse revision, not a second old compiler for comparison.1007 remains
unresolved; a genuine old-family carrier would be stronger evidence than
invented zero/FF data, but independent mapping can continue elsewhere without
claiming such captures exist.

Private evidence: LEGACY_1460_GEOMETRY_REFERENCES_20261006.json and
PACK9_INTEGER_INDEPENDENT_V2_20261006.json. The first integer report also
matches but lacks explicit mode metadata; use V2 for reproducible attribution.

## Opaque metadata boundary regression (2026-10-07)

The earlier zero/FF diagnostic conclusion now has a reusable independent
`legacy_metadata_reference` check. It extracts exactly1460 bytes at4c for
8164-byte diagnostics or14c for8168-byte diagnostics, rejects unknown geometry,
requires the stated zero/FF records, and requires every outside byte to remain
equal. `verify_legacy_metadata.py` replays all four retained diagnostic pairs
and records their hashes in LEGACY_METADATA_BOUNDARY_PROOF_20261007.json.
This is additional regression coverage of existing evidence, not discovery
of the field's semantics. All proofs explicitly label syntheticDiagnosticOnly
and cameraInstallValidated=false. No fabricated records are added to the app
or offered for installation. 323 tests and py_compile pass. A genuine legacy
carrier remains missing; independent research continues on other components.

Initialization regression (2026-10-07): the classifier now rejects boolean
IDs and unknown/noninteger selector values instead of treating them as valid
numeric branches. Synthetic tests cover explicit skips, each switch branch,
both bounds and out-of-table default behavior. `verify_initialization_mapping.py`
re-extracts the hash-verified DLL gate, requires its full rules to match the
retained extraction, and reproduces all87 route attributions exactly.
INITIALIZATION_MAPPING_REGRESSION_20261007.json records the baseline hash.
This strengthens reproducibility of an existing result, not new camera
support. The default common-list branch remains a compiler behavior, never
an unknown-camera compatibility verdict. 327 tests and py_compile pass.

## Genuine old-compiler1007 resources found (2026-10-11)

The archived EU2 compiler SHA
`8837dc1094941d345b7d0cc798e2a64e75f0bcf31ef22a708dfcb5c061d632ff`
contains24 `BIN` resources102..125, each1460 bytes and beginning with a
little-endian uint32 length1460. Static initializer7b60 selects six resources
per camera selector, using style minus81:

| Selector | Recorded model | Resource IDs81..86 |
| --- | --- | --- |
|80000213|5D|102..107|
|80000232|1D II N|108..113|
|80000234|30D|114..119|
|80000236|400D|120..125|

The initializer calls FindResourceA/SizeofResource/LoadResource/LockResource
then internal setter67e0 with field1007, byte order4949, the resource pointer
and its size. Caller8a5d reads style1009 before this initialization. All24
mapping entries and15 instructions are hash-gated by
`extract_legacy_resources.py`; resource bytes are not extracted to files.
The current EU3 known revision has no equivalent BIN resource collection.

Native compile-only experiment in owned hidden hosts: the official archived
Emerald PF2 (style81) fails rcGet80 on all four selectors without1007. Supplying
the appropriate genuine old resource to an in-memory reference changes all
four to rcGet0. It succeeds with insertion both before and after selector
setup. Output sizes are8164 for5D/1D II N and8168 for30D/400D. The resource is
copied byte-for-byte into the observed carrier region (offset76 or332).
Private report: LEGACY_GENUINE_RESOURCE_OFFICIAL_PF2_20261011.json.

The20 modern PF3 five-style cases still return80 even though GetPropertySize
confirms1007 is retained at1460 bytes, in either ordering. Therefore1007
explains the official-PF2 failure but is not sufficient to make arbitrary
modern PF3s compatible with these old branches. Other legacy fields and
conversion semantics must still be traced. No camera operation, DLL patch,
production integration or physical compatibility claim occurred. Resources
and carriers were kept in memory, never packaged or saved as binaries.

## Modern PF3 legacy-field bridge and9-node proof (2026-10-11)

Read-only observation of helper4ef20 isolates modern PF3 failures to1004,
1005 and1007. With genuine1007 supplied, only1004/1005 return80; all other
carrier reads, including both2916-byte grids, return0. Supplying host32
copies of source1018→1004 (300 bytes) and1029→1005 (240 bytes) clears these
remaining errors. The earlier alias relation observed in official PF2 thus
provides a successful in-memory bridge for these tested modern PF3s.

All20 five-base cases (four selectors × Neutral/Faithful/Landscape/Portrait/
Standard) compile with rc0; all inserted1007 bytes and both alias fields match
their sources exactly, after applying the known1005 cipher seed3f194.
Report: LEGACY_GENUINE_RESOURCE_ORDER_COMPILE_20261011_ALIASES.json.

All48 LUT cases (four selectors × twelve Neutral LUT vectors) likewise compile
with rc0 and exact inserted fields. Each selector has10 distinct pairs of
output grid hashes across12 inputs; this is not itself an accuracy metric.
Observing4bea0 *before selector setup*, rather than only during final output,
captures96 planar-double grids. Their intermediate range reaches286; the
earlier255.75 helper guard was only a conservative tested range, not a native
clamp. New research-only `pack9_observed_overshoot` supports the observed
0..286 range without changing the default `pack9` guard or production use.
All96 independent packed results match the native helper's2916 bytes exactly.
All96 also match their final carrier locations after decoding with seeds
252e4 (1022) and2d456 (102a), established at54e71/54e81. Total279936 grid bytes
compared. The helper runs during input preparation, explaining the initial
empty late-observer trace; no empty trace is accepted as a grid proof.

Reports: LEGACY_GENUINE_RESOURCE_ORDER_COMPILE_20261011_READS_ALIASES_LUTS_PACK9.json
and its independent audit LEGACY_RESOURCE_GRID_PROOF_AUDIT_20261011.json.
This proves packing and placement given observed MLib output, not independent
upstream MLib generation, native rendering accuracy, installer acceptance or
physical camera support. Genuine old resources remain external private
research dependencies; no binaries or default fabricated values were bundled.

## Independent dense-source9-node generation (2026-10-11)

The preceding494d0 curve/matrix path is NOT the source of the tested modern
PF3 grids. Derived subclass routine4cd10 reads dense1070/1071 through46fd0,
constructs header[3,9,17496,0], and passes null curves to46a50. Bindingd11e0
resolves `MLIBcalcLuckyFromFileLUT` at MLib1c950, which calls196a0 at1ca9a.
The separately verified synthetic cdecl wrapper1b670 also calls196a0; it is
not the named export. Both bindings are asserted inDENSE9_ROUTE_STATIC_20261011.json.

New `legacy_dense9_reference.py` reproduces that direct dense/null-curve/flag0
path: trilinear33-grid sampling at40/255 increments, shared diagonal boundary
samples capped at index6 and normalized1, correction(8*b-5.2*a)/2.8, scaling255,
clipping0..320 and integer truncation. It does not call the preceding polynomial/
selective MLIBcalcLuckyEx reference or read observed numerical grids.

All96 grids from the retained48 LUT cases are now reproduced directly from
the independently decoded PF3 source records, including exact double-array
hashes. Packing and encryption then match all96 final carrier-grid hashes:
279936 encoded bytes, no native execution during replay. Twelve unique source
files are checked by hash before use. Local-DLL cipher tables remain an
explicit dependency. Report: LEGACY_DENSE9_SOURCE_PROOF_20261011.json.

Additional own-host helper comparison covers seven quantized synthetic33-grid
sources (identity, constant, square, impulse, scrambled, black, white) in both
converter options1/2:14/14 exact full-array comparisons. Constant white exposes
the native integer truncation of floating interpolation:270 planar components
are254 and1917 are255, identically in native and independent outputs. The unit
test preserves this observed behavior, not an idealized all255 result. These
tests validate the specific direct path, not every source or non-null curve
configuration. Report: DENSE9_SYNTHETIC_PROOF_20261011.json.543 tests pass.

Remaining old-family independence work includes whole-carrier composition,
1007 semantics/generation without Canon resource bytes, and the other ten
older initialization-skip selectors. No new camera capability is asserted.
