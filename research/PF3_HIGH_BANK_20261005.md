# PSE alternate-bank investigation

Scope: hash-checked installed x86 EdsCFParse, own hidden laboratory processes,
no camera session, no installed-file changes, no compiler acceptance patch.
Sources are the two archived PSE-converted Emerald PF3s; dense-grid donor is
the archived Aerochrome PF3. Read-only references are mutated only in memory.
All source, descriptor and DLL hashes remain unchanged.

## Completed causal experiments

Twenty stock compiles: two sources, M50/R8 IDs with the recorded R8 descriptor,
and control / grid1070 / grid1071 / bank9011zero / bank9011one variants.
Every compile succeeds. Each mutated variant yields byte-identical output to
its matching control. Grid readbacks confirm that the donor replaces the
requested grid and survives setting the camera ID and descriptor. Thus the
negative result is not explained by a rejected or immediately lost mutation.
Neither the alternate bank's presence nor its 9011 flag makes these tested
stock paths include arbitrary dense grids.

Eight positive-control compiles on unchanged Emerald: control, reference-bank
9032=2, active1032=2 and active1011=1, for the same two IDs. Reference-bank
saturation and active1011 changes leave native output identical. Active
saturation changes exactly one metadata byte: offset84 for M50, offset88 for
R8. This is evidence of scalar control propagation, NOT a changed color LUT.

Eight further compiles query PF3 aggregates alongside individual records.
The file-reference aggregate115 is32bytes/type102. Reference9032 mutations do
not change it; active1032=2 changes its word at offset8. Aggregate8115 size
query returns80 in this API, despite individual40009032 being readable and
writable. Do not infer that a setter branch implies a public getter exists.
These115 calls concern PF3 files only, not EDSDK registration state.

## Static corroboration and limits

59 immediate-value candidates found for8000; unrelated flag/constants must
not be conflated with record IDs. In the confirmed set-property function
53d00, the block starting53d69 extracts8000 from the requested ID. The Basic
aggregate115/8115 setter combines it with40001030..40001035. The lower setter
51590 retains low16bits when forwarding4000xxxx file properties at51680.
This supports an independently addressable alternate Basic bank, not a
universal compiler-enable flag.

## Evidence

Private outputs under ../tmp/PF3_FIELD_EXPERIMENTS_20261004:

- HIGH_BANK_COMPILER_20261005/HIGH_BANK_RESULTS.json
- HIGH_BANK_CONTROLS_20261005/HIGH_BANK_RESULTS.json
- HIGH_BANK_AGGREGATES_20261005/HIGH_BANK_RESULTS.json
- HIGH_BANK_STATIC_REFERENCES_20261005.json

Reproducible tools: camera_install/high_bank_research.py and high_bank_probe.js.
No raw payload is saved by these tools; hashes, differences and property
snapshots are retained. The generated configured agent is a private artifact.

## Next useful work

1. Observe the compiler's record reads at the table-selection boundary for
   genuine PSE files versus our arbitrary-grid files; distinguish bank
   selection, conversion and discarded output without overriding anything.
2. Trace the lifecycle of the alternate bank in PSE import/Reflect operations
   on scratch files only. Test whether serialization preserves or regenerates
   those records, while separately tracking checksum and main-grid changes.
3. Continue the unresolved1460-byte legacy1007 origin and writer analysis.
   Neither invented zero buffers nor successful rcGet prove a valid style.

These ID/descriptor combinations are offline test inputs, not physical
compatibility claims for either camera or every Canon model.

## Canon serialization roundtrip

Six scratch files from the two PSE sources: copy all records, omit the fourteen
high-bank records, and change only9032 to2. All six have valid Canon-generated
checksums and complete terminated record lists. Copy-all preserves every data
record/type/length; omission removes exactly the fourteen90xx entries; the
scalar mutation changes exactly9032. Sixteen stock compiles (four original
controls plus twelve scratch cases) give byte-identical carriers for each
corresponding source and virtual ID. The bank is genuinely retained by Canon
serialization, but its omission/change does not affect these compiler paths.

