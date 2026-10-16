# Carrier metadata: static legacy branch attribution

Reproducer: `../tmp/PF3_FIELD_EXPERIMENTS_20261004/extract_carrier_metadata.py`.
Output: sibling `CARRIER_LEGACY_METADATA_20261009.json`. Hash-gated EdsCFParse
revision `7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0`.
Static PE inspection only: no DLL execution, device enumeration or camera session.

The Ver3 carrier method at RVA 54cd0 has size-gated branches for 8164 and
8168 bytes. Both write validity 1, a data size of total minus 40, and retrieve
1002/1009/1007/1004/1005/100b/1022/102a from the style's record collection.
Their layouts differ: 1007 begins at 0x4c or 0x14c; the 252-byte control
conversion at 512e0 writes at 0x81c or 0x50 respectively. The latter branch
also writes 0x00fc0028 at 0x4c. Full offsets and instruction evidence are in
the generated report. These branches do not justify a modern 372-byte header.

Record helper 4ef20 checks destination capacity against stored size at
record+0xc, rejects an undersized destination with 0x64, and delegates to
46de0 with capacity, destination and byte order. Missing record or failed
conversion returns 0x50; successful conversion returns zero. Therefore
calling this an unconditional opaque memcpy would overstate the evidence.

Next: attribute 46de0 and 512e0, then follow modern header paths. This is
not yet an independent full carrier generator or registration implementation.
The production camera path was not changed. Static assertions, py_compile
and all 448 unit tests passed.

## Control envelope follow-through

512e0 zeroes its temporary buffer and writes a leading 2fff/ffff/zero
record header. Its two selected IDs, read from RVA cf5d8, are 100a followed
by 100d. Each present record gets an eight-byte ID/type/length header and
typed output via 46de0. It reserves room for the final ffff/ffff/zero
terminator. Cipher 02db0 is applied from offset eight to the buffer end,
including padding, with seed 22e1. This is distinct from registration 115.

Added `control_section_reference.py` for the unencrypted envelope only.
It uses the already native-checked typed output reference; its complete
envelope has synthetic tests, not native equivalence. It rejects overflow
instead of emitting native partial output, supports only little endian,
and contains no cipher keys or actual Canon records. Existing typed-copy
research already covers 46de0, so repeating those native probes is unnecessary.
Next useful evidence is archived control-section equality or a bounded owned
offline compiler observation, followed by modern header attribution.

## Archived full-section equality

`verify_control_section_archives.py` now verifies source SHA against the
original native diagnostic report, and every retained payload against its
recorded hash, size and successful getter result. From the official Emerald
PF2 source it reconstructs the control records, envelope, terminator and zero
padding. All eight complete 252-byte sections match, before and after cipher,
across 8164/8168 layouts and 00/FF synthetic metadata seeds. No native code
ran during replay. This proves more than only record prefixes, but remains
one source with experimental 1007 preconditioning, not valid whole carriers
for actual cameras. Cipher tables still come from the hash-verified local
DLL; redistribution and full independence are not implied. Four new unit
tests pass, bringing the suite to 452.

## Modern 17-node header: 78980-byte branch

`extract_modern_header.py` anchors at jump-table target 55b60 rather than
guessing an instruction boundary. Hash-gated assertions and the global
control size252 establish total78980, data78940, and first table372.
The whole output is zero-initialized before fields are populated.
Name1002 occupies offsets8/46 (32 bytes each), style1009 offset44 (2 bytes),
and 1031/1030/1032/1033 occupy80/84/88/92. Fields1034/1035 occupy104/108;
deadbeef markers occupy96/100. Size/control words at112/114 precede the
252-byte control envelope at116. Table prefix100c is at368, followed by
two zero bytes. The sizes at40 and4 are both little endian. Initial static
interpretation of the shift/or sequence as byte reversal was incorrect;
archived prefix equality exposed it and the reference/report were corrected.

1030's comparison uses uint32 capped at7; 1034/1035 use
uint32 comparisons clamped1..5. The shift/or sequence preserves the value.
Missing-record fallbacks depend on style,
with jump-table targets retained in the report. Do not simplify these into
uniform numeric packing or generic zero defaults. The report maps this
branch only: the 83076 extension, 10-node and full33 headers are not yet
proved equivalent. No new native calls, independent full-header equality,
camera registration or physical validation occurred.

## Complete modern prefix reconstruction

Static follow-through at56035 shows the 83076 branch has the same prefix
layout with different total/data sizes. Added `modern_header_reference.py`
for complete successful record sets only, explicitly rejecting missing-field
fallbacks. It accepts independently encoded control bytes, no carrier input.
`verify_modern_header_archives.py` verifies source/output hashes against the
retained trace and rebuilds all372 prefix bytes from source PF3 records.
All24 successful archived outputs match exactly across sizes78980/83076.
Two original trace entries without successful retained outputs are skipped,
not counted as passes. No native code or camera access occurred. The local
DLL remains required for cipher keys; whole carrier independence is unproved.
Three new unit tests cover lengths, name duplication, markers, clamps and
rejection of incomplete records/layouts. Full suite:455 passing.

## Opt-in missing-control defaults

Reference now models absent control IDs under an explicit opt-in flag. Any
missing member of1030..1033 resets the entire four-field group: strength3
except style84 strength0; the other three fields zero. Presence of later
detail records is evaluated separately, so complete1034/1035 overrides any
earlier clearing. If either detail ID is absent, both detail values default:
style82 ->2/4,84 or85 ->2/2,88 ->1/1, all others ->2/3. Both modern jump
tables produce the same pairs; the static reproducer asserts this.

Required name/style/table-prefix records remain required. Invalid, oversized
or failed conversion inputs still raise rather than imitate malformed native
records. The opt-in behavior has54 synthetic missing-field cases across nine
styles, not new native equivalence. Default strict behavior retains24 exact
archived complete-prefix matches. Full suite458 tests; no production change.

## Composite replay and isolated extension

`verify_modern17_composition.py` rebuilds the source-derived prefix plus four
packed tables, selecting matrices from source1009 and captured selector1/2.
It uses captured planar inputs, not captured packed outputs; packing order
is1/1/2/2 mapped to output blocks0/2/1/3. All24 reconstructions match the
first78980 bytes. Twelve are complete78980-byte carriers; twelve83076-byte
carriers retain an unresolved4096-byte tail. Two trace failures stay excluded.
This is composite equivalence, not independent source-to-carrier compilation:
upstream planar grids and local DLL cipher keys remain dependencies.

Static tail provenance is now asserted in `extract_modern_header.py`:
the extended branch creates1f02 via49830, copies4096 bytes, runs virtual3c
pre/post filters around cipher02db0 with seedb8ed, and places the result at
78980. Next useful work is49830 generation and these filters, not assuming
the extension duplicates one of the four17-node tables.

## Extension builder attribution

Hash-gated static assertions now follow49830 through48d10 (floating10 grid),
46f50/4a5e0 auxiliary legacy source,46cd0 or46d70 settings,475c0 (processed
integer10 grid),49e00 (existing integer octant pack reference), and4a2b0
record1f02 creation with4096 bytes.475c0 invokes46a70 per pixel before
matrix conversion/quantization. Thus the tail is neither copied17-node data
nor a direct pack10 of the observed14bd0 floating grid.

A read-only diagnostic on the first retained R5 identity case tried both
float packing matrices and simple integer scaling1/2/4; none matched the
decoded4096-byte tail. This negative check is not an exhaustive conversion
search or new native rejection. The existing trace lacks475c0/49e00 tail
inputs, so next obtain those through a normal owned offline invocation or
fully reproduce46a70 from the attributed auxiliary inputs. Do not guess
the missing transformation from carrier length or camera model.

## Normal isolated tail observation

`capture_tail_stock.py` ran one normal identity compilation in an owned hidden
x86 host, with exact source/descriptor/compiler/MLib revision checks and
existing finally cleanup. Its dedicated agent imports only EdsCFParse APIs;
no EDSDK enumeration, session, EOS Utility attachment, or camera operation.
The recorded descriptor and ID are offline compiler inputs, not a physical
camera. Baseline output SHA exactly matches the prior83076-byte carrier.
The current read-only observer records one475c0 call returning to4999b and
one49e00 call returning to499ad. Earlier trace simply lacked these observers.

`verify_tail_stock.py` confirms all12000 integer-grid bytes match the packer
input. Independent `pack10_integer` reproduces the native4096-byte block
exactly and also the decoded carrier tail at78980 with seedb8ed. This closes
tail packing and its linkage for one normal identity case.475c0's upstream
pixel transformation still needs independent reproduction; the captured
integer input and DLL cipher keys remain dependencies. No universal or
physical compatibility claim follows. py_compile and458 unit tests pass.