Three further Canon-serialized scratch files preserve the full bank and change
only1070 or1071, using the Aerochrome donor. Record comparisons establish that
only the requested dense grid changes. Eight compiles including original
controls again return identical complete payloads. Therefore the earlier
negative in-memory mutation result also holds after serialization/reopening.

## Distinguishing preparation from final assembly

Six read-only selection traces found no readDense calls during final carrier
GetData, while dense10/dense17 builders ran. This observation alone does NOT
mean the tables are never read: four follow-up traces split input preparation
from final compilation. M50 input preparation calls readDense46fd0 for indices
1/2, from4cecf. R8 input preparation in these cases does not. No90xx lookups
were observed in either measured phase.

Four cache-stage probes then show M50 creates4096-byte1022/102a on input
preparation and retains their hashes after compilation. R8 creates zero-size
derived nodes initially and19652-byte1022/102a after compilation. The separate
stock dense17 builder4d8d0 reads curves1018/1019/1065, matrix1021/1029 and
selectors1061/1062/1023/102b, rather than directly reading1070/1071.

Four final consumed-record traces compare checksum-verified copy-all versus
serialized1070-only mutation. M50's prepared1022 hash changes from4d765e5f...
to d7b48637..., proving the new dense grid reaches its prepared cache. Raw
getter4ef20 reads that changed cache successfully four times in final assembly.
Yet all four assembled color blocks and the complete returned payload stay
identical. Static assembly56c40..56d8e explains the loss:

-56c57/56c7b write1022/102a to the first two4096-byte regions.
-56c9c/56cc0 write them again to regions at relative2004/3004.
-56d1f/56d3a overwrite the first pair from1f00/1f01 after4c770.
-56d6e/56d89 overwrite the second pair from1f00/1f01 after4d660.

The mutation affects the prepared cache but not the regenerated1f00/1f01
hashes. The identical destination expressions and the before/after consumed
hashes establish this specific overwrite, not a general unsupported claim that
every compiler route discards dense tables in the same manner.

Dense reader46fd0 has three direct call sites (4cd9a/4ceca/4cf8a), all inside
converter4cd10. No direct call-to4cd10 instruction was found; its address is
stored in the known context vtable atbc564, slot20 relative tobc544. Constructor
4c610 installs that vtable. A failed scan of4cca0 was an incorrect candidate
address and is NOT evidence about the actual converter. Track the actual
virtual caller dynamically next.

Two final observer runs locate the real converter caller at573be during M50
input preparation (return1). The R8 run has no converter call. Evidence:
HIGH_BANK_VIRTUAL_CONVERTER_CALLER_20261005/HIGH_BANK_RESULTS.json. Next trace
the controlling branch around573be and its descriptor/ID-dependent dispatch,
then compare it with the final-assembly overwrite proved above.

Additional private evidence: HIGH_BANK_ROUNDTRIP_20261005,
HIGH_BANK_SERIALIZED_GRID_20261005, HIGH_BANK_SELECTION_TRACE_20261005,
HIGH_BANK_INPUT_SELECTION_TRACE_20261005, HIGH_BANK_DERIVED_CACHE_TRACE_20261005,
HIGH_BANK_CONSUMED_CACHE_TRACE_20261005, DENSE_READER_CALLERS_20261005.json and
DENSE_CONVERTER_CORRECTED_CALLERS_20261005.json.

## Family dispatch and preservation versus overwrite

The virtual caller is now explained statically. Thunk4cd00 dispatches context
vtable slot20 to4cd10. Caller572d0 sets the target ID, runs initialization57110,
then calls family classifier4eaf0. At57399/573a5/573b1, classes8/9/10 skip
the converter; other classes call the thunk at573b9 (return address573be).

New independent extraction `compiler_family_research.py` reads four bounded
selector/jump tables and explicit exceptions from the hash-known revision.
Native comparison in a fresh hidden host calls only the leaf classifier with
12-byte scratch contexts. **87/87 recorded IDs agree**, covering all ten
internal classes. No EDSDK, reference mutation, camera session or patch.
These classes are internal dispatch numbers, not physical support assertions.