## Full tail pixel-chain replay

A second normal owned offline compilation retains all1000 ordered1cab0
pixels and initialized settings, with the original carrier SHA unchanged.
`verify_tail_pixels.py` verifies exact475c0 planar-input/normalized-pixel
linkage for observed scale256, then evaluates existing independent
`compact_pixel_reference.point`. Maximum error across3000 components is
1.1379786002407855e-15. Independent matrix/packing reproduces all4096 tail
bytes with the alternate matrix (pack10 coefficient_mode=False).

The proof is tied to the same source/output hashes as the prior78980-byte
composition, so the disjoint proofs cover all83076 carrier bytes for this
identity case. Captured upstream grids/settings still feed the references;
this is not a standalone source-to-carrier compiler. Scale256 was confirmed
for this context, not assumed universal. Cipher keys still require the local
DLL. No physical camera operation occurred; both owned hosts finished and
cleanup returned. Next remove captured-input dependence by deriving the
tail's initialized settings and grid from source/descriptor records, then
extend beyond identity.

## Tail settings now source-derived

Added `tail_settings_reference.settings_from_records`: observed complete
mode1 branch maps pre1018, post1065, third1019, matrix1021, axes1061 and
selectors1023. Static helper windows46cd0/47030/47130/471c0 are retained and
asserted in the extractor. This matters because the three identity curves
are byte-identical, so matching captured bytes alone cannot establish their
semantic order. The caller stack and helper IDs determine it.

The tail verifier now decodes the hash-verified PF3 and generates all these
arguments independently; it only compares them to captured settings as a
check, not as calculation inputs. All initialized settings match exactly;
the1000-pixel reference and4096-byte tail remain exact. Complete required
records and bounded axes/selectors only; missing-field fallback is not
guessed. Three new synthetic unit tests cover distinct curve provenance,
missing records and selector boundaries.461 tests pass. Captured upstream
floating grid, numeric mode/scale attribution and cipher keys still prevent
an independent source-to-carrier compiler claim.

## Tail grid now descriptor-derived

The replay no longer feeds captured floating-grid pixels into its calculation.
`modern_grid_arguments` independently expands the normalized recorded modern
descriptor using the source style ordinal and index1; the existing 10-node,
flag1 reference computes all1000 RGB samples. The normal identity case matches
the observed upstream grid within1e-10 and still produces the exact4096-byte
tail after source-derived pixel settings and packing. Captured grid/settings
are verification targets only. Two synthetic tests guard argument derivation
and unsupported selectors/modes. No camera or native DLL execution in replay.

Limitations: one identity case, recorded descriptor and local DLL cipher keys,
observed numeric mode/scale, and the other four 17-node grids remain to be
integrated into a complete independent compiler. No new physical compatibility
claim follows. Next: derive the 17-node descriptor grids in the same composite
proof and test nonidentity vectors before transport integration.

`verify_descriptor_grids.py` also rebuilds both upstream17-node grids
(4913 RGB samples each) and the10-node grid (1000 samples), with maximum
component error0.0 against all three normal compiler observations. The
second descriptor selection uses mode2, not mode1; this is now explicitly
checked rather than silently inferred. These are upstream grids, not the
four complete packed17 output tables.463 unit tests pass; changed references
and replay scripts compile successfully. Next concrete gap: source-derived
postprocessing of those17-node grids into the four output table inputs.

## Modern composition caller isolated

Hash-gated `extract_modern_composition.py` preserves680 static instructions
across492a0,4a2f0 and47f60. The caller builds one grid via48a30 and another
through virtual+10, then calls4a2f0 before packing the combined grid; it also
packs the second grid separately. The composition loop passes first-grid RGB
coordinates into47f60 with the second-grid object as source. Its17-wide loops
cover4913 samples. The sampler contains six coordinate-order branches and
explicit boundary/index correction; neither a trilinear assumption nor direct
copy of descriptor output is justified. The existing live-free trace confirms
11220 outputs equal packer inputs1/3, while14bd0 outputs equal none directly.
Next: replay47f60 coordinate scaling, ordering and boundary handling against
the composed packer inputs. Static extraction runs without executing Canon
code or contacting a camera; py_compile passes.

## Floating tetrahedral composition replay

Added bounded `modern_composition_reference.sample17`: step256/(17-1),
truncate cell indices, apply native last-cell correction only when cell15
has a positive remainder (`coordinate += remainder/(step-1)`), cap neighbor
indices at16, select tetrahedron by remainder order and accumulate four
weighted vertices. Static constants256 and1 are now hash-gated assertions.
The reference intentionally rejects coordinates outside observed0..256;
negative/native exceptional-domain behavior is not silently generalized.

`verify_modern_composition.py` computes4913 composed samples for each mode
using captured descriptor/user grids only as the upstream inputs. Both
composed planar packer inputs match within2.842170943040401e-14 and both
19652-byte packed tables match exactly. No final native packed bytes feed
the calculation. This isolates the missing composition math, but does not
yet remove captured user grids or prove nonidentity/camera behavior.
Next: source-derive11220 settings/grids, join the previously descriptor-derived
grids, then extend the composed proof across nonlinear vectors.

## Source-derived modern user grids joined

Static derived vtablebc544+10 points to4d8d0, not base-class49a10. The derived
builder reads three curves via46cd0, matrix via47030, selectors via471c0,
axes via46c40 (1061/1062), and forwards zero-split arguments through46a10.
The extractor now verifies this call chain and the vtable target. Mode2
uses1029/1062/102b; mode1 uses1021/1061/1023. Missing/unobserved records reject.

`modern_user_grid_arguments` feeds existing11220 independent mathematics from
the PF3 records. Both4913-node user grids agree within2.161e-12. The composition
verifier now also computes both descriptor grids independently, with error0,
so NO captured grid pixels or initialized settings are calculation inputs.
All four final19652-byte tables remain exact (78608 bytes total). Captured
grids/settings/packed tables serve only as validation targets.468 tests pass.
The case is still one Neutral identity input with a recorded descriptor and
DLL-derived cipher keys, not physical compatibility or complete dependency
removal. Next: join header+tables+tail into one source/descriptor replay and
exercise nonidentity source vectors. References and production UI are separate.

## Complete source/descriptor modern carrier replay

`modern_carrier_reference.build_observed_modern17` joins source-derived header,
four independently calculated tables, and optional4096-byte tail. The first
complete83076-byte identity carrier equals the archived normal compiler output
byte-for-byte. All-vector replay is now bounded to the24 successful original
cases; two original compiler failures remain skipped, not silently repaired.
No captured intermediate settings, grids or packed data enter this builder.
Keys are explicitly supplied; verifier obtains them from known local DLL.
This is still an experimental observed-route reference, NOT production install.

Critical audit: `MODERN_VECTOR_DIVERSITY_20261009.json` shows12 distinct dense
source table pairs for each size78980/83076, but just ONE distinct color-table
body in each group. Thus varied LUT fixtures do NOT provide nonlinear color
coverage on this normal compiler branch. Reproducing all these outputs would
reproduce the ignored-LUT behavior, not solve arbitrary-LUT acceptance. Keep
this result distinct from prior acceptance-patched/native installation results.
Next: validate the same independent composition on real varying settings or
the observed dense-table acceptance route, without weakening registration gates.

All-vector process completed normally:24/24 successful archived carriers match
in full (12x78980 and12x83076),1944672 bytes compared;2 original error cases
skipped.469 unit tests pass and changed references/verifiers pass py_compile.
This establishes complete observed normal-route equivalence only, with the
ignored-dense-LUT limitation above explicitly retained.

## Acceptance branch: simple decimation rejected

Inspected production acceptance hooks without executing/attaching them:
the derived17 builder is4d8d0; its observed override reads1070/1071 and calls
MLib196a0 through46a50 with optional curves null, mode1/2, destination17/flag2.
This replaces the user grid, not the descriptor selection/composition loop.

`audit_dense17_sampling_hypothesis.py` verifies original source and archived
patched-payload hashes, then tests six even-node decimation hypotheses (scales
255/255.75/256, caps255.75/256) against24 direct-user-table cases. Only4 cases
match any candidate; no candidate matches all. Therefore identity agreement
does not justify a simple dense33-to17 implementation. The audit is negative
evidence, NOT a newly working acceptance route or physical validation.

Known-hash MLib `extract_dense_converter_windows.py` preserves six bounded
instruction windows, asserting curve preparation and color helper calls1000/
1790 on separate converter paths. Next attribute branch predicates and mode
color-space transformations, then compare proper converter outputs. No native
DLL execution or camera access this turn; laboratory outputs remain private.