Class counts:1=2,2=2,3=3,4=4,5=23,6=5,7=34,8=1,9=10,10=3.
Classes1/2 are the four legacy initialization-error cases; class7 also includes
the ten old skipped-initialization IDs and two older errors. Therefore the
numeric family classifier alone does not predict compile success.

Twenty stock compiles use the same PSE Emerald file and recorded R8 descriptor,
one representative per class, control versus in-memory1070 Aerochrome grid.
Repeated with a read-only descriptor-capability observer, same results:

| Internal class | Representative | Payload bytes | Changed output bytes |
|---|---|---:|---:|
|1|5D|compile error|not comparable|
|2|30D|compile error|not comparable|
|3|1D III|8528|3828|
|4|450D|16720|7659|
|5|M3|16744|7659|
|6|7D II|16752|7659|
|7|M50|16752|0|
|8|1D X III|78980|0|
|9|R5|83076|0|
|10|C50|431616|0|

This disproves a blanket "stock compiler always discards arbitrary tables"
statement. It does NOT validate physical cameras or genuine descriptors for
the representative older bodies: this is explicitly a shared-descriptor test.

Consumed-record observers distinguish the actual assemblies:

-Class3 reads prepared1022/102a directly at550eb/5510e.
-Classes4/5/6 read1022/102a twice each, then1f00/1f01 only once each
 (5532c/55347,55671/5568c,55ae8/55b03). Their changed cached regions survive.
-Class7 reads1022/102a twice but overwrites both pairs with1f00/1f01,
 including the second pair after4d660; no changed cache survives.
-Class8 reads four19652-byte records; class9 also reads4096-byte1f02.
-Class10 never enters the observed10/17-node builders (full33 route).

Descriptor gate4b4f0 is true for both grid indices in classes4/5/6/7, with
additional4d660 callers only for class7. Thus the presence of that capability
gate alone does not explain the difference; destination overwrite count does.
The next useful branch is to independently verify preserved versus overwritten
region boundaries, extend compact conversion to classes1/2's2916-byte requests,
and inspect full33 consumption without transplanting model-specific payloads.

Evidence: COMPILER_FAMILY_STATIC_20261005.json,
COMPILER_FAMILY_NATIVE_20261005.json,
HIGH_BANK_TEN_FAMILIES_20261005/HIGH_BANK_RESULTS.json,
HIGH_BANK_TEN_FAMILIES_DESCRIPTOR_GATE_20261005/HIGH_BANK_RESULTS.json.
Python compilation, JavaScript syntax check and243 automated tests passed.

## Exact output-region proof

`payload_region_research.py` independently decodes each observed compact or
17-node output region with the two known XOR seeds, then compares full bytes
against records captured by the read-only raw getter. It does not generate,
replace or save any camera payload. Unknown geometries remain unmapped.
Twenty further stock compiles confirm these exact positions under the same
shared-descriptor conditions as above:

|Class|1022/102a positions|1f00/1f01 positions|
|---|---|---|
|3|336 /4432|not read by this assembly|
|4|8528 /12624|336 /4432|
|5|8552 /12648|360 /4456|
|6|8560 /12656|368 /4464|
|7|no exact output match for changed prepared cache|368 /4464 and8560 /12656|
|8|39676 /59328|372 /20024|
|9|39676 /59328|372 /20024, with1f02 at78980|

In classes4/5/6 only the second pair equals prepared1022/102a after1070 mutation.
In class7 no decoded region equals either changed prepared record, while each
region equals the final regenerated1f00/1f01 read for that destination. This
confirms the overwrite using complete bytes, independently of static addresses
or simple changed-output counts.

Full33 was initially invisible to the consumed-record filter: it uses1f03/1f04,
not1f00/1f01, and each record is215622 bytes. Expanding the bounded observer
and comparing plain (non-XOR) regions confirms:

-1f04 at568f3 equals exactly output372..215993.
-1f03 at56914 equals exactly output215994..431615.
-Both records and the whole output remain identical after1070-only mutation.
-Observed source lookups contain curves1018/1019/1065, matrices1021/1029,
 policies1023/102b, and derived1f03/1f04; they do not read1070/1071 here.
-Static builder4dac0 calls46cd0 (curves) and47030 (matrix), builds a33-node
 intermediate, then supplies the derived records. No alternative-camera
 payload transplant is involved.

The missing full33 records in the earlier observer were a filter limitation,
not evidence that the route had no derived records. Tests now cover compact
and17-node geometry, exact/missing matches, unmapped sizes and non-XOR full33.
Evidence: HIGH_BANK_OUTPUT_REGION_PROOF_20261005/HIGH_BANK_RESULTS.json and
HIGH_BANK_FULL33_OUTPUT_REGION_PROOF_20261005/HIGH_BANK_RESULTS.json.
Next: independently reconstruct the full33 planar output from its curves and
matrix inputs and determine which acceptance path chooses dense versus derived
grids, while retaining the older2916-byte initialization problem separately.

## Full33 independent mathematical replay

Two additional unpatched stock compiles retain numeric MLib captures privately:
the Emerald control and1070-only mutation, class10/C50 with recorded R8
descriptor. Reusing `modern_grid_reference.py --experimental-selectors` compares
all33³ nodes and planar packing against both native numeric grids and final
payload regions. **Four captures pass with zero mismatched nodes and maximum
error0.0**, modes1/2 in both compiles; independently packed bytes occur in the
matching final regions. This is stronger than a hash-only unchanged-output
comparison: the existing curve/matrix/selective-axis model explains the
observed full33 output for this source. It is not proof for all possible PF3
curves, matrices, sources, descriptors or physical bodies.

Private evidence: HIGH_BANK_FULL33_MATH_20261005/PRIVATE_MATH_TRACE.json and
INDEPENDENT_MATH.json. Retained numerical payloads stay in the private sibling
tmp directory, never the public package or application resources.

## Additional native selection candidates (2026-10-06)

A fresh hash-gated executable-section immediate scan finds11 references to
1070/1071 and1f03/1f04. In addition to the previously traced568xx output
assembly, a507xx sequence reads1f04/1f03 into the same372/215994 offsets with
215622-byte lengths and a431616-byte output allocation. It calls49420 before
those reads and returns0x51 if its low-byte result is false. The entry and
selector conditions of this alternative sequence remain to be verified;
linear candidate disassembly alone cannot establish reachability or a new
acceptance path. A deliberately off-boundary exploratory decode at504a0 was
not used as evidence. Existing instruction-aligned scan contexts are retained.

Private evidence: DENSE_SELECTION_STATIC_REFERENCES_20261006.json and
ALTERNATE_COMPILER_MODE_STATIC_20261006.json. The latter includes419 candidate
references, mostly the ubiquitous4949 parameter; this is an inventory, not419
distinct compiler modes. Next isolate the enclosing selector and49420 call
before invoking any scratch-only native probe. No production code changed.

The enclosing function is4f2d0 (confirmed frame prologue); its class10 jump
table50b7c selects504ac. The49420 routine creates a base context via46be0,
whose vtablebb5e4 slot18 calls49b50. That builder derives a33-node grid from
curves/matrix/selective adjustments, not a direct1070 copy. The PF3 helper
context instead uses vtablebc544 slot18=4dac0. Both still need distinct names
and dispatch evidence; their similar output geometry is not equivalence.

New read-only observers of4f2d0/54cd0/49420/49b50/4dac0 establish that the
stock Emerald class10 control and1070 mutation call54cd0 and4dac0 twice,
but none of the three base-context functions. Both output431616 bytes and
remain identical. This rules out claiming507xx is an already exercised
alternative in this ordinary PF3 compilation. Existing content-dispatch
evidence has slot0c=54cd0 for Identity PF3, consistent with the observation.
Private evidence: FULL33_CONTEXT_DISPATCH_20261006/HIGH_BANK_RESULTS.json.
JavaScript syntax and257 tests pass. Next compare an archived official PF2
reference to determine whether it exercises the base-context dispatch.