## Dense17 converter: endpoint correction solves direct tables

The previous negative result concerned even-node decimation, not all simple
resampling. Aligned196a0 control flow shows flag2 skips the boundary extrapolation
branch; for17 nodes it sets coordinate domain256, caps input at255.75/256,
trilinearly samples33³, scales by256 and clips output to255.75. Optional-curves
null bypasses the later color/curve transforms: their presence elsewhere in
the routine must NOT be asserted as active on this route.

New `dense17_reference.convert17` implements this bounded null-curve path.
The source/archived-patched-payload hash-checked audit now verifies BOTH modes
for ALL12 identity/gains/swap/gray/impulse/local-tent/octant/Superia/Aerochrome
vectors:24/24 direct-user packed tables exact (471648 bytes). This is useful
nonlinear evidence with changed tables, unlike the earlier normal-route sweep.
Still not complete accepted-carrier equivalence or physical camera validation.

Static extraction was corrected to decode once from196a0 and select bounded
windows from that aligned instruction stream; arbitrary starts had introduced
a bogus instruction at198c0. Constants.9990234375,256,255.75 are hash-gated.
471 unit tests pass, including identity endpoint/layout and clipping/geometry.
Next: combine these source-derived accepted user grids with descriptor grids
and verify the two composed tables, then the auxiliary1f02 generation.

## Complete accepted carrier replay:12 nonlinear vectors

`verify_accepted_modern_tables.py` uses the hash-verified original PF3s and
archived acceptance-modified83076-byte payloads fromPF3_ACCEPTANCE_PATCH_PROBE.
It independently calculates descriptor grids, null-curve dense17 user grids,
tetrahedral composition, all four packed tables, control/header serialization,
and the auxiliary compact tail from source table1070 using compact_flag1 and
coefficientModeFalse. No captured intermediate grids/settings are calculation
inputs. All12 complete carriers match byte-for-byte:996912 bytes, including
gains, channel swap, gray, localized edits, Superia and Aerochrome.

The auxiliary candidate check preserves ambiguity: gray can also match source
table2, so uniqueness is NOT asserted. The fixed table1 selection follows the
observed auxiliary workflow; every vector matches that selection. An initial
overstrict uniqueness assertion rejected gray and was corrected, not hidden.

This proves archived accepted-route equivalence for the recorded modern
descriptor/Neutral fixtures, not physical camera behavior, all base styles,
all descriptors, independent cipher provenance or independent USB transport.
The original archive predates this replay; its payload hashes are checked,
but no new native trace/physical experiment was run. Production hooks and UI
remain unchanged. Next extend accepted composition across base styles and
descriptor families, then expose a strict reusable offline compiler reference.

## Reusable accepted reference and six-base normal-route extension

Experimental `accepted_modern_reference.build_accepted_modern17` now exposes
the independently calculated accepted route. All12 archived Neutral83076
carriers still match completely through this reusable implementation. It is
not imported by the production install workflow; keys/descriptor remain
explicit inputs, and other bases on this accepted route remain unverified.

The separate six-base NORMAL-route sweep initially matched Standard/Neutral
but failed Portrait/Landscape/Faithful/FineDetail. All four17-node tables and
headers were already exact; only the4096-byte auxiliary tail differed.
Static475c0 predicates4776e..4777f select the first quantization matrix iff
style81/84 ANDmode1, otherwise the second.49e00 itself only packs integers.
`pack10_for_style` now models that selection. The six archived83076 carriers
all match byte-for-byte (498456 bytes), using a borrowed recorded descriptor.
Evidence: COMPACT_STYLE_BRANCH_20261009.json and
SIX_BASE_MODERN_SOURCE_PROOF_20261009.json. No DLL execution/camera access.
474 unit tests pass. This resolves normal-route base diversity, NOT arbitrary
LUT acceptance for all bases, descriptor families, or physical compatibility.

## Full33 source-record replay without captured initialized arguments

`full33_packing_reference.source_full33_table` derives11220 arguments from
host-ordered source records, then evaluates all35937 coordinates and stores
planar32768-scale uint16 channels. `verify_source_full33.py` checks four retained
old-selector vectors (1023/102b, H0/H5), both modes:8/8 tables byte-exact,
1724976 bytes. It never reads captured initialized arguments or grids as
calculation inputs. Payload hashes match the older field report; mutated-source
hashes are newly recorded, not pretended to be historical provenance.
Report SOURCE_FULL33_PROOF_20261009.json explicitly states that limitation.

A separate diagnostic finds the372-byte prefix of1023_H0 matches the existing
17-node prefix after changing only data-size words4 and40 to431616-40. This is
one archive observation, not yet a generalized full33 header implementation.
Next attribute the full33 serializer branch statically, then verify complete
source-only carriers rather than table-only equality.475 unit tests pass and
the new function/verifier compile. All24 prior normal78980/83076 replays remain
exact after the style-tail correction. No native execution or camera access.

## Complete full33 normal-route replay

Static branch56586 confirms control252 + total69504h =431616 and duplicated
data-size694dch+252=431576. The existing modern envelope is reused: name/style,
Basic/detail controls, deadbeef markers, control serialization512e0,100c at368.
It writes1f04 at372 and1f03 at215994, each34a46h=215622 bytes, without the
compact-table XOR transform. FULL33_HEADER_STATIC_20261009.json hash-gates the
DLL and asserts the relevant instructions. Missing-control defaults are not
enabled by the new full33 prefix helper.

`full33_carrier_reference.build_observed_full33` now joins that prefix with
two source-derived tables. All four retained selector carriers match their
archived payload hashes byte-for-byte:1726464 bytes. SOURCE_FULL33_PROOF now
reports both8 table checks and4 whole-carrier checks.476 unit tests and
py_compile pass. Production install paths remain untouched.

The next acceptance gap is distinct:4cc40 calls virtual+18 for each mode,
then4c340 and4be30 before storing1f04/1f03. The observed normal override4dac0
constructs a33-node grid with source curves/matrix/selectors/axes through46a10;
that does not itself prove arbitrary1070/1071 tables reach this serializer.
Next attribute the alternative dense override and its gates, rather than
assuming full33 normal-route equality establishes arbitrary-LUT acceptance.

## Full33 acceptance clarification and cross-language conversion proof

Inspection of production dynamic_camera_agent.js confirms the431616 path calls
applyFull33Tables AFTER successful Canon GetPropertyData when no17/10 grid path
was observed. It directly rewrites both full33 tables with encodeFull33Planar.
Thus its arbitrary-LUT path is app-level output-table replacement, not simply
a compiler acceptance-gate change. The existing FULL33_HOOK_EXACT_VALIDATION
report's15 virtual cases check this policy, not unmodified compiler acceptance.
This distinction was already implicit in code but must remain explicit in
portability claims. No production hook change was made.

The full33 static report now also asserts derived vtablebc544+18 ->4dac0 and
its33-node curve/matrix/selector/axis calls through46a10. Portable helper
encode_app_dense_full33 validates the full215628-byte source envelope and
reuses existing compiler_regression.full33_planar arithmetic, avoiding a
duplicate conversion implementation.

verify_full33_js_policy extracts ONLY the real pure encodeFull33Planar JS
function and executes it in Node, without Frida/Canon. It matches Python for
all4096 source levels with asymmetric channels and a nonlinear vector:
2/2 complete215622-byte tables exact. FULL33_APP_POLICY_CROSS_LANGUAGE_20261009
records source/agent/output hashes.478 unit tests pass. This establishes
portable conversion-policy equality, not a new Canon-native breakthrough or
physical compatibility. Next obtain whole dense-carrier equivalence where
retained evidence permits, and continue independent registration transport.

## Compact16752 prefix source reconstruction

Static556fe serializer branch uses a uint16 data-size at40, style42/name44,
Basic76, markers92/96, detail100/104, control marker48h at108, encoded control
at112 and100c at364. It is NOT the modern372-byte prefix copied unchanged.
`compact_header_reference.build_compact16752_prefix` reuses strict source-field
conversion but maps this368-byte layout explicitly. Missing controls remain
rejected; other compact sizes/default branches are not generalized.

First replay failed all36 cases by one byte: inherited marker4c instead of48.
Instruction557ac/557b1 confirmed the distinct marker; corrected reference now
matches36/36 source-derived prefixes across12 vectors each for M50,7DII,5DS
archive routes. Source/payload hashes are checked; COMPACT_HEADER_PROOF and
COMPACT_HEADER_STATIC retain evidence. This is header equality only, not
complete compact-carrier or physical camera compatibility. Next source-derive
the four compact blocks and their descriptor/user composition.