The official archived Emerald PF2 control and scratch1070 mutation both
exercise4f2d0,49420 and49b50 twice on the same class10/R8-descriptor setup.
Neither calls54cd0 nor4dac0. Both compile successfully to431616 bytes but
the mutation leaves output identical. Thus the507xx candidate is confirmed
as the PF2/base-context path for this fixture, not a newly discovered means
of making arbitrary PF3 tables accepted. PF2/PF3 dispatch differs even when
output family and size are equal; swapping extensions cannot remove this.
Private evidence: PF2_FULL33_CONTEXT_DISPATCH_20261006/HIGH_BANK_RESULTS.json.
All input files and the installed compiler remain unchanged.

## Ten-class paired format matrix

Forty unpatched compiles cover the official Emerald PF2 and its archived
PSE-converted PF3, control/1070 mutation, one representative per native-verified
class1..10, all with the same recorded R8 descriptor. Context hooks observe
baseOutput for every PF2 cell and pf3Output for every PF3 cell, including
failed class1/2 generations. No mixed context was observed in any cell.

Classes1/2 fail for both formats (8164/8168-byte reported sizes); do not count
reported size as successful output. PF2 classes3..10 succeed and all ignore
the1070-only mutation in final bytes. PF3 classes3..6 change3828/7659 bytes,
whereas classes7..10 remain unchanged. Thus format-dispatch and output-family
selection are independent dimensions. This is stronger than the previous
single-class comparison but remains one source pair and a borrowed descriptor,
not a compatibility matrix for physical bodies or all PF2/PF3 documents.

context_dispatch_research.py independently summarizes these observed events,
rejects unsafe/duplicate/mixed-context evidence and leaves missing observations
unknown rather than inferring a context from a filename. Its four new tests
bring the suite to261 passing tests; py_compile passes.
Private evidence: PF2_PF3_CONTEXT_FAMILY_MATRIX_20261006/HIGH_BANK_RESULTS.json
and PF2_PF3_CONTEXT_FAMILY_MATRIX_SUMMARY_20261006.json.

All ten PF2 mutations return SetPropertyData rc0; immediate rereading of1070
returns rc0/215628 bytes and the same full donor-grid SHA256 in every cell.
The lack of final changes is therefore not a rejected write or missing
in-memory table. It is bounded evidence of a stored but unused dense record
in this PF2 generation path. No serialized PF2 alteration is claimed here.

## Version-to-context creation

Static ae00 empty-reference creation tests(version16&ff00)==3000 and passes
the full version to53f70; other versions fall back to53290 with2001. This
must not be used to describe file-open behavior. Read-only constructor hooks
on two actual archived sources observe the file-open path instead:
PF2 header00002000 invokes53290(version2000), return siteb02c; PF3 header
00003000 invokes53f70(version3000), return siteb002, then its inherited53290
constructor receives3000 at53f87. That second constructor is inheritance,
not evidence that a PF3 switches back to the PF2 output path.

Instruction-aligned file-open branchafbc masks the version withff00, accepts
2000 atb004 (53290), and3000 or4000 atafda (53f70), passing the full low16-bit
version in either case. Header PSP is checked separately atafaf. No40xx file
was exercised here; a static constructor branch is not format/camera support.
format_context_reference.py separates these two entry points and leaves
unmapped file-open versions unknown.264 tests and py_compile pass.
Private evidence: FORMAT_CONTEXT_VTABLE_REFERENCES_20261006.json and
FORMAT_CONSTRUCTOR_TRACE_20261006/HIGH_BANK_RESULTS.json. Original files,
Canon DLLs and camera state unchanged. Next investigate40xx initialization
without confusing a header-only diagnostic with a valid newer-format file.

## Archived40xx fixture and strict API status

Reinspection of the existing231-unique-source inventory finds one actual
00004000 source: Fine Detail (SHA256126611fb855066506b4752c287d51d2c62f07349679280f7378206f44fc4dd02),
434511 bytes,28 serialized records, correct checksum and terminator, repeated
across seven archive paths. No new format or redistribution fixture was made.

Twenty unpatched compiles observe53f70(version4000) followed by inherited
53290(version4000). Classes7..10 pass all API gates and ignore1070 mutation.
Classes1..6 return rcId7. Classes3..6 subsequently return rcGet0 with a sized
buffer, but the strict driver correctly refuses to label them compiled: a
later successful call must not erase the earlier ID-setting failure. Classes
1/2 additionally return rcGet80. These are virtual/shared-descriptor outcomes,
not physical support limits of Fine Detail on every model.

VERSION40_FINE_DETAIL_CONTEXT_MATRIX_20261006/HIGH_BANK_RESULTS.json retains
the complete call status. envelope_version_research.py creates private,
clearly labelled header-only diagnostics from checksum-verified sources,
preserving every byte after offset4 and the original source. Changing4000
to3000 will isolate the version gate, not constitute a valid style conversion
or something to install. Python compilation and266 tests pass.

Static4000 immediate references elsewhere (d3b0/d430/d7f3, among others) are
not assumed to mean file versions: they compare API arguments and need their
own attribution. Only the confirmed file-open branch is interpreted here.

Changing only Fine Detail's envelope4000 to3000 does not clear any rcId7:
all20 diagnostic cells retain the same ID-setting outcomes. Native setter
572d0 reads1009 at573cd, checks base style88 at573e1, then applies an explicit
ID list plus three bounded jump tables. Rejected IDs branch to574c4, which
sets result7. This is a base-style/ID gate, not the version mask alone.

fine_detail_policy_research.py extracts those tables (574f0/57518/57558),
validates their two destinations, and predicts rcId for the original matrix:
20/20 agree. Its explicit IDs match the previously mapped compact-prefix
policy set, but the two policies remain separately named and extracted.
Later rcGet0 must never authorize a compile after this rejected rcId.
No gate was bypassed, no source base was renamed, and the diagnostic4000→3000
files are not installable conversions.268 tests and py_compile pass.
Private evidence: VERSION40_AS30_CONTEXT_MATRIX_20261006/HIGH_BANK_RESULTS.json
and FINE_DETAIL_ID_GATE_PROOF_20261006.json.

## Fine Detail full recorded-ID sweep

The driver can now select every native-verified model ID and perform control
compilation only.87 Fine Detail compiles (same recorded R8 descriptor) complete
with input hashes unchanged. Independently extracted ID gate agrees87/87:

|Observed outcome|Count|
|---|---:|
|rcId0, rcGet0, strict compile pass|40|
|rcId7, rcGet0, strict compile refused|33|
|rcId7, rcGet80, strict compile refused|4|
|rcId0, rcGet80, strict compile refused|10|

The ten latter IDs are the previously mapped initialization-skipping old
models, not Fine Detail-specific rejections.37 recorded IDs hit the Fine Detail
gate; the extracted global rejection set contains41 IDs, including four not
represented in this87-ID baseline. No claim is made about those four runtime
outcomes. The independently extracted compact-prefix policy set is exactly
equal to the41 rejection IDs in this exact DLL; equality of these two sets
does not equate descriptor capability, RAW support and camera installation.

The verifier now requires an observed pre-ID PF3 aggregate114=88 (four bytes,
rcGet0), so it cannot silently apply the Fine Detail prediction to Neutral or
unproven sources. The current269 tests and py_compile pass.40 compiler passes
are not40 physically supported bodies: default-family fallback and the shared
descriptor still limit the virtual evidence.
Private evidence: FINE_DETAIL_ALL_RECORDED_IDS_20261006/HIGH_BANK_RESULTS.json
and FINE_DETAIL_ALL_ID_GATE_PROOF_20261006.json. Next keep these model gates
separate from the unresolved old initialization and missing1007 metadata.
