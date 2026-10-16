# Internal descriptor capability words — private offline evidence

Known x86 compiler hash, own hidden hosts, untouched source/DLL/descriptor inputs.
No EDSDK, camera sessions, EOS Utility attachment or installation.

Static reader4b4f0 gets style ordinal via472d0 and chooses a copied internal
descriptor using policy4c3b0.47250 copies1d44 bytes;47290 copies39cc bytes.
If copying fails, the gate returns false. Otherwise it compares a uint16
word to exactly1:

- Compact: offset1ee + ordinal×5d8 + index×2.
- Modern: offset1ee + ordinal×9a0 + index×2.

The offsets are into the copied internal descriptor, NOT the incoming raw
01000210 blob. Neutral ordinal3 gives offsets4984/4986 or7888/7890 for
indices1/2. Static code4b53a/4b572 corroborates these formulas.

Twenty stock class-representative compiles compare R8 and1300D descriptors
(`DESCRIPTOR_FLAG_WORDS_R8_20261007`, `..._1300D_20261007`). Four follow-ups
retain bounded deduplicated internal copies for M3/M50 in
`DESCRIPTOR_INTERNAL_COPIES_R8_20261007`, `..._1300D_20261007`.

M3 compact copies succeed with either descriptor; observed words0/0 disable
both gates. M50 modern copy succeeds with R8 and words1/1 enable both;
with1300D the copy fails and both gates disable. M50 still compiles in that
case, so a false gate alone must not be mislabeled rc81.

R5 and1DXIII reproduce rcGet81 with the1300D descriptor without passing
through4b4f0. Follow-up read-only traces now establish a different failure
chain: 48a30 calls47290, whose node-copy46de0 refuses a14796-byte request
against a7492-byte internal node (storage type65535). 48a30 returns false,
492a0 returns false, and the output branch returns81. R5's49830 tail also
observes the same failed reader; its output branch sets81 at56459 (the
main preparation failure sets81 at56413).

Private DESCRIPTOR_NODE_LENGTH_R8_20261007 and
DESCRIPTOR_NODE_LENGTH_1300D_20261007 retain four stock compiles. With R8,
both routes read14796 from a14796-byte node successfully. With1300D,
all three observed reads request14796 from7492 and fail. Static46dee..46dfd
implements requested>stored rejection unless type2, which may truncate.
descriptor_read_reference independently checks this guard, without treating
guard passage as sufficient for successful copying. This is evidence for
these inputs/routes, not a universal descriptor-compatibility rule or LUT
rejection. No fabricated padding or replacement descriptor is installed.

The three captured successful internal copies are not equal to the same-length
incoming prefix, nor to the prefix starting at offset280. Length difference
alone is not a header-removal proof. The native copy/normalization mechanism
remains to be traced; do not read capability flags directly at these offsets
in arbitrary raw captured descriptors.

Further PRIVATE DESCRIPTOR_IMPORT_R8_20261007 and
DESCRIPTOR_IMPORT_1300D_20261007 runs observe the inputs-stage store51500
for record210, without replacing arguments. Its callers51b6f and52093
deliver7492 and14796 bytes respectively. The R8 imported buffer matches
the later47290 copied buffer byte-for-byte. The1300D run uses M50's modern
reader, which fails, so it cannot establish an import-to-copy equality.
These imports place the normalization before record storage, rather than
inside the output reader. Function51b90 begins by copying39cc bytes and
then transforms structured fields before storing210 at5208e; the exact
field transformation still requires a complete independent replay. The
initial51b20 disassembly begins mid-instruction and is not an entrypoint
proof; only the aligned51b90 entry and observed call returns are relied on.

DESCRIPTOR_IMPORT_SOURCE_R8_20261007 additionally captures the actual51b90
argument. Independent descriptor_import_reference reproduces all14796 bytes
of the stored buffer exactly: for each of six9a0-byte style regions, decode
240-byte blocks at10/1f4 with seed3fcb and100/2e4 with seedc7. The helper
2e30 jumps to2db0, the already independently mapped XOR cipher. Remaining
bytes are preserved. The apparent word/dword reconstruction instructions
retain the original byte order (an initial exploratory middle-byte swap was
incorrect and removed before recording the exact result). This is not an
arbitrary raw-file decoder: input is the observed import-function argument.
Compact import and the outer descriptor envelope still need independent
replay. No keys, descriptor buffers or captured payloads are published.

Compact follow-up:51760 uses five5d8-byte style regions with the same four
240-byte blocks and seeds as the modern importer. Independent
normalize_compact matches all7492 bytes of the1300D import exactly in
DESCRIPTOR_COMPACT_SOURCE_1300D_20261007, including the subsequent reader
copy. Its R8 companion instead enters51b90 and stores14796 bytes even for
M3:47250 subsequently copies exactly the first7492 bytes of that modern
normalized buffer, without changing its style stride. Independent modern
replay also matches that import exactly. Thus reader success on a larger
descriptor does NOT establish layout/semantic compatibility. This supersedes
the compact-import pending item above; the outer envelope remains unresolved.

Raw-prefix/selection follow-up: the captured import argument is exactly the
raw prefix at offset0 for both fixtures, not offset280. The280 extra bytes
form a suffix, preserved as opaque data by normalize_observed_raw. Reading
the incoming first uint32 as little-endian yields2000000a (1300D) and
2000000f (R8). Aligned51590 disassembly selects compact for20000001 or
versions >=20000003 and <20000008, and specially2000000a; all remaining
unsigned versions >=20000008 select modern. Lower unaccepted values return81.
The branch5169a reads the descriptor's own first field, not camera ID.
There is no upper-version acceptance guarantee beyond this observed branch.

Independent raw replay matches the entire stored210 record for both archived
inputs. The strict wrapper accepts only observed length+280 geometries and
does not claim the suffix is ignored elsewhere. It is not a universal raw
descriptor schema. The field semantics and purpose of the suffix remain open.
Tests cover version boundaries, rejected versions, opaque-tail retention,
length rejection and both transformation geometries without private fixtures.

Reproducible CLI: python -m camera_install.descriptor_import_reference
REPORT DESCRIPTOR DLL OUTPUT. It checks offline/no-mutation provenance,
descriptor hash, exact DLL hash against the native inputs, raw-prefix source,
selected native store caller, complete independent normalization, and all
captured reader prefixes. It refuses empty/missing observations rather than
counting them as exact. PRIVATE DESCRIPTOR_RAW_IMPORT_R8_PROOF_20261007.json
and DESCRIPTOR_RAW_IMPORT_1300D_PROOF_20261007.json each verify one native row.
Output retains only hashes/counts, no proprietary buffer bytes. A successful
proof explicitly does not assert camera compatibility or physical validation.

Parameter-selection follow-up: aligned48a30 reads the modern descriptor,
then48a82..48ab1 copies60 dwords from104+ordinal*9a0+index*f0. The reference
modern_parameter_matrix implements this static formula for observed indices
1/2 only. A mid-function observer at48ab3 captured an identity-like matrix
but changed both stock compiles to rcGet80 (private
DESCRIPTOR_MATRIX_ARGUMENTS_R8_20261007). Those runs are instrumentation-
affected and NOT native-valid evidence; the mid-function hook was removed.
No consumer/runtime equivalence is claimed from that capture. Further
observation should use stable entrypoints, not reuse the disruptive hook.

Stable observer follow-up DESCRIPTOR_MLIB_MATRIX_R8_20261007 restores
successful stock1DXIII/R5 compilation with the original baseline payload
hashes. Existing MLib entry observers retain five successful14bd0 calls:
mode1/2 for both routes, plus R5's tail preparation mode1. All five240-byte
matrices match the independent normalized Neutral descriptor selections.
match_modern_matrix_calls preserves possible indices[1,2] because both
Neutral matrices in this fixture are equal; it must not infer the index from
this coincidence. Private MATRIX_CONSUMER_PROOF.json stores hashes/matches,
not bytes.11220 mode2 has a different matrix and is not claimed to consume
the same original selection unchanged. This is consumer byte equality, not
proof of every parameter's semantics or compatibility of a borrowed descriptor.

Five-point expansion:48b98..48ca2 selects the header at
3f8+ordinal*9a0+index*1e4, reads uint16 kind/count, and expands each40-byte
group to84 bytes: uint32 point-count5 followed by20 extended words, unsigned
at positions0/4/8/12/16 and signed at the other positions. Independent
modern_axis_parameters reproduces all five176-byte axisParameterBlock
observations in the stable trace exactly. Both Neutral indices match, so
index ambiguity remains explicit. Tests include -32768/-1/32767, unsigned
60000, group-size limits and exact output layout. Four-point oldParameterBlock
captures are null in this fixture and are not falsely counted as validated;
their expansion and subsequent adjustments remain a separate pending branch.

Four-point preparation follow-up: stable46a30 entrypoint with observed caller
48ce5 exposes argument7 before the delegated MLib call. In PRIVATE
DESCRIPTOR_FOUR_POINT_R8_20261007 both routes retain original successful
baseline payload hashes. Independent modern_four_point_parameters expands
the header at2d0+ordinal*9a0+index*104 and each32-byte group to68 bytes:
point-count4 plus16 words (every fourth unsigned, others signed). All four
native buffers match exactly: index1/count5/348bytes and index2/count6/416bytes
for1DXIII and R5. Unlike equal matrices/axes, these blocks distinguish the
indices. The earlier null oldParameterBlock at14bd0 does not establish that
four-point data was absent from upstream preparation; its later handling
inside MLib1c190 remains to trace. No mid-function instrument is retained.

MLib1c190 follow-up resolves that apparent absence. Argument7 contains the
four-point block; argument5 is the split count, zero in48cae..48ce0. At1c1bd
zero takes1c394, forwarding null as14bd0's old block and the complete block
as its additionalParameterBlock. In the existing stable PRIVATE math trace,
all five additional blocks match independent expansion exactly. Combined
match_modern_descriptor_calls checks matrix, axes and four-point block
together and now identifies unambiguous indices1/2/1 for the relevant calls.
DESCRIPTOR_CONSUMER_PROOF.json records the five matches without buffer bytes.
The complete path raw descriptor -> normalization -> selected/expanded
arguments -> MLib14bd0 is independently matched for Neutral in these two
successful offline routes. Nonzero split behavior and other styles still
need separate evidence; this is not universal physical compatibility.

Six-style extension DESCRIPTOR_CONSUMER_SIX_STYLES_R5_20261007: six archived
base PF3s (Standard81,Portrait82,Landscape83,Neutral84,Faithful85,FineDetail88)
all compile successfully on the offline R5 route with borrowed R8 descriptor.
All18 stable14bd0 calls match matrix/axes/four-point arguments independently,
and each yields unique descriptor index1,2,1. The proof derives ordinal from
decoded1009, not filename; verifies original source hashes and private payload
hashes; and retains only hashes/selectors/matches in
SIX_STYLE_DESCRIPTOR_CONSUMER_PROOF.json. This expands descriptor-consumer
equivalence to all six observed styles on this route, not all camera routes.
Unknown selectors are rejected by validated_style_ordinal; the DLL's fallback
behavior is not interpreted as supported unknown styles. No app/release or
camera session is changed by these laboratory compiles.

Genuine RP follow-up DESCRIPTOR_GENUINE_RP_20261007 selects native-verified
ID80000433 and archived RP descriptor hash2bff34bc3d7cae7d6c65c5e930befe2e0d0920d725ca9fdb18acbb9c8a7aec60.
The control compile succeeds; independent raw import/store/copy matches
exactly (RP_IMPORT_PROOF.json). The high-bank lab CLI now permits selecting
specific IDs present in the native-verified matrix; unknown IDs and empty
filter results abort before native work, avoiding borrowed representative IDs.

RP's stable MLib trace has four14bd0 calls, unlike the R5 three-call route.
The first pair has axis counts6/3 and additional counts3/2; the second pair
has neither parameter block. The strict R5 descriptor-consumer matcher refuses
this trace rather than treating missing arguments as equality. RP therefore
needs stage-aware comparison; the common raw importer is proven, common
downstream parameter consumption is not yet proven. No new physical result
is inferred from using the genuine archived descriptor.

RP consumer partition follow-up DESCRIPTOR_RP_CALL_PROVENANCE_20261007:
two14bd0 calls match the genuine RP descriptor's independently expanded
matrix/axes/four-point blocks, with unique indices1/2. The other two have
neither axis nor additional block, and are recorded separately as parameterless
consumers, NOT as descriptor matches or incompatibility failures. All four
return through observed MLib1c3b4 zero-split forwarding;1c190 split counts
are0. Its own caller module could not be resolved by the observer (likely
an instrumentation thunk, not proven), so upstream-stage identity remains
unresolved and the trace must not label those calls by assumed phase.
RP_DESCRIPTOR_CONSUMER_PARTITION.json records the two exact matches and
two uncovered calls. The native control succeeds with unchanged payload hash.
This extends descriptor-consumer equality to the actual RP ID/archived RP
descriptor, not only borrowed R8 data. It still establishes no new physical
camera behavior. Observer provenance stores module-relative offsets only.

Wrapper-origin follow-up DESCRIPTOR_RP_WRAPPER_ORIGINS_20261007 observes
all four46a30 calls in compile stage:49109 with axes/four-point pointers for
modes1/2, then49ddd with both pointers null for modes1/2. All produce10-node
grids and splitCount0. Stock payload remains unchanged. Static49d76..49dd8
zeroes a240-byte matrix, assigns uint32ffff at byte offsets0/54/a8, and passes
null parameter lists. Independent parameterless_matrix_reference matches
both parameterless14bd0 matrices exactly in the prior stable trace
(PARAMETERLESS_MATRIX_PROOF.json). It intentionally uses65535, not silently
substituting exact unity65536. This identifies two distinct builder paths,
not two mysteriously missing descriptor blocks. Their full downstream grid
relationships still require stage-aware tracing. The first initial disassembly
at49d78/490a0 was mid-instruction; only aligned observed call sites and the
verified49d76 sequence are used for this interpretation.

Final packing cross-check on DESCRIPTOR_RP_CALL_PROVENANCE_20261007:
existing independent packed10_reference reproduces all six captured packer
outputs exactly. Four49e00 integer-packed blocks equal the complete decoded
4096-byte payload blocks at368/4464/8560/12656 with alternating seedsb8ed/
33137. Two4b760 floating-packed outputs do not occur directly in those blocks;
PACK10_PAYLOAD_PROOF.json records six exact packings and four payload matches.
The raw3000-double14bd0 outputs do not equal either4b760 input directly, so
no direct-copy origin is asserted. For example the fixed-matrix grid and first
floating pack input differ by up to0.12454212454212454; assuming exact unity
or an unverified scale would conceal the intervening transformation. This
narrows the remaining linkage to post-builder conversion before final packing,
not packing correctness. All observations are offline, source files unchanged.

Converter/packer linkage correction: the two4b760 inputs are exactly the
two196a0 outputs, not the14bd0 grids. Existing compact_flag1 reproduces each
captured33³->10³ null-curve conversion with maximum errors2.84217e-14 and
5.68434e-14, and existing pack10 reproduces the subsequent packed bytes.
New compact_pipeline_reference verifies these links jointly, refuses absent
packer links/unsupported configurations, and retains only errors/counts in
CONVERTER_PACKER_LINK_PROOF.json. This reuses previously validated math; it
does not claim discovery of a new interpolation formula. The supposed gap
between14bd0 and4b760 arose from comparing different pipeline branches.
Remaining work is their composition into final integer inputs, not assuming
the converter outputs should equal descriptor/fixed-matrix builder outputs.

Integer-packer origins RP_INTEGER_PACKER_ORIGINS_20261007: stable49e00
entry captures two calls from4c92d and two from4d81d. Independent packing
still matches all six outputs and four final blocks; payload mapping associates
4c92d with368/4464 and4d81d with8560/12656. The static call sites4c928 and
4d818 take the integer-planar buffer atEDI+12 after separate builder logic,
including4a3b0 immediately before each packing region.475c0 also feeds other
integer-packer callers48791/499a8, but those callers are not observed in this
RP run. Do not label every49e00 call as the same conversion path. The proof
now retains callerRva alongside payload locations in
PACK10_ORIGIN_PAYLOAD_PROOF.json. Input PF3/descriptors/DLLs remain unchanged;
post-builder integer conversion is still pending independent replay.

Correction from RP_INTEGER_CONVERSION_20261007: a bounded stable entry/exit
observer for4a3b0 records no calls, nor47af0 calls, on the genuine RP identity
control. All four49e00 origins remain4c92d/4d81d and the payload SHA256 remains
13b74b052917daab83f563d95db710b1ad91d209ae08235a3066105251762707, unchanged
from the preceding controls. Static known-hash disassembly4c8fb..4c91b shows
two mutually exclusive branches:475c0 then jump4c91b, or4a3b0 then4c91b.
Therefore the previous phrase "including4a3b0 immediately before" describes
an alternate static branch, not the observed identity execution. Do not infer
a quantizer/tetrahedral composition for this run. Next trace475c0 and its
branch predicate; retain4a3b0 observation for fixtures that actually take it.

RP_COMPACT_PIXEL_BRANCH_20261007 confirms four475c0 outputs equal downstream
49e00 planar integer inputs byte-for-byte: two4c900->4c92d and two
4d7f0->4d81d. Payload hash remains the preceding baseline. The independent
compact_branch_reference refuses missing grids, unmapped origins and absent
exact packer links; BUILDER_PACKER_LINK_PROOF.json records all four links.
Known-hash static predicates4c82f/4c837 and4d71f/4d727 select475c0 iff
4b290 returnsfalse AND object byte+8 iszero; otherwise choose4a3b0. Observed
first-pair predicatefalse/zero confirms this case. The initial second-pair
observer filter had a wrong return address4d716; corrected to4d71f after
disassembly. No runtime second-pair flag claim until another capture.
475c0->46a70->MLib1cab0 mathematical behavior was already independently
validated in prior compact-pixel experiments; these new captures establish
its concrete link to final packing rather than inventing new math.
Next inspect the upstream4c340 preparation and alternate policy fixtures.
308 regression tests, py_compile and observer JS syntax pass.

Alternate-policy controls: the directory M50_INTEGER_ALTERNATE_20261007 is
misnamed: authoritative matrix identifies camera ID80000432 as RebelT7 /
2000D /1500D /KissX90, class5, NOT M50. Retain the directory for audit;
never derive model identity from its filename. Native control passed with
unchanged baseline but no4a3b0/47af0/49e00 observations. A second control
7DII_INTEGER_ALTERNATE_20261007, ID80000289/class6, likewise passed unchanged
without those calls. Thus selecting a true4b290 camera policy does not alone
exercise4a3b0: outer family dispatch must first reach these builders.
Known-hash static4c340 is exactly ret0xc, followed byint3 padding: it does not
modify the upstream floating grid in this revision. Adjacent4c350/4c360 are
also ret0xc stubs. Previous pending "upstream4c340 preparation" is closed as
a no-op, not an unimplemented color transform. Next identify which real
input/object initialization or family fixture reaches4a3b0, and trace48d10
upstream grid provenance. No borrowed descriptor is physical model evidence.

MLIB_INTEGER_PACKER_CHAIN_PROOF.json now verifies four initialized MLib14bd0
stack7 output grids match475c0 floating inputs exactly, in addition to four
475c0 integer outputs matching49e00 inputs. The earlier no-match check looked
for initializedOutputFloat64Hex at the capture root instead of inside
gridArguments; that was a tooling lookup error, not a transformation gap.
Two parameterless floating outputs are identical and the verifier retains
both candidate capture indices; byte identity does not prove unique origin.
The verifier rejects failed MLib calls, wrong output arguments/geometries,
missing buffers and missing matches. Synthetic tests cover these boundaries.

RP_STANDARD_GRID_CHAIN_RETRY_20261007 reproduces all eight exact links with
the archived Standard base PF3, and now capturesfalse/zero at all four branch
decisions, including corrected4d71f. Native output remains its own baseline.
First attempt RP_STANDARD_GRID_CHAIN_20261007 failed before compilation:
a new48d10 observer altered the entry bytes before the main agent's dense10
semantic signature scan, yielding an ambiguous-signature error. That hook
was removed; retain failed evidence but do not count it as Canon rejection.
Stable known-hash48d10 disassembly selects47250 when object+12 iszero and
47290 otherwise, then produces a10-node double grid using descriptor matrix
and four-point expansion. More provenance is available from existing dense10
builder observations without overlapping entry hooks. 309 tests pass.

Known-hash4b290 policy extraction: thirteen direct equality IDs plus three
bounded byte-selector switch tables4b384/4b3ac/4b3ec, whose jump targets are
4b375(true) and4b377(false), yield exactly41 true IDs. Independent
compact_branch_reference.coefficient_policy encodes this numeric policy only,
NOT support/registration. All48 native-verified matrix IDs in classes7..10
returnfalse; thus they cannot select4a3b0 through this policy alone. Unknown
IDs defaultfalse by this routine, not by a support guarantee.
COMPACT_BRANCH_POLICY_PROOF_20261007.json checks14 observed policy returns
across RP identity/Standard, T7 and7DII against the reference (all exact).
These are stock offline observations with the respective archived descriptor
inputs, not physical validations. The46be0 base constructor initializes
byte object+8 tozero; its downstream setters/alternate object instances remain
unresolved. Do not change that flag experimentally without lab-only provenance.
310 tests and py_compile pass. Next trace writers/callers and virtual methods
on the46be0 object; the alternate4a3b0 may require a different public API mode.

RP_GRID_ENGINE_CONSTRUCTORS_20261007 observes two46be0 calls, both returning
to derived constructor4c622, both initial flagbytezero. Native identity
payload hash remains13b74b052917daab83f563d95db710b1ad91d209ae08235a3066105251762707.
Stable observer records no transient addresses. GRID_ENGINE_VTABLE_PROOF.json
links known-hash static eight-slot base tablebb5e4 to derived tablebc544:
base494d0/49130/48630/492a0/49a10/49830/49b50/49420;
derived4cd00/4c9e0/4c770/492a0/4d8d0/49830/4dac0/4cc40.
Slots3 and5 inherit modern17 builder492a0 and compact tail49830; six other
slots override base operations. Only these eight entries are identified;
bytes after the table are not additional virtual methods. Constructor4c610
calls46be0 then installsbc544 without changing flag+8. Thus stock observed
RP uses the derived compact builder, while modern operations can remain
inherited. This is code-path provenance, not a new family-support guarantee
or proof that4a3b0 is globally unreachable. Remaining work: identify any
valid mode that sets flag+8, or classify alternate branch as unobserved for
the stock fixture corpus; continue other unsolved format/old-family paths.
310 regression tests and observer JS syntax pass.

FOUR_FAMILY_FLAG_BRANCH_20261007 tests class4(450D),5(M3),6(7DII),7(M50)
representatives with the archived R8 descriptor: all four stock controls
match their baselines. Only M50 reaches475c0/49e00, with all fourfalse/zero
branch flags and four exact floating plus four exact integer links. No
4a3b0/47af0 calls in these four controls. FAMILY_BRANCH_PROOF.json retains
this bounded result, not a claim about every input in each family.

Static writer FOUND: alternate output method542c0 creates the derived
engine at545c3/549ec, object atEBP-30/EBP-40, then explicitly writesbyte1
atEBP-28/EBP-38 (545d2/549fb), i.e. object+8. It calls4c770 next. This
explains a legitimate route selecting4a3b0 without an experimental mutation.
Normal54cd0 output examples552fa and56cf5 instantiate the same derived
engine but do NOT perform that write. Method542c0 branches directly on
cameraID and accepts output length4158 in one case, whereas54cd0 switches
on4eaf0 internal class. Pending: identify the public property/dispatch that
selects542c0, then obtain its output in the isolated host and replay4a3b0.
Do not label this as normal01000203 or PF2-specific until that dispatch is
proven. 310 tests, py_compile and observer JS syntax pass.

2026-10-07 alpha28 physical feedback: user reports the new build works on
their EOS RP after the black-image fix. Their original superia400 PF3 used
runtime-generated zero polynomial matrices/zero-point curves. Offline
production-agent fake-transport replay gave all four compact blocks maxY0;
Canon-serialized corrected copy preserved the dense LUT and gave maxY512,
999 nonzero luminance entries per block. Proof../tmp/alpha28_black_fix_proof.json.
Production generated bases now use independently constructed16.16 identity
matrices, three identity curve groups, explicit empty selector/axis headers;
existing strict cache validation regenerates old bases. This specific physical
confirmation does not validate other camera families or pixel-exact preview.

Public alternate dispatch RESOLVED:53f70 sets vtablebf0d4;542c0 is slot1c
(not20).4ef70 compares property00ff0001 and calls this slot at4eff7.
ALTERNATE_FF0001_20261007 uses a private scratch agent requesting that public
property, no flag modification. RP ID with archived R8 descriptor succeeds,
16744 bytes, two4a3b0 calls and2000 calls47af0.7DII succeeds16744 without
4a3b0;450D size succeeds but getterrc80. This is NOT01000203 camera transport.
Captured constants are0.5 and288.0. Replay uses truncation when4b290 true,
otherwise +0.5 then truncation; multiply coordinates32,47af0, signedshift6.
Input/output planar indices remain equal despite transposed traversal; two
chroma output pointers swap. Initial transpose hypothesis failed2682/2820
components, unchanged-index/no-pointer-swap failed1968/1958; correct mapping
matches all6000 components in ALTERNATE_CONVERSION_PROOF.json. Bounded
reference rejects negative/nonfinite coordinates. Upper endpoint proof below
extends the bounded domain. Next compare documented geometry with normal output,
without treating this alternate property as a new installation route.

`descriptor_capability_reference` independently checks every captured gate's
offset/word/result from the retained copy and rejects unknown geometry, unknown
selectors or unverified incoming descriptor hash. 12 gate observations match,
including four failed-copy false results. Tests288, py_compile and JS syntax
checks pass. Internal copies remain private Canon-derived research fixtures.

## Alternate conversion upper endpoint — independent replay

`INTEGER_TETRAHEDRAL_ENDPOINT_20261007.json` contains 5280 interior cases
and 70 additional endpoint cases: five synthetic table patterns, seven
coordinate triples touching 9216, and two padding values (0 / 123456789).
The native lab allocation owns all padding addresses; no camera is accessed.
`INTEGER_TETRAHEDRAL_ENDPOINT_REFERENCE_20261007.json` independently matches
all 5350 outputs. Both padding values give the same result for every paired
endpoint case. Neighbor vertices outside the last grid plane carry zero
weight; the Python reference skips them instead of accessing padding.

The offline alternate converter now accepts its observed upper clamp 288
(fixed-point coordinate 9216), including finite inputs above 288. Negative
and nonfinite coordinates remain unvalidated and rejected. This is not an
installation route or a claim about additional physical camera support.
313 automated tests, py_compile and laboratory JS syntax checks passed.

Follow-up: the replay artifact now retains the native-input SHA256 and DLL
revision hash, explicitly verifies all 35 endpoint guard pairs, and fails
instead of merely printing a summary if any native output differs. Synthetic
identity-plane tests cover half-step boundaries and independent channel
coordinates for both truncation and rounding. These regression tests validate
the reference; they do not substitute for native wrapper captures with the
alternate coefficient policy enabled. 314 tests and py_compile pass.

### Public alternate-property policy sweep

`ALTERNATE_FF0001_20261007/policy_probe.py` replays the archived Aerochrome
PF3 through public property 00FF0001 for IDs 80000346, 80000355, 80000384,
80000393, 80000422 and 80000432. All six have coefficient policy true,
but none executes 4a3b0; all getters return rc=0. Full private observations
and source/borrowed R8 descriptor hashes are in PRIVATE_POLICY_RESULTS.json.
Therefore camera-ID policy alone does not guarantee this conversion is
selected by the public alternate getter. These successes do not validate
the missing policy-true conversion or physical camera compatibility.

The first sandboxed run stalled in Frida attachment, produced no artifact,
and its exact owned host/driver were terminated after checking parent and
command line. The completed isolated retry ran with verified DLL revisions;
all host lifetimes are managed by compile_stock's finally cleanup.

`verify_policy_routes.py` narrows the divergence: every one of those six
alternate-property outputs contains two observed 4b760 float packer calls,
with coefficientMode=true, and no 49e00 integer packer. The existing independent
pack10 reference reproduces all 12 native packed blocks byte-for-byte.
`POLICY_FLOAT_ROUTE_PROOF.json` records input and output hashes. The previously
captured RP alternate route instead contains 14bd0 -> 4a3b0 -> 49e00 as well
as two 4b760 calls; its additional integer conversion is not common to the six
policy-true cases. This is a route-selection distinction, not new packing math
or a claim that all policy-true IDs must use this observed path. py_compile
passes for the private verifier; production code and build are unchanged.

### Complete known-revision coefficient policy sweep

The private driver now supports `--all-policy-ids`, preserving the original
six-case artifact separately. All 41 IDs from the independently mapped 4b290
policy were compiled through 00FF0001 with the same archived Aerochrome and
borrowed R8 descriptor. PRIVATE_ALL_POLICY_RESULTS.json retains observations;
ALL_POLICY_FLOAT_ROUTE_PROOF.json hashes that input and verifies every
successful float packer capture. Results: 17 getters rc=0, 24 getters rc=80,
34 independently byte-exact 4b760 blocks, no 4a3b0 in any captured case.
This falsifies using the coefficient-policy list alone to find a public
policy-true alternate integer-conversion vector for these inputs. It does
not prove the branch is unreachable with all descriptors/inputs, nor that
the 24 IDs fail normal 01000203 compilation or installation. No new physical
compatibility inference is warranted. The next branch investigation should
trace the 542c0 selection gates before constructing more model-specific
experiments. Private scripts compile; the 314-test suite remains green.

### Getter dispatch explains all 24 alternative rc=80 results

Known-hash read-only `selection_static.py` reconstructs the two indexed
camera-ID switch tables at 54ab0/54ab8 and 54bb4/54bc0. At entry 542ef,
ESI is initialized to 0x50. The explicit ID 80000270 and 23 other policy
IDs dispatch straight to 54a98, which returns ESI without reading PF3
records. This explains the 24 observed errors as deliberate dispatch
exclusions for this property, not missing records or failed interpolation.
The other policy IDs dispatch one to 5433d and sixteen to 5466c.
The native/private verifier now joins all 41 results to these static
targets and matches every rcGet; no model installation claim is made.

ALTERNATE_SELECTION_TABLES.json preserves those targets. The linear getter
disassembly stops at the verified ret8 at 54aaa, before its switch data.
The builder's earlier gate 4b4f0 is called at 4c7b9; false goes to 4c935,
where existing/generated 4096-byte grids are stored as 1f00/1f01 instead of
executing dense conversion. That gate consults descriptor copies through
47250/47290 and selected-style flag words, before the later 4b290 policy
at 4c82a. Its exact correlation with these new captures remains to verify;
the absence of 4a3b0 alone is not sufficient to prove which gate failed.
No installed code modified, no camera access. Private scripts py_compile.

Gate correlation completed: the verifier independently decodes retained
internal descriptor copies for both gate calls in all 17 successful policy
cases. All 34 word tests are zero/disabled, agree with native 4b4f0 outputs,
and explain taking its fallback before coefficient-mode branch selection.
Two additional IDs (80000269 / 80000289) with the genuine archived 7772-byte
1300D descriptor still yield zero flags at Neutral ordinal3, indices1/2;
both getters succeed and all four float-packed blocks replay exactly.
Private artifacts PRIVATE_COMPACT_DESCRIPTOR_POLICY_RESULTS.json and
COMPACT_DESCRIPTOR_POLICY_ROUTE_PROOF.json retain this countercheck. Thus the
zero flags are not solely an artifact of borrowing the R8 descriptor. No
descriptor bytes were changed; further inspection should compare other
style ordinals before constructing artificial capabilities. py_compile passes.

### Both alternate conversion policies validated with native style vectors

`style_gate_probe.py` compiles the five untouched archived Manual Loader base
PF3s against two contexts: policy-true 80000289 with archived compact 1300D
descriptor, and policy-false RP ID80000433 with archived R8 descriptor. This
is still an offline cross-descriptor experiment, not physical validation.
PRIVATE_STYLE_GATE_RESULTS.json retains source/descriptor hashes, initialized
descriptor copies, native gate results and conversion/packer captures.

Compact descriptor: Faithful/Landscape/Portrait have both word gates enabled;
Standard has first enabled and second disabled; Neutral has both disabled.
Modern borrowed descriptor: both gates enabled for all five bases. Each gate
matches the independent normalized-copy word test. Thus selection genuinely
depends on descriptor geometry AND selected style, not only camera-ID policy.

`verify_style_conversions.py` replays all 17 observed 4a3b0 outputs (7 policy
true, 10 false): 51000 integer components exact, and all 17 downstream 4096-byte
49e00 packed blocks exact. STYLE_ALTERNATE_CONVERSION_PROOF.json retains hashes
and counterfactual wrong-policy comparisons: switching the policy changes
4328 components in the true cases and5693 in false cases. These are therefore
discriminating native vectors, closing the previously missing policy-true
mathematical validation. No synthetic capabilities, installed DLL changes,
camera writes, app builds or public releases. 314 tests and py_compile pass.

### Alternate serialization: mixed Standard conversion located end-to-end

`style_gate_probe.py --standard-payload` retains two private native 16744-byte
outputs in PRIVATE_STANDARD_PAYLOAD_RESULTS.json plus hashed .bin files.
`verify_standard_payload.py` checks their hashes, uses the independent cipher
decoder, and accounts for every 4096-byte block using captured native packers:
offsets360/4456/8552/12648, with seedsB8ED/33137/B8ED/33137 respectively.
STANDARD_ALTERNATE_PAYLOAD_PROOF.json records exact block locations and hashes.

In the compact-descriptor/policy-true Standard case, integer converted data
occupies offset360 only; the float reference at4456 equals the reference at12648.
The other float reference occupies8552. In the modern borrowed descriptor/RP
case, integer converted blocks occupy360 and4456; float reference blocks remain
at8552 and12648. The verified set of converted offsets exactly matches enabled
descriptor gate indices in both cases. This connects gate -> conversion ->
packing -> ciphered location, including the mixed enabled/disabled case.
It is specific to public property00FF0001 and must NOT be substituted for the
normal camera-registration01000203 carrier. Private scripts compile,314 tests
pass; app, original fixtures, installed DLLs and camera state unchanged.

The observed alternate block-location proof is now reusable in
`alternate_payload_reference.verify_blocks`. It explicitly requires the four
bounded 4096-byte blocks with observed offsets/seeds, two distinct strict
boolean gates, complete native-packer coverage, and unambiguous integer
locations matching enabled indices. Synthetic regressions reject missing,
corrupt, wrong-seed, wrong-gate and ambiguous blocks. Both retained native
Standard outputs replay through this extracted verifier without change.
This is offline research code, not a transport validator or builder for other
layouts. 318 tests and py_compile pass; no Canon fixtures in test sources.

### Second alternate geometry verified, not a normal carrier layout

The static dispatch's single policy-true target5433d is ID80000324, not80000302.
An initial302 run inadvertently repeated the default branch; its16744 output
and proof are retained separately as PRIVATE_DEFAULT_302_CONTROL_RESULTS.json
and DEFAULT_302_CONTROL_PAYLOAD_PROOF.json. It is not evidence for5433d.
The corrected324 run with untouched Standard and compact descriptor returns
16728 bytes, matching static expected4158. Its four block offsets are
344/4440/8536/12632 (seedsB8ED/33137/B8ED/33137). One gate enabled, one disabled;
all blocks match captured packer outputs exactly, with integer output only
in the first slot. PRIVATE_OLDER_ALTERNATE_RESULTS.json and
OLDER_ALTERNATE_PAYLOAD_PROOF.json retain source, descriptor and payload hashes.
The independent verifier accepts only the two now-observed header sizes344/360;
regressions reject unknown sizes and verify the shifted geometry. 319 tests
and py_compile pass. Normal01000203 transports and app remain unchanged.

Same-input geometry comparison: untouched Standard and compact descriptor
are hash-identical across IDs80000324/80000289. All four corresponding
4096-byte ciphertext blocks are identical, not merely mathematically similar.
ALTERNATE_GEOMETRY_COMPARISON.json proves the header360 is exactly header344
expanded with two little-endian u32 values(1,1) before original offsets24
and84, then the
u16 moved to32 and u32 moved to100 incremented by8. Observed u16 changes
4140 ->4148; u32 FC0040 ->FC0048. This exact transformation explains every
header byte for this pair. It does not prove field semantics beyond observed
length-like relationships, nor authorize translating normal camera carriers.
`compare_alternate_geometries.py` verifies payload/input hashes before comparison,
and fails if the proposed header transform differs. The first zero-padding
hypothesis failed at new offsets24/28/92/96 (native values1); it was rejected
before the successful(1,1) extension proof. py_compile passes.

Five-style countercheck: `style_gate_probe.py --geometry-matrix` retains ten
new isolated native outputs, five archived bases at IDs80000324/80000289 using
the same genuine compact descriptor. `verify_geometry_matrix.py` checks input
and output hashes and proves all five complete header expansions byte-exact,
plus all twenty corresponding ciphertext blocks identical. Evidence:
PRIVATE_GEOMETRY_MATRIX_RESULTS.json, GEOMETRY_MATRIX_PROOF.json and private
PRIVATE_MATRIX_*.bin. This includes both-enabled, both-disabled and mixed gate
states, not only Standard. The independent `expanded_header` helper rejects
unknown lengths/observed structure fields and is tested with synthetic bytes;
it is a research prediction, never a camera serializer. 320 tests and py_compile
pass. This extends evidence over these five bases/one descriptor/two IDs,
not all PF3s, descriptors, compiler revisions or physical camera models.

Recent integrity audit: `audit_recent_evidence.py` independently hashes seven
proof-to-source links (including the full41-policy capture) and13 retained
native payloads. Every hash matches; private
RECENT_EVIDENCE_INTEGRITY_20261007.json records the chain. This is artifact
integrity, not a substitute for numeric replay or goal completion. Remaining
research still includes genuine opaque1007 semantics, old initialization
routes, broader descriptor revisions and complete format/flag meanings.
No live laboratory handle remains from the completed capture runs.

### Fine Detail rcId7 static cause

Read-only hash-gated scan finds the actual selector comparison at573dc/e1:
raw1009 word0088 is checked after a successful read; other selectors skip
this specific rejection. The subsequent camera-ID comparisons and three
tables at574e8/574f0,57510/57518,57550/57558 route41 IDs to574c4, which sets
return code7. Independently extracting those tables produces exactly the same
41-ID set as4b290 coefficient policy. Evidence: FINE_DETAIL_SELECTOR_STATIC,
FINE_DETAIL_REJECTION_BRANCH and FINE_DETAIL_STATIC_REJECTION_IDS files dated
20261007. Disassembly stops before jump-table data at574e8.

This provides a static mechanism for previously observed Fine Detail rcId7
on M3/1300D/450D/1DIII/7DII and descriptor-independent rejection there; it does
not constitute native execution of all41 cases. `rejects_fine_detail_branch`
replays only this known-revision branch with strict ID/selector types; false
means this rejection is not selected, not that the style/camera is supported.
328 tests and py_compile pass. Production editor/transport unchanged.

Native full-list confirmation: fine_detail_native_probe.py runs all41 IDs
plus RP/R8 controls in separate own hidden hosts, with untouched archived
Fine Detail (SHA126611fb855066506b4752c287d51d2c62f07349679280f7378206f44fc4dd02)
and one borrowed R8 descriptor. All43 initial public114 reads confirm0088.
The41 list IDs return rcId7, both controls rcId0. The independent verifier
requires exactly43 distinct expected IDs and checks every native return
against the static condition. FINE_DETAIL_NATIVE_REJECTION_PROOF_20261007.json
and FINE_DETAIL_NATIVE_MATRIX_CHECK_20261007.json retain the result and hashes.

Crucially,17 rejected-ID cases still return rcGet0 from alternate00FF0001.
They must NOT be counted as valid compilations: upstream API rejection remains
authoritative even when a downstream buffer exists. This experiment validates
the branch on these offline inputs, not the physical body's supported styles.
No EDSDK/session/write or installed DLL changes.328 tests and py_compile pass.

Research reporting fix: compiler_failure_research previously used only rcGet
and a generic error field; a trace with rcId7/rcGet0 could be labeled
no-failure-observed. It now preserves nonzero rcCreate/rcId/rcDescriptor/rcSize
as apiErrors and classifies ID setup rejection ahead of downstream read noise.
Two regressions cover getter success with earlier failure and other setup APIs.
verify_setup_error_summary.py replays the43 retained ID/getter status pairs,
preserving all41 rejections including the17 with getter success. Evidence:
SETUP_ERROR_SUMMARY_REGRESSION_20261007.json. Missing statuses remain unknown;
no-failure-observed still never means physical support.330 tests and py_compile
pass. This changes only offline research reporting, not production transport.

Paired selector-only control: the same archived Fine Detail source and borrowed
descriptor were replayed for all43 IDs, changing public PF3 property114 from88
to84 only in memory. All43 Set camera-ID calls then return0, removing all41
previous rcId7 rejections. Independent snapshot comparison confirms114 is the
only changed captured property, including unchanged dense tables. Evidence:
FINE_DETAIL_NEUTRAL_SELECTOR_CONTROL_20261007.json and
NEUTRAL_SELECTOR_CONTROL_VERIFIED_20261007.json, verified by
verify_neutral_selector_control.py. This isolates the known-revision rejection
to the selector rather than the table contents. It does NOT establish faithful
Fine Detail rendering under Neutral or validate any camera installation. No
production workaround was added; original source remains untouched.

Downstream paired audit: compare_selector_downstream.py records all43 alternate
00FF0001 getter returns before/after selector change. No getter status changes:
17 formerly rejected IDs return0 in both runs,24 return80 in both; the two
non-rejected controls give one0 and one80 in both. Thus eliminating rcId7 does
not eliminate alternate getter failures. SELECTOR_DOWNSTREAM_COMPARISON_20261007.json
retains per-ID pairs and source hashes. This alternate property is not the
normal01000203 transport; neither getter success nor failure establishes camera
compatibility. The remaining alternate failure mechanism must be studied
separately from the selector gate; no universal workaround follows here.

Static/native join attribute_alternate_failures.py confirms all24 policy-list
getter failures select explicit rejection54a98. A distinct control, ID80000487,
selects nonreject5466c but returns80 for this Fine Detail source even after the
neutral selector mutation. ALTERNATE_FAILURE_ATTRIBUTION_20261007.json keeps the
full join and hashes. One additional own hidden known-hash native trace retains
FINE_DETAIL_R8_ALTERNATE_TRACE_20261007.json: rcId0/rcGet80, no failed4ef20Raw
reads captured. Hence missing raw property attribution is not yet evidenced;
the remaining failure needs return-path tracing, not guessed property synthesis.
This is alternate00FF0001 only, not proof of a normal R8 installation failure.

Coverage correction and completed trace: the initial packing-only trace had
observe_dense=False, so4ef20Raw hooks were not installed. Its lack of captured
failed reads was not evidence of successful reads. Repeated the own hidden
known-hash host with observe_dense=True; rcId0/rcGet80 remains unchanged. Four
raw reads fail:1022/4096 at callers54951 and54997;102a/4096 at54974 and549bc.
FINE_DETAIL_R8_ALTERNATE_TRACE_20261007.json now contains the expanded trace.
This identifies a derived-4096-table-read failure in the alternate getter;
it does not justify fabricating those records or changing normal transport.

Node-level refinement: verify_alternate_empty_records.py independently checks
the expanded trace's four failed raw reads against four metadata lookups.
Both1022/102a nodes EXIST, storedType4, storedSize0; the requested4096-byte
reads return80. Therefore these are empty derived nodes, not absent nodes.
ALTERNATE_EMPTY_RECORD_PROOF_20261007.json keeps exact callers and input hash.
The distinction matters for reconstructing initialization versus lookup logic;
no synthesis or production transport change was made.

Normal-getter control: private_neutral_normal_agent.js differs from the neutral
alternate agent only in output property FF0001 ->01000203. Same archived source,
R8 ID and descriptor, observed hidden hash-gated host. All setup/getter APIs
return0 and no4ef20Raw failures are captured. Full report retained privately as
FINE_DETAIL_R8_NORMAL_TRACE_20261007.json. This demonstrates the empty4096-node
failure belongs to the alternate getter on this input, not a general inability
of the normal compiler getter to produce output. Selector was Neutral in both
controls, so this is not a Fine Detail fidelity or physical-install validation.

Full normal getter matrix: same archived source, Neutral selector-only mutation,
borrowed R8 descriptor, all43 IDs in hidden known-hash hosts. All setup APIs0;
39 getters return0 (8528x3,16720x5,16744x26,16752x4,83076x1), four return80:
80000213/232/234/236, matching the previously identified legacy1007 group.
No claim that this run directly traced those four failure causes. Per-case
output sizes/hashes retained in FINE_DETAIL_NEUTRAL_NORMAL_MATRIX_20261007.json;
verify_normal_selector_matrix.py checks coverage and all retained stages in
NORMAL_SELECTOR_MATRIX_VERIFIED_20261007.json. Getter outputs are not physical
compatibility or faithful Fine Detail under Neutral.330 regression tests pass.

Direct four-case follow-up: same source/Neutral selector/borrowed descriptor,
normal01000203 with raw-read coverage. All four give rcId0/rcGet80 and exactly
three failed raw reads:1007/1460,1004/300,1005/240 (all80).213/232 callers
54da3/54dc2/54de7;234/236 callers54f31/54f50/54f75. Therefore this particular
source has additional legacy alias-read failures, not just1007. Do not infer
that supplying1007 alone fixes it. Private FINE_DETAIL_LEGACY_NORMAL_TRACE
files and LEGACY_SELECTOR_READ_FAILURE_PROOF_20261007.json record all12 reads;
verify_legacy_selector_traces.py checks the complete set.330 tests pass.

Read-only source decode (hash-checked original and known-hash compiler cipher
tables) shows1004/1005/1007 absent from serialized Fine Detail, but1018 exists
with type4/300 bytes and1029 with type4/240 bytes. Thus origin data for the two
previously proven legacy aliases is present with expected geometry; the failed
legacy reads cannot simply be attributed to absent modern curve/matrix data.
inspect_fine_detail_legacy_sources.py retains per-record hashes in
FINE_DETAIL_LEGACY_SOURCE_GEOMETRY_20261007.json. Next distinction is whether
initialization fails to expose/remap those origins in this input; no metadata
is fabricated and original remains intact.

Four-trace stage correlation: strengthened verify_legacy_selector_traces.py
requires successful convertDense during inputs (caller573be, low-byte1) for
all four IDs, then existing size0 nodes1004/1005/1007 at the failing getter.
Thus successful dense conversion is insufficient to initialize the legacy
curve/matrix/metadata aliases for this PF3-format context (version4000).
LEGACY_SELECTOR_READ_FAILURE_PROOF_20261007.json now retains both conversion
success and node emptiness for every case, not just read errors. Native return
success at an earlier stage is not evidence that every required field was
populated.330 tests pass; no changes to installed DLLs or transport.

Official Emerald PF2 control, same213 ID and borrowed descriptor with Neutral
selector mutation: research-only observer now includes1004/1005 write filters.
Native4a2b0 writes300/240 bytes at callers49620/4963c, returns0; corresponding
node writes succeed and later raw reads4f3c2/4f3e1 return0. Overall getter still
returns80, including1007 failure. This positively locates the alias preparation
sites for this PF2 path without claiming every failing raw read is fatal (PF2
also probes absent modern Basic fields). EMERALD_LEGACY_ALIAS_TRACE and
PF2_ALIAS_PREPARATION_PROOF_20261007.json retain source/observer hashes and exact
write/read pairs; verify_pf2_alias_writes.py validates both pairs.330 tests pass.

Alias-origin confirmation: expanded bounded observer captures only300/240-byte
input buffers for the two alias setters. Repeated own offline Emerald host;
independent source decode plus swap32 matches all540 input bytes exactly:
1004 <-1018,1005 <-1029. Updated PF2_ALIAS_PREPARATION_PROOF retains source and
observer hashes and both exactSourceBytes results. This directly links source
records to native preparation, complementing older final-carrier comparisons.
No arithmetic curve/matrix transform was needed to match these two buffers on
this control; other styles/formats still require separate evidence.330 tests pass.

Matched Emerald archived-format comparison: original PF2 and PSE unchanged PF3
share1018/1029 bytes exactly (also1021);1019 differs and onlyPF3 has dense1070/71.
Same ID213/Neutral selector/borrowed descriptor/observer revision: PF2 writes
both aliases and reads0; PF3 performs no observed4a2b0 alias writes and reads80.
EMERALD_SOURCE_FORMAT_COMPARISON and EMERALD_FORMAT_ALIAS_DIFFERENCE_PROOF keep
source/trace hashes; independent verifier checks same origins and equal observer
coverage. This rules out different1018/1029 contents as the explanation on
this pair, but does NOT isolate envelope version alone because other records
differ. Both overall getters fail; no camera validation.330 tests pass.

Preparation entry correlation: read-only observer additionally watches494d0 in
the known-hash host. Repeated both formats with identical observer: Emerald PF2
calls494d0 once, caller53f2f, returns low-byte1; Emerald PF3 never calls it on
this control. All prior exact alias-byte and write/read proofs still pass and
their trace hashes were refreshed. The paired verifier now requires the positive
PF2 call and absent PF3 call. This locates the divergence before alias writes,
not at final reads or endian handling. Next static target is call-site53f2f
and the PF3 override path.330 tests pass; application transport unchanged.

Base-setter control flow confirmed from entry53d00: successful01000001 storage
is followed by53b40 initialization, then classification4eaf0. Classes8/9/10
skip494d0; other classifications reach call53f2a (return address53f2f). Private
extract_base_alias_gate.py checks exact compare instructions, all three skip
targets, and preparation call in the hash-verified DLL; BASE_ALIAS_PREPARATION_GATE
retains instruction bytes. Independent base_context_prepares_legacy_aliases
replays only that gate, with strict uint32 validation and two synthetic tests.
PF3 setter override is not covered by this predicate and still needs its own
mapping; true/false is never a camera-support verdict.332 tests and py_compile pass.

PF3 setter override572d0 confirmed: non-ID properties delegate53d00 at5734d;
01000001 stores1001, calls its own initialization57110 at5737f, constructs
4c610 context, then skips conversion for the same classes8/9/10. Other classes
call4cd00 at573b9, not494d0. Hash-gated extractor now verifies all three skip
targets plus delegate/initialization/conversion calls and records the complete
pre-rejection instruction segment. Independent pf3_context_converts_dense
replays this predicate with strict domain tests. This explains the observed
different preparation calls for matched Emerald inputs, not a complete solution
for empty legacy aliases or1007.333 tests and py_compile pass. No installed
DLL/editor/transport changes.

Deterministic legacy alias control on all four IDs: private agent copies only
public1018->1004 (300 bytes) and1029->1005 (240 bytes) after inputs, without
setting1007, serialization, or camera transport. Independent verifier decodes
the intact Fine Detail source and confirms each copied buffer equals swap32 of
its source origin. All eight alias reads now return0;1007/1460 still returns80
and overall getter80. Both dense tables remain byte-identical before/after on
every case. LEGACY_ALIAS_CONTROL_PROOF_20261007.json retains four trace hashes,
exactSourceAliases and denseTablesUnchanged. This is a private causal control,
not an installable workaround: unresolved1007 remains authoritative, and no
synthetic metadata was inserted.333 tests and syntax checks pass.

Initialization list comparison: base lists cf838/cf860 and PF3 lists cf878/cf8a0
are exactly equal. Legacy sequence1009,1002,1007,1004,1005,1003,100b,1022,102a;
common sequence1009,1002,100c,1022,102a. All175 indexed model selector bytes
53c50 versus57220 also match, with PF3 targets571d9/571e0/57145 corresponding
to skip/legacy/common. extract_base_alias_gate.py validates and records this
in initializationComparison. This rules out differing list contents/indexed
selectors as the explanation for this matched legacy control; it does not by
itself prove all explicit skip branches equivalent. Preparation/conversion
after list creation remains the observed divergence.333 tests pass.

Complete initialization-context equivalence: extractor now supports explicit
base53b40 or PF357110 context with separate confirmed jump targets/list RVAs,
rejecting unknown contexts before reading files. Both full extracted rules
are equal except functionRva, including all eight explicit skip IDs, indexed
selectors and lists. verify_both_initialization_contexts.py also requires the
original base extraction remain byte-for-byte equivalent as JSON values to the
retained baseline and reproduces all87 IDs' attributions in both contexts.
BOTH_INITIALIZATION_CONTEXTS_PROOF_20261007.json retains both rules and pairs.
This removes the prior explicit-branch uncertainty; conversion semantics and
camera compatibility remain separate.334 tests and py_compile pass.

Public103 action control: static base setter calls49130 after clearing1020/1028;
49130 generates those two records, not1004/1005. Own hidden213/Neutral Fine Detail
host calls set103 with empty input in memory: rc0;1020/1028 change from length0
to217828 each, both read0, dense1070/71 unchanged. All three legacy read failures
1004/300,1005/240,1007/1460 remain and overall getter80. Private action agent never
serializes or installs. verify_action103_control.py records exact output hashes
and unchanged failure set in ACTION103_CONTROL_PROOF_20261007.json. The generated
records' mathematical meaning is not established by size; action is not a legacy
alias recovery method.334 tests and syntax checks pass.

Generated1020/1028 structure identified: ICC acsp/scnr/RGB/Lab envelopes217828,
12 tags, shared A2B0/A2B1/A2B2 at offset520 length217308, type mft2. Independent
bounded icc_profile_reference validates tag ranges/shared tags, dimensions and
payload geometry:3->3 channels,33 nodes,16 input curve entries,256 output entries,
215622-byte CLUT, plus2 zero alignment bytes. Initially strict unpadded length
check rejected the native tag; exact observed alignment padding was then modeled
and tested, rather than ignoring arbitrary trailing bytes. Private
ACTION103_ICC_GEOMETRY_PROOF retains tag and CLUT hashes for both profiles.
Structure does not prove colorimetric equality to original dense tables or camera
payload suitability. Four synthetic tests,338 full tests and py_compile pass.

ICC curve/matrix refinement: independent parser reads all input/output curve
entries, not just endpoints, and reports exact rounded linear-ramp comparisons.
Both native profiles have identity16.16 matrix and all three input/output curves
exactly linear (16 entries step4369,256 entries step257). CLUT first node both
(0,32768,32768); last nodes1020=(65534,32768,32767),1028=(65531,32770,32766).
The two CLUT hashes differ; identical structure/curves is not identical color
mapping. Updated ICC geometry proof retains these facts. Synthetic test verifies
nonlinear zeros are not mislabeled identity and then checks linear ramps.
339 tests and py_compile pass. No encoding equivalence to dense RGB is asserted.

ICC builder linkage: static46b80 is a trampoline through pointer d11e4; own
hash-gated hidden host resolves it to MLib.dll1b690, exported
MLIBcreateCustomMLDataEX. Observer reads binding only (no new function call);
repeated action103 reproduces both previous CLUT hashes exactly. Updated ICC
proof requires the exact module/RVA/export binding and retains it with trace
hash. This links generated profiles to a named MLib interface; argument and
colorimetric semantics still need separate mapping.339 tests and syntax pass.

Actual ICC builder observations: bounded hook on hash-verified MLib1b690 captures
two native calls from491cd/4924f. Both numeric arguments are(8,1); no semantic
label is assigned yet. Both return nonnull structures with size217828 and ICC
header matching their corresponding retained1020/1028 profile exactly. Updated
independent ICC verifier requires the two callers, argument tuple, sizes and all
128 header bytes. However, the new trace fails the strict ICC geometry verifier:
record1028 has nonzero trailing alignment bytes (fcfc), unlike the earlier zero
padding. The previous geometry proof is not refreshed and CLUT reproduction is
not yet verified for this trace. Unchanged legacy failures were independently
verified.339 unit tests and syntax checks pass, but do not resolve this native
verification failure. Investigate padding provenance before changing validation.

Follow-up read-only diagnostic separates bounded alignment from LUT semantics.
ICC_ALIGNMENT_DIAGNOSTIC_20261007.json proves both CLUT hashes and all previously
reported LUT geometry/matrix/curve fields unchanged.1028 has fcfc in its two
alignment bytes;1020 has0000. A temporary diagnostic copy zeroes only alignment
for inspection; original evidence and strict parser remain unchanged. This does
not establish padding provenance or strict ICC acceptance. Five ICC unit tests
and py_compile pass. Static known-hash extraction ICC_BUILDER_STATIC_20261007.json
checks the entire MLIBcreateCustomMLDataEX wrapper: arg0 becomes ECX, arg2 is
pushed to4420, arg1 is not read by this wrapper. Numeric8 is therefore not evidence
of grid size. Callee4420 branches on the first input word and needs further mapping.

ICC builder dispatch follow-up: exact instruction assertions map mode0 to4720,
mode1 to5930/6260 (unsigned field+c threshold10), mode2 to7810 after count
handling, and other modes to null. Both captured action103 inputs have mode0,
linking them to4720 statically, not a hooked destination observation. Its first
block invokes existing curve normalizerf490 six times: two groups of three
structures at100-byte strides. Updated private extraction retains both dispatch
and preparation instructions with DLL/trace hashes.339 tests and py_compile pass;
the alignment provenance and downstream ICC quantization remain unresolved.

Mode0 final serialization is linked statically at58b7 to3f60. Its tag provider
3730 uses a12-entry switch; the successful allocation path copies supplied tag
bytes for the entire supplied length, with no padding normalization in that copy.
Thus trailingfcfc may originate upstream; this is not proof of uninitialized
memory. The provider's non8-bit length arithmetic matches observed geometry:
52+32*(3*16+3)+2*33^3*3=217306, rounded to217308. Private extraction retains
switch targets, intent-size instructions, serializer and final caller. Double
precision Lab grid storage was located before serialization;16-bit writing still
needs tracing. Hash-gated extraction and py_compile pass; no production changes.

16-bit writer located atMLib2590, called by the final provider construction
branch3ee7. L is multiplied by65535 then divided by100 and clamped0..65535;
a/b multiply65536 and1/256, clamp-32768..32767, add32768. Helper29651 selects
integer conversion via mantissa shifts, discarding fractional bits; byte stores
write big-endian. Private extraction retains writer/helper instructions and
asserts all seven constants against the known DLL hash. Independent finite Lab
reference encode_observed_lab16 adds endpoint, clamp, fraction and invalid-input
tests.341 tests and py_compile pass. Native pre-encoding Lab samples have not yet
been compared with the reference; this is not a pixel-equivalence claim.

Native Lab comparison experiment prepared: bounded observer2590 retains at most
two33^3x3 input-double grids and their written CLUT bytes; independent verifier
checks every node and links output to retained1020/1028 profiles. Previous trace
preserved as FINE_DETAIL_ACTION103_PRE_LAB_WRITER_20261007.json. Own isolated
compile launched in terminal session59968, still returning running with no output
at last poll; no equivalence result exists yet. Node syntax and verifier py_compile
passed. Do not overwrite this pending state with a claimed successful comparison.

Pending execution resolution:59968 had no visible Python/lab host and unchanged
capture, then was explicitly cancelled (terminalexit1). Scoped elevated offline
retry completed in3.4s; no EOS Utility/camera access. Native Lab writer capture
contains two complete35,937-node grids. verify_native_icc_lab16.py proves all
107,811 components per profile exactly against encode_observed_lab16 and links
both byte arrays to retained1020/1028 ICC CLUTs. Hashes reproduce previous CLUTs.
NATIVE_ICC_LAB16_PROOF_20261007.json retains trace/observer hashes. Action103
verifier still confirms unchanged legacy failures. Strict ICC geometry now passes
both profiles (zero padding this run), so geometry proof refreshed; earlierfcfc
trace remains preserved. Padding variability confirmed across runs, cause not yet
established.341 tests, Python syntax and observer Node syntax pass. Equivalence
scope is finite captured Lab-to-ICC quantization, not RGB-to-Lab/RAW/camera support.

Writer alignment follow-up: bounded2590 entry/exit observations now record the
two bytes beyond semantic LUT length. Both observed profiles had0000 on entry,
unchanged on exit and identical in retained ICC. Full native Lab equivalence
reproduces; verifier now requires entry=exit=profile alignment. Prior Lab trace
and proof preserved with PRE_ALIGNMENT names. This proves preservation in the
observed zero-padding case, not the provenance of the earlierfcfc bytes or absence
of writes in every execution. Strict geometry/action103 verifiers refreshed;
341 tests, Node syntax, py_compile and hash-gated static extraction pass. Next
useful branch: native synthetic boundary values to validate quantization clamps
and fractional decisions beyond the range present in these two real grids.

Synthetic quantization gate completed: private_synthetic_icc_writer.js invokes
known-hash MLib2590 using its observed ECX/EDX fastcall in an owned hidden x86
host. No PF files, EDSDK or cameras involved. Synthetic buffers contain eight
Lab nodes per call, generated identity output-curve values, and16 sentinel guard
bytes.432 nodes cover black/white, out-of-range clamps, half/fractional values,
and nextafter values around quantization boundaries sampled across the16-bit
range. Every native CLUT byte equals the independent finite Lab reference; all
guards remaina5. SYNTHETIC_ICC_WRITER_PROOF_20261007.json retains exact inputs,
outputs, agent/DLL hashes and loaded module path.341 tests, Node syntax and
py_compile pass. This extends mathematical evidence, not model support. Still
pending: RGB-to-Lab profile construction and earlier nonzero padding provenance.

ICC color-chain samples: caller-filtered1000 observations at52fb retain eight
selected node indices per profile, linked to corresponding complete2590 Lab
input grids. Existing independent RGB/XYZ and floating XYZ/Lab references match
all16 samples: maximum XYZ error5.551115123125783e-17, Lab error0. Numeric mode10
or11 is checked, not labelled as camera compatibility. ICC_RGB_LAB_SAMPLE_PROOF
retains sample indices/errors and trace/observer hashes; this is sample coverage,
not complete RGB-to-Lab grid equivalence or earlier curve/polynomial reproduction.
Full Lab-to-ICC quantization again matches both CLUT hashes. Nonzerofcfc was now
actually observed at writer entry, unchanged at exit and retained in1028 ICC:
the earlier padding anomaly originates before2590, not in that observed writer.
Allocator provenance remains unproved. Strict ICC parser still rejects this
nonzero padding; do not treat the prior zero-padding geometry proof as current.
Previous trace preserved PRE_RGB_LAB; action103 failures unchanged.341 tests,
Node syntax and py_compile pass. No production/camera changes.

Full ICC color gate replaces sample-only coverage for this fixture. Caller52fb
captures two complete35,937-node RGB/XYZ grids with completed count, fixed mode
and zero API failures. verify_icc_full_color.py independently computes XYZ from
captured RGB, then Lab from independently computed XYZ (not native XYZ), then
16-bit CLUT. Both modes10/11 produce exact final CLUT bytes for all71,874 nodes.
Max floating XYZ error2.220446049250313e-16; max end-to-end Lab error
1.1368683772161603e-13. ICC_FULL_COLOR_PROOF retains trace/observer hashes and
coverage. Full Lab verifier, strict ICC geometry (zero padding this run) and
action103 failure verifier refreshed. Previous trace preserved PRE_FULL_COLOR.
341 tests and syntax checks pass. Prior curves/polynomial stages remain outside
this proof; no RAW/camera or other-fixture equivalence is asserted.

Full ICC polynomial gate: caller5176-filtered1d380 captures two complete input/
output grids and native57 coefficients. Mode0 description bytes at25c contain
60 signed16.16 words; omitting row padding and dividing65536 reproduces all57
native doubles exactly for both profiles (no decimal truncation on this path).
Independent19-term polynomial reproduces all71,874 native output nodes with
maximum error0. ICC_POLYNOMIAL_GRID_PROOF links coverage and coefficient origin
to trace/observer hashes. Captured pre-color RGB grids are not identity lattices:
max absolute deviation0.1498295390047133 /0.313690185546875, so this is not merely
identity testing. Full color and quantization gates reproduce on expanded trace;
341 tests, Node syntax and py_compile pass. Previous trace preserved PRE_POLYNOMIAL.
Still pending: link lattice through input curves, and polynomial output through
clipping/gamut/output curves to the color input. No camera/production changes.

Closed mode0 ICC pipeline gate for explicit identity curves: all six100-byte
builder curve structures are exactly(2,0,0,255,255) plus zero padding. Native
polynomial input equals the R/G/B33^3 lattice exactly. Independent polynomial
then component clamp0..1 equals every captured RGB color input exactly.7302 and
7319 components are genuinely clamped in the two profiles. Computing all later
XYZ/Lab and16-bit encoding from that lattice and the builder16.16 coefficients
reproduces both complete CLUTs byte-for-byte. ICC_IDENTITY_CURVE_PIPELINE_PROOF
records strict curve precondition, trace/observer hashes and coverage.341 tests
and py_compile pass. This closes all stages for this identity-curve fixture only;
nonidentity curve interpolation and other gamut-policy paths still require their
own controls. No render/UI/camera changes.

Nonidentity two-point control: own-host public PF property40001018 changes only
red curve word4 from255 to230 after descriptor setup, before action103; setter
returns0 and readback equals exact one-word mutation. No source serialization.
Both ICC builder descriptions now contain(2,0,0,255,230) in first input curve,
other five curves unchanged. Separate FINE_DETAIL_ICC_CURVE_CONTROL trace and
ICC_LINEAR_CURVE_PIPELINE_PROOF retain this control without replacing baseline.
Independent256-sample linear curve plus cached evaluator matches every native
polynomial input exactly. Full curve->polynomial->clamp->output curve->XYZ/Lab
encoding produces both35,937-node CLUTs byte-exact; max final RGB discrepancy
2.220446049250313e-16, zero differing encoded bytes.341 tests, Python and Node
syntax pass. This validates bounded two-point nonidentity input curves; nonlinear
curves, output-curve property mapping and alternate gamut policies remain open.

Differential output-curve mapping: two separate in-memory red endpoint255->230
controls for40001019/40001065. Both setters/readbacks match exact one-word change.
1019 changes only the first curve in builder's second group (description offset
320);1065 changes none of the848 captured builder bytes. Initial post-RGB1019
hypothesis fails (RGB error.0980392156862745, many predicted CLUT byte differences),
retained as ICC_1019_POST_RGB_REJECTED. Actual1019 RGB and CLUT remain baseline;
its ICC first output curve changes to trunc(i*257*230/255), i0..255, ending59110.
Other two output curves remain identity. Corrected independent pipeline validates
both complete CLUTs and all768 output entries per profile for both controls.
1065 leaves these ICC tables unchanged; do not generalize to other compiler paths,
where separate earlier evidence maps1065 differently. Separate traces/proofs keep
baseline intact.341 tests, Python and both agent Node syntax pass. Nonlinear
controls and second-group channel1/2 semantics still need explicit experiments.

1019 channel1/2 controls completed: exact one-word endpoint255->230 mutations
reach corresponding second-group builder offsets420/520 in both profiles. Native
RGB, complete CLUTs and all768 ICC output-curve entries remain baseline; independent
pipeline matches all nodes and entries. This path consumes only channel0 as the
tested lightness output curve; do not infer the others are irrelevant elsewhere.
CH1/CH2 traces and proofs retain control provenance separately. Private agent now
parametrizes property/channel. compile_stock accepts the bounded configuration
only for its exact private agent path, properties1018/1019/1065 and integer
channels0/1/2, with known-hash observation required. Three gate tests cover wrong
agent, invalid fields/types and rejection before native start without the hash
gate.344 tests, py_compile and Node syntax pass. Production UI/export unchanged.

Nonlinear ICC input control completed: private 1018 channel0 curve replaced with
exact three points (0,0), (128,96), (255,255), zero-padded to100 bytes. Native
set/readback and both848-byte builder descriptions match only this mutation.
Independent quadratic B-spline samples plus observed monotonic finalization,
cached interpolation,19-term polynomial, RGB clamp, color/Lab transforms and
16-bit encoding reproduce both35937-node CLUTs byte-for-byte. Captured input
and RGB doubles also match with zero error. All768 output-curve entries per
profile remain identity. Evidence: FINE_DETAIL_ICC_CURVE_1018_CH0_mid96 trace
SHA256 db5468550ac4bcb01dcc888f941780c89b2ab5b098110c3104bbaa08021422c4;
ICC_NONLINEAR_CURVE_1018_CH0_mid96_PROOF_20261007.json. Scope is this bounded
nonlinear input case only; second-group nonlinear lightness mapping remains
unproved. Old213 route still returns80 with same missing legacy properties;
ICC equality does not resolve that route or prove camera compatibility.
344 tests, py_compile and private-agent Node syntax pass. No camera access,
installed DLL changes, public fixtures, UI/export changes or new build.

Nonlinear1019 channel0 control now independently verified with same three
points (0,0),(128,96),(255,255). Exact API mutation and second builder group
mapping validated. Both full CLUTs and captured input/RGB doubles remain
baseline; separate first ICC output curve changes254 of256 entries, preserving
endpoints. Quadratic B-spline plus finalization and cached sampling at i/255,
then trunc(value*65535), reproduces all768 output entries per profile exactly.
Trace SHA256 fc0da584c32feb4a79cdf531bee23a20df3f7f57a559747d4c54001674f4e12e;
ICC_NONLINEAR_CURVE_1019_CH0_mid96_PROOF_20261007.json. This strengthens separate
input-curve versus output-lightness interpretation for observed mode0 only.
Old legacy213 missing-property failure remains unchanged.344 tests and verifier
py_compile pass. Original fixtures, installed DLLs and working build untouched.
Pending: additional curve shapes/channels, mode1/2 builder semantics, and origin
of missing legacy1007 metadata; no universal or physical support inferred.

Nonlinear1019 channel1/2 follow-ups: exact three-point mutations reach their
respective second-group builder blocks. Both profiles retain baseline RGB,
CLUTs and all768 output entries; independent reconstruction is exact. Trace
SHA256 CH1 d579bb002fb53728fa38b4e42f9e17759508145250ae874bccc5ad16931cb3a6,
CH2 8e19e6ca90e14ed3c639e8c5df16051fb5f6f9381741cf3433d50accc09aa8ab.
Separate ICC_NONLINEAR_CURVE_1019_CH1/CH2_mid96 proofs preserve provenance.
This is observed mode0 behavior, not globally unused PF3 properties.

Known-hash static builder extraction extended to entry windows5930,6260,7810.
Executable assertions check5930 requires EDX3 and stack argument9/10, with
local ESI40/32;6260 requires EDX3 then computes unsigned1024/(argument-1).
7810 first two observed entry calls normalize curves through f490. These are
instruction-level facts, not validated parameter semantics or safe complete
synthetic layouts. No calls into unobserved modes yet.344 tests and py_compile
pass; original sources, installed DLLs and public build unchanged.

ICC dispatch reference added as research-only pure header inspection, never
used by camera transport. Static hash-gated assertions tie mode1 header reads
at4/8/12 and payload offset20 to native register/stack forwarding. Mode1 unsigned
node count<=10 selects5930, whose header gate only accepts9/10 with EDX3;
larger values select6260, where local step=unsigned1024/(nodes-1). Header acceptance
is explicitly not payload acceptance, especially large counts yielding step0.
Mode2 signed prefix(+47c)/total(+f0c) comparison rejects prefix>total; zero/equal
counts take unsplit route, otherwise split path. Width read at+f10; curve-group
offsets4/130 and matrix25c retained as static argument facts. Negative counts are
represented faithfully as branch behavior, not accepted safe data. Four new
test methods cover boundaries, unsigned/signed distinctions and truncation;
348 full tests and py_compile pass. Next: map full mode1 grid payload reads and
mode2 record allocation/count invariants before any native synthetic invocation.

Mode1 payload sampler static map: both5930/6260 call7020 with EDX node count,
payload pointer from third stack argument and coordinates.7020 reads uint32
elements at index(axis0*N+axis1)*N+axis2, then offsetsN^3 and2*N^3 for the
other two output channels: planar, not interleaved triples. Native conversion
uses signed cvtdq2pd plus exact high-bit correction constants(0,4294967296),
so all uint32 values are preserved, not interpreted as signed negatives.
Fraction comparisons dispatch through73e8 table; four-vertex weighted sums
match tetrahedral structure statically, but independent native equivalence is
still pending. Extractor stops before jump-table data, retains full5930/6260
windows and asserts sampler indexing/output-store instructions and constants.
Research decoder limited9..33 nodes requires exact20+12*N^3 bytes and accepted
mode1 header. Synthetic planar/index/high-bit/truncation tests added;349 full
tests and py_compile pass. No native unobserved-mode calls, camera access or
production pipeline changes. Pending: direct isolated sampler proof, complete
coordinate scaling and ICC color conversion behavior for mode1.

Native7020 synthetic interior proof completed in own hidden x86 host. Own-memory
thunk supplies ECX output, EDX nodes, XMM3 coordinate0, stack payload pointer
and coordinate1/2 doubles; installed DLL bytes unchanged. First attempt rejected
unsupported Frida ABI namecdecl before target invocation; host cleaned in finally.
Correct Windows mscdecl retry and strengthened coverage rerun match136/136 cases
byte-exactly, maxerror0, output trailing guardsa5 intact. Four node sizes9/10/17/33,
six fraction orders, ties/integer points and24 seeded random interiors each;
synthetic uint32 planes exercise high bits/nonlinear values. Independent planar
decoder, sorted tetrahedron vertices and base-relative weighted sum reproduce
all outputs. Endpoints>=N-1 explicitly rejected: zero-weight neighbor reads need
separate padded/native evidence, not assumed safe. MODE_ONE_SAMPLER_PROOF_20261007
retains agent/hash/coordinates/native and expected doubles.351 tests, py_compile,
Node syntax pass. No camera, EOS Utility session or public build modifications.
Next: endpoint address behavior with own padded arrays and full mode1 coordinate
scaling/color conversion; mode2 safe input layout remains independently open.

Endpoint7020 proof added with explicitly padded own arrays:168 native cases
across9/10/17/33-node planes, including all eight corners and single/multiple
maximum axes. Padding0 versusffffffff yields80 distinct equal-output pairs;
all168 outputs byte-exact independent tetrahedral reference, maxerror0,
trailing output guards intact. Native reads still reach zero-weight neighbors;
reference may skip them mathematically, not justification for unpadded native
calls. Public research sampler defaults interior-only; explicit boolean
allow_endpoints enables tested closed-domain math.352 tests and py_compile pass.
MODE_ONE_SAMPLER_ENDPOINT_PROOF_20261007 retains separate endpoint evidence.
Static5930 coordinate constants independently decoded/asserted: multiplier256,
upper clamp255, neighbor increment1; grid-unit coordinate uses division by
local step40/32. Full ICC grid loop denominator and color path still need
independent validation. No camera sessions or installed/public-build changes.

Full mode1 native builder synthetic experiment: headers(1,1,3,N,0), planar
ramps at N9/10/17/33 accepted through exportedMLIBcreateCustomMLDataEX; four
217828-byte ICCs, 12tags, sharedA2B0/1/2 mft2 grid33. Input buffers+guards unchanged.
MODE_ONE_BUILDER_PROBE_20261007 retains synthetic cases/native profiles and
hash/path evidence; this does not validate model registration or arbitrary PF3.
Large-grid constants statically asserted1024 multiplier/1023 clamp, local
step1024/(N-1); small-grid multiplier256/clamp255 steps40/32.
Independent full33^3 reconstruction from planar ramp, sampler, scaling,
RGB-to-XYZ mode10, Lab and16-bit encoder currently FAILS exact-byte gate:
differentBytes6/2/8/8 for N9/10/17/33. Every differing node is on grayscale
diagonal; L matches, a or b differs by one uint16 code32767 versus32768.
Detailed coordinates/codes/hashes retained in MODE_ONE_BUILDER_REFERENCE_PROOF
with exact=false and nonzero verifier exit; do not weaken byte-exact gate.
Possible floating operation-order/cube-root effect not yet proved.352 suite
tests and py_compile/Node pass separately; new full-chain verifier remains
intentionally failing. Next: capture native XYZ/Lab doubles on these diagonal
nodes and compare inline mode1 Lab arithmetic to shared helper reference.

Mode1 read-only diagonal observation now captures33 RGB/XYZ and writer Lab
triples per four synthetic profiles:132 samples, all35937 color calls per
profile accounted. Entry1000 caller gates5d74/668a;2590 writer geometry gated.
MODE_ONE_BUILDER_OBSERVED trace SHA256
bb55117626d22e7af9ddf774b14ca78b83a3aa51e72d0ba02b3bd3ece29c49e0.
Observer CLUTs equal prior unobserved CLUTs exactly. Independent Lab from
captured nativeXYZ matches all132 nativeLab samples with zero error, and
nativeLab->Lab16 encoding matches every captured diagonal node. Attribution
report MODE_ONE_DIAGONAL_ATTRIBUTION records RGB-to-XYZ error up to
1.1102230246251565e-16. Thus mismatch is upstream of Lab/encoder for these
samples, not a quantizer defect; full independent chain still fails its strict
byte gate. Static RGB/XYZ disassembly bounded to function return1469 retained.
Next: separate custom native SSE2 pow29ad0 rounding from matrix accumulation
order and verify predicted RGB exactly.352 tests, syntax checks pass; no camera
sessions, installed binaries or working build altered.

Mode1 neutral-axis mismatch resolved without weakening exact-byte gate.
Direct own-memory SSE2 pow29ad0 thunk shows all396 decoded diagonal components
equal Python reference exactly; nativepow was not the cause. Python3.12+ sum
uses compensated float accumulation, unlike observed scalar SSE additions.
Research RGB modes10/11 now explicitly compute(products0+products1)+products2.
All132 captured XYZ values and Lab values now exact, all diagonal encodings
exact; four complete synthetic mode1 CLUTs (143748 nodes) byte-exact,0 differing
bytes. Static known-hash mode10 matrix constants asserted in correct XYZ order.
Original failure retained as MODE_ONE_COMPENSATED_SUM_REJECTED summary; current
MODE_ONE_BUILDER_REFERENCE_PROOF passes against unchanged original native trace.
Updated observed trace SHA25676de9beee576e0233e723d20d939f5ef59d54fa925bf15a9e36b73c02cd9e2d2
contains nativepow decoded values. Added exacthex regression for affected neutral
sample. Existing full real captured ICC modes10/11 color-chain verifier still
matches both CLUTs.353 tests, py_compile/Node pass. Scope remains synthetic mode1
field4=1, not other modes, full metadata/padding serialization or camera support.
Next: nonlinear/mixed synthetic grids, other mode1 color selector and mode2 input
layout; original legacy1007 metadata failure remains independent and unresolved.

Mode1 nonlinear mixed-grid coverage completed for N9/10/17/33: synthetic
planes include cross-channel r*g and quadratic b*b modular terms, bounded255
or1023. Selector1 full-chain independent reconstruction byte-exact for all
four143748-node outputs; trace SHA256f74b478af0c1f12253076533cd86f9356364f3ef3f7857862238ad784c77586f.
Selector2 added as bounded separate input (header field4=2), using distinct
native inline color path. Both mixed and ramp controls reproduce exactly via
mode11 color reference; four profiles each, no source/guard mutations. Mixed
selector2 trace SHA256f51a285b78ed85d8f55379afa88b4789325621360dfc8d805be2c1d64917a5bd;
ramp selector2 trace SHA2568fab3d20b32987c7bb157febd2e4513003998c430d93c9e43c84913d5c5b77cb.
Separate selector/pattern filenames and provenance checks preserve prior ramp
evidence. Across16 mode1 profiles (2patterns x2selectors x4node sizes),574992
CLUT nodes match byte-for-byte. This is synthetic mathematical conversion
coverage, not metadata/padding/full serialized ICC equivalence or any camera
validation. Observer rejects selector2 until its call path is mapped separately.
353 tests, py_compile and Node syntax pass. Next mode2 layout/allocation paths
and legacy1007 remain open; production UI/export/build unchanged.

Mode2 layout correction from linked caller/entry evidence: earlier dispatch
reference mislabeled+25c as matrix by extending mode0 assumptions. Actual7810
normalizes9 curves, groups at4/130/25c; third group arrives in first stack
argument. Polynomial240-byte rows are at388, second stack argument, signed
16.16 scale1/65536 with19used words per80-byte row. Reference and tests corrected,
hash-gated extractor asserts9 calls/argument loads/coefficient scale.
Variable records begin atf10: its count also defines shared capacity/stride,
not an independent header followed byf14 record origin. Kind atf08,total atf0c;
record stride4+16*first count. Split allocation8+count*stride, first8bytes
kind/count then records. Copies each active record count and16-byte elements;
inactive capacity is not initialized by observed copy loop, so reference refuses
partial records rather than fabricating byte-exact padding. Bounded copy-only
reference tests unsplit/split, exact lengths and partial-capacity rejection;
354 tests, py_compile and static assertions pass. No native mode2 call yet.
Next: identify meaning/use of16-byte records and scalar478, then zero-record
mode2 control in own host when all remaining native reads are bounded.

Mode2 consumer map links known fa40 selective/axis stages: first records kind1
gate before second curves; companion+480 kind2 gate; later second records kind1.
Field478==2 selects numericRGB/XYZ11, otherwise10 (sete+10), statically asserted.
Private full exported builder control with nine identity curves, identity19-term
polynomial at388, zero record kinds/counts/companion and selectors1/2 now runs
successfully in own hidden host. Two217828-byte ICCs; input buffers/guards intact.
MODE_TWO_EMPTY_BUILDER_PROBE trace SHA256
a2422c3d26aba19c9a2b4ace6afb87422b3936c9e9335d72fb21fe9314a30f1b.
Independent full33^3 control: selector2 matches byte-exact35937 nodes; selector1
FAILS625 bytes across619 nodes against direct identityRGB->mode10->Lab hypothesis.
MODE_TWO_EMPTY_REFERENCE_PROOF records exactfalse/true and mismatch examples;
verifier exits nonzero, no gate relaxed. Additional selector1 processing remains
to be attributed, not a native failure or proof of invalid ICC.354 existing
tests and syntax pass separately. No sessions/transport/installed DLL changes.
Next: capture mode2 polynomial/input/output curves and RGB immediately before
1000 for selector1; reuse earlier luminance/color references where justified.
# Mode 2 selector-1 fixed-point stage: partial attribution

### Read-only full property sequence proof (2026-10-08)

Private `compiler_object_probe.py` invoked the observed content object's size
and sequence writer slots (0x20/0x24) into owned memory, without Reflect,
property mutation, camera access or original-file writes. The known-hash
Fine Detail reference produced exactly 434479 bytes; returned count matched
the allocation and both trailing A5 sentinels remained intact. Independent
decoding and selection of original records using the observed allowlist gave
the same bytes, SHA256
`9635b1d9e92ecbe02eafd5fa33c3d468e3a44b61339a3b640a966aea98e7d20c`.
The original parser left no unexplained tail. Private evidence:
`COMPILER_OBJECT_METHODS_20261008.json`, `sequenceComparison`.
This establishes ordering, filtering and record encoding for this reference
content object, not whole-file checksum/Reflect correctness or universal
camera support. Next independent branch: other content classes and bounded
sequence-write failure behavior.

The subsequent bounded-write probe tested capacities 0, 1, 7, 8, 31, 63,
255, 1024, size-1, size and size+1 in fully allocated owned buffers. All 11
outputs matched independently selected complete-record prefixes; bytes past
the declared capacity remained A5. Insufficient capacity returns -1 but can
leave earlier complete records written (e.g. 434478 capacity leaves 434467
bytes). This sequence writer is therefore not transactional. Exact-size and
size+1 calls return 434479 and reproduce the complete sequence. These are
bounded cases for the known Fine Detail object, not a proof of all arbitrary
inputs; callers must discard a failed sequence rather than use its prefix.
No production implementation was changed.

Expanded sequence experiment: 344 unique mode/capacity cases, crossing every
selected record's end at -1/0/+1, plus the initial small and full capacities.
Modes 0 and 0x4949 produce little-endian headers and reverse each complete
numeric type-3/type-4 element relative to the original big-endian file;
0x4d4d and 1 reproduce big-endian headers/data. Raw types stay unchanged.
All complete prefixes matched the independently decoded original records,
all return values matched full-success versus -1 partial failure, and all
bytes beyond the declared capacity remained A5. This proves these bounded
cases for this object; other content classes and malformed record lengths
remain separate investigations. Evidence remains private in
`COMPILER_OBJECT_METHODS_20261008.json` (`native.bounds`).

Read-only cross-format class inventory: known-hash Emerald PF2
(`26fe253a44c698b2cf5f70763802c7f97d2d26267ca215f1ff5c77402fdeb33d`)
uses content vtable 0xbe224, while its unchanged PSE PF3
(`7330d7f6ec663b77406740a224d0867ea4f028689a544682be3a3770036432d5`)
uses 0xbf0d4, matching Fine Detail's content class. Both share slots 0x20
(size 0x512a0), 0x24 (sequence write 0x51090), 0x10 (0x50c00) and 0x14
(import 0x52110). PF2 instead uses filter 0x538f0, Reflect 0x53920 and
slot 8 setter 0x53d00; PF3 uses 0x56ea0, 0x56ed0 and 0x572d0.
Only method pointers were inventoried; no new PF2 method was invoked.
Private evidence `CONTENT_CLASS_PF2_20261008.json` and
`CONTENT_CLASS_EMERALD_20261008.json`. Next: statically resolve the PF2
filter and checksum branch before applying the shared sequence probe.

Static PF2 filter 0x538f0 uses the same 0xffff7fff mask and 21 IDs at
0xbe268. Its allowlist is a strict subset of PF3's 31-ID list: PF3 adds
1034, 1035, 1060..1065, 1070 and 1071. This class's PF2 serialization
therefore excludes the arbitrary 33-node table records, even though the
shared record writer can encode their types. PF2 Reflect 0x53920 also sums
serialized property bytes, adds 0x22e1 in state1, appends checksum/terminator
and applies the seed-12 cipher. It writes version/header constant 0x01200000
as a native little-endian word. Its normal stream tail likewise does not
check the position/write return status before returning zero. These are
static observations, not injected stream-failure or whole-file tests.
Private hash-gated extractor and evidence:
`extract_pf2_serialization.py`, `PF2_SERIALIZATION_WINDOWS_20261008.json`.

Native read-only sequence confirmation: Emerald PF2 produced exactly 1207
bytes (SHA256 992679c8ec10ffcd013cf6f13128e6ec87fe996fc61c44078ad286ea2ae891a7),
matching all independently decoded selected original records. Its 100
filter decisions and 140 endian/boundary cases matched. Unchanged Emerald
PSE PF3 produced exactly 435500 bytes (SHA256
ee154f113c7fe0a4a8683f6e4e8a2077b802716b223773b2ffa89e124fcc0990),
with 100 filter decisions and 44 bounded/endian cases matching. Neither
original left an unparsed tail. An initial exhaustive Emerald report hit
Frida's 128MiB message limit; that run supplied no verified result. After
the owned host terminated, a fresh compact-report run passed. This was a
laboratory transport limit, not a Canon compiler rejection. Private evidence:
`CONTENT_SEQUENCE_PF2_20261008.json`, `CONTENT_SEQUENCE_EMERALD_20261008.json`.
The larger Emerald PF3 sequence also establishes that Fine Detail's
434479-byte property length is not a universal PF3 size invariant.

Read-only whole-file framing/checksum observations for the same references:
Fine Detail (434511 bytes, 28 records) and Emerald PF3 (435532 bytes, 42
records) each contain 0xfffe whose value equals the sum of all bytes before
that checksum record, with zero delta. Official Emerald PF2 (1243 bytes,
11 records) has no 0xfffe checksum record. All three finish at 0xffff,
have exact declared body lengths, no unparsed tail and exact independent
seed-12 re-encoding. The PF2 absence is an actual reference variation, not
a parser failure or reason to invent a checksum requirement. Static Reflect
emission of a checksum therefore does not prove every accepted input had
one. Private verifier/evidence: `verify_sequence_file_checksums.py`,
`SEQUENCE_FILE_CHECKSUMS_20261008.json`. Original files were not changed.

Five public-safe synthetic regression tests now cover checksum absence with
a terminator, the observed 0x22e1 checksum bias, an empty parser tail without
a terminator, every nonempty truncation of a checksum record, and explicit
opt-in for high-bit record IDs. They preserve the distinction between an
inventory parser and a strict whole-file validator: successful consumption
alone is not proof of termination or checksum correctness. No proprietary
fixture was added. `py_compile` and the complete 377-test suite passed.

PF2 record-reader static follow-up: observed slot0x2c 0x532d0, complete
method through 0x535c5. Checksum handling is conditional on record ID fffe
at 0x53469; mismatch at 0x53572 sets content state+0x10=-1, but the method
returns consumed bytes rather than an error code. The loop compares its
cursor against the supplied end, with no explicit ffff stop branch in this
method. Thus absent checksum is not rejected by this local check, and
consumed bytes cannot alone establish validity. Caller validation remains
unmapped here. Our research parser deliberately stops at ffff and preserves
trailing bytes; it is not an emulation of this native loop. Initial candidate
slot0x0c 0x4f2d0 proved to be carrier output conversion, not record reading;
no function was invoked on that mistaken assumption. Evidence appended to
`PF2_SERIALIZATION_WINDOWS_20261008.json`, hash-gated instruction checks.

Reader caller attribution: inner/delegated load method invokes virtual0x2c
at 0xb068 on its field+0x1c content object, consistent with the native
inventories. It passes 0x4d4d after body decoding at 0xb050. The immediate
normal tail frees its buffer and returns zero at 0xb074 without checking
the reader's consumed count or content state. Consequently successful
reference creation is not sufficient evidence of checksum acceptance;
invalid content state may be exposed by later methods (e.g. previously
mapped state=-1 gates). This is a local static chain, not a claim that every
outer caller ignores state. `find_record_reader_callers.py` retains 14
linear-disassembly candidates, but the scan is not exhaustive because
embedded data can stop decoding; only the 0xb068 receiver is attributed.
Private evidence `RECORD_READER_CALLER_CANDIDATES_20261008.json`.

Native checksum-state experiment on owned hidden host: original known-hash
Fine Detail opened with content state0; private copy changing only one bit
of the decoded checksum data opened successfully with the same content
class 0xbf0d4 but state-1. This proves the open-success/validity distinction
for this PF3 reference. Original hash was checked again after execution.
No carrier compilation, Reflect, camera session or installed DLL change.
An initial harness run attempted Initialize twice in one host and failed
on its second call; corrected harness initializes once and both observations
passed. Private script/evidence `checksum_state_probe.py`,
`CHECKSUM_STATE_PROOF_20261008.json`; invalid scratch remains private.

Expanded native opening experiment adds whole-record removal variants with
the outer body length updated exactly: checksum absent, terminator absent,
and both absent. All three CreateRef calls succeeded with content state0
and the same PF3 content class; only checksum-present-but-wrong produced
state-1. Inputs ended on complete record boundaries, not partial reads.
This demonstrates permissive opening on this DLL/reference, not acceptance
for carrier compilation or cameras. State0 must not be treated as a strict
whole-file conformance certificate either. Canon export remains unchanged
and continues emitting its checksum/terminator; no workaround removing
them was introduced. Five native observations now have explicit state
assertions in `checksum_state_probe.py` and private report hashes.

Public getter observation across those five references: GetPropertySize
returns0 for 0x114, 0x40001002 and 0x40001070 even for checksum-invalid
state-1, reporting sizes4/32/215628. GetPropertyData on that same invalid
reference returns45 (0x2d) for all three. Original and complete-record
removal variants return0 for all data reads. Thus opening plus size lookup
is still insufficient; actual public data-read return codes expose this
invalid-state gate without reading private object fields. Fifteen paired
size/data cases are recorded and asserted in the private probe. No checksum
removal workaround or production validation change was introduced.

Getter destination experiment: A5-filled buffers with two trailing A5
sentinels show that the three state-1 GetPropertyData calls returning0x2d
do modify their outputs: all destination data bytes become zero, while
sentinels remain intact. They do not match valid property outputs. A first
test assuming unchanged buffers correctly failed; revised observational
probe retained the actual zero-fill evidence. Complete-record removal
variants yield property hashes identical to the original for the three
sampled properties. Error return codes must therefore be respected even
when allocated output data looks structurally consumable; this is not a
demonstration that the previous camera-black incident had this cause.
Fifteen destination/hash cases remain private in CHECKSUM_STATE_PROOF.

Production-source cross-check (read-only): canon_engine.EdsCFParse.get_property
checks both size and data return codes before returning bytes; inspected
dynamic_camera_agent.compilePf3 and rp_loader_agent.compilePf3 expose an
output buffer only when rcGet==0. No ignored-error path was identified in
these three routines; this is not a whole-repository safety proof. Three
synthetic regression tests in test_canon_property_error_gate.py confirm
that a zero-filled rc0x2d buffer raises, genuinely successful zero bytes are
returned (no unsafe pixel-value heuristic), and an expected-size mismatch
prevents the data call. No production code changed. py_compile and all
380 tests passed without requiring Canon fixtures for these new tests.

State1 origin remains unresolved: bounded static scan of 0x4de00..0x57400
found no immediate mov [receiver+0x10],1; expanding to 0x1000..0x57400
retained generic assignment candidates, including unrelated record fields
and stack arguments. The apparent 0x5371a store is explicitly zero after
xor ecx,ecx and belongs to output construction, not proven content state.
This negative linear scan does not prove state1 unreachable: register or
other instruction stores and code/data boundary decoding remain possible.
Private `find_content_state_assignments.py` and candidate JSON preserve
windows for subsequent receiver attribution. Do not infer header semantics
or introduce the checksum bias without establishing the actual state source.

Complete PF3 reader 0x53fb0..0x542a5 likewise compares the checksum directly
with the preceding-byte sum (0x54252) and sets state-1 on mismatch; no
state1 assignment or 0x22e1 adjustment occurs in this method. Native
private Fine Detail variant with only checksum +=0x22e1 confirms state-1,
three size queries rc0 and three data reads rc0x2d. This rejects the
hypothesis that the writer's state1 bias is itself an accepted checksum
flag in this normal opening path. Source of state1 remains open; it must
not be treated as an acceptance workaround. Six references / eighteen
paired reads are now retained in CHECKSUM_STATE_PROOF; production unchanged.

Follow-up state search includes inc/dec/or/and/add/sub/xor as well as mov
into +0x10 candidates; no additional non-mov content-region transition
was found by this bounded linear scan. It retains 248 generic candidates
without claiming receiver identity. Separately, complete property-size
method 0x53850..0x538ed and PF3 wrapper 0x54ca0 show that PF3 tail-jumps
to PF2 size lookup at 0x54cbc. These vtable slot0 functions are getters,
not constructors. The wrapper clears output size/type and does not test
content state; this aligns with the successful size lookups on state-1,
without proving every callee branch is state-independent. State1 origin
remains unresolved, not silently assigned to a header or model family.

Read-chain attribution now explains zero outputs on error: public export
0x3d40 dispatches outer virtual0x18 ->0x12840, which calls0x5a540 with
(destination,0,size) at0x1287d before delegating through field+0x24 slot0x14.
Observed inner0xac70 delegates field+0x1c virtual4 to PF3 0x54c80, whose
state-1 gate returns0x2d; otherwise it tail-jumps PF2 0x535e0 with the same
gate. Outer returns the delegated result at0x128ed. Thus zero data is
wrapper initialization, not recovered content from an invalid reference.
Hash-gated call-site assertions retained in PF2_SERIALIZATION_WINDOWS.
No production path or camera operation changed; all380 tests passed.

Known Emerald PF2/PSE-PF3 record comparison preserves original bank IDs:
PF3 contains paired low/high IDs for 1002,1009,100a,100d,1011,1018,1021,
1029 and1030..1035, plus 1070/1071 (215628 bytes each). PF2's1010 record
is absent from PF3, which instead includes1023/102b (8 bytes each).
Normalizing IDs into a dictionary initially revealed collisions; the
comparison now retains ordered lists of original IDs and exact cross-bank
type/data matches, not destructive overwrite. This is one supplied
conversion pair, not evidence that every PF3 uses both banks identically.
Private script/evidence `compare_emerald_records.py`,
`EMERALD_RECORD_COMPARISON_20261008.json`; no proprietary assets added to
production and all380 tests passed.

Cross-bank exact matches in this pair: PF2 1009,1018,1021,1029 data/types
match both corresponding low/high PF3 records; 100c matches its sole PF3
record. Record1019 differs in only six bytes/words: indices25/50 become2,
28/29/53/54 become255, all from zero. These positions repeat in the two
25-word blocks following the first, consistent with a structural/default
initialization rather than a floating-point rounding delta; detailed
semantic attribution remains separate. Same-size1002 changes are metadata
bytes (11 changes low bank,21 high). Comparison now records original IDs,
cross-bank equality and exact changed offsets/words, not just whole hashes.
No claim that all conversion pairs behave this way.

The six1019 changes are now attributed using the already independently
tested curve normalizer: PF2 block0 is [2,0,0,255,255] with normalized
points(0,0),(1,1), domain256; blocks1/2 have count0 and zero words. PF3
has that identity curve in all three100-byte blocks. Thus this PSE
reference initializes the two previously empty curve blocks rather than
altering the first curve or introducing rounding changes. This explains
the exact six changed words for this pair; it does not establish that a
count0 curve is valid input to every MLib stage. Private comparison now
includes all six block descriptions and normalized pairs.

Cross-ID data search (same stored type, at least8 bytes) found no exact
matches between differing normalized IDs in this conversion pair. Specific
candidate PF2 1010 is type4/two words[0,0], whereas PF3 1023 and102b are
type4/two words[1,0]. Previously observed native getter fallback from
missing1023/102b to1010 is therefore a compatibility mechanism, not proof
of equal stored values or safe replacement. Private comparison records
the words and negative cross-ID search; no semantic meaning is assigned
to the first word solely from this pair. All380 tests passed.

Native public fallback confirmation with original read-only Emerald files:
PF2 GetPropertySize/Data returns0 and8 bytes[0,0] for1010,1023,102b despite
only1010 being stored. PF3 returns rc80 for1010 size lookup, and returns0
and8 bytes[1,0] for1023/102b. This proves fallback is directional in these
observed classes, not a symmetric alias relationship. Private inventories
CONTENT_CLASS_PF2/EMERALD now include fields and exact returned bytes.
No setter, Reflect, carrier compile or camera session was used.

## Read-only compiler object dispatch observation (2026-10-08)

Private `compiler_object_probe.py` opened the hash-verified original Fine Detail
PF3 in an owned hidden x86 host. No property writes, carrier import or camera
access occurred; reference release and host cleanup ran in finally blocks.
Evidence: `COMPILER_OBJECT_METHODS_20261008.json`.
The actual outer vtable is RVA `0xb8df0`; setter slot `+0x1c` is `0x13790`.
Static disassembly shows this wrapper delegates through object field `+0x24`.
The observed delegated vtable is `0xb81d8`, setter `+0x1c` is `0xb0d0`,
not the previously identified importer caller `0x51590`.
`0xb0d0` handles property `0x40008001` specially; otherwise it delegates
through field `+0x1c`, virtual slot `+8` at `0xb137`.
All eight observed slots in both vtables point to executable memory.
The chain to the legacy importer remains unproved: next read-only probe
must inspect that third object rather than treating aligned pointer-table
candidates as genuine vtables. These are compiler objects, not EDSDK
registration transactions. Production code and the confirmed build unchanged.

### Third delegation resolved (2026-10-08)

The repeated owned-host read observed inner field `+0x1c` holding an object
with vtable `0xbf0d4`. Its setter slot `+8` is `0x572d0`; its slot `+0x14`
also contains importer `0x52110` directly. All eight sampled methods are
executable. Hash-gated static checks now reproduce this conditional API chain:
`EdsCfpSetPropertyData 0x3fc0 -> 0x13790 -> 0xb0d0 -> 0x572d0 ->
0x53d00 -> 0x51590 -> 0x52110`.
The compiler property `0x01000203` takes the generic setter branches, unlike
special camera-ID property `0x01000001`. Setter object state `+0x10 == -1`
returns `0x2d`, while `+0x10 == 1` returns `9` before generic delegation.
This is a structural, conditional reachability proof, not a successful carrier
import experiment. It neither manufactures the opaque `0x1007` record nor
changes any camera-registration property. Evidence and asserted instruction
windows are in private `LEGACY_IMPORT_WINDOWS_20261008.json` and
`COMPILER_OBJECT_METHODS_20261008.json`. Next issue: inspect genuine legacy
input provenance and import status, keeping initialized-but-empty metadata
distinct from a validated payload.

### Legacy classes 6/7 import status caveat (2026-10-08)

Hash-gated static checks of `0x52faa..0x53207` confirm both classes use
16752-byte input, marker 1 and body length 16712. Four 4096-byte regions at
`0x170/0x1170/0x2170/0x3170` pass through transform `0x2e30` with alternating
seeds `0xb8ed/0x33137`; this branch is not the old 1460-byte `0x1007` branch.
Size mismatch jumps to `0x531fa`, setting return accumulator to `0x50`.
However, after allocation/copy `esi` has already been zeroed at `0x52fbc`:
marker or body-length mismatch jumps straight to `0x531ff`, returning that
zero without the subsequent property stores. Thus a zero import status alone
cannot prove a carrier was ingested. This is a static control-flow finding;
no malformed input was executed. Future round-trip experiments must compare
read-back properties/content, not only status. Private evidence and exact
instruction assertions: `LEGACY_IMPORT_WINDOWS_20261008.json` and its extractor.

### Legacy import transform independently checked (2026-10-08)

`0x2e30` jumps to `0x2db0`: bytewise XOR with the 512/513-byte tables,
seed-index wrapping and constant `0x37`, matching existing research `decode`.
Owned hidden-host `legacy_cipher_probe.py` compared 45 synthetic cases exactly:
seeds 0,511,512,513,0xb8ed,0x33137,0x3f194,0x252e4,0x2d456 and lengths
0,1,512,513,4096. Native output equals independent Python for every byte.
This covers seeds used by both oldest and class6/7 imports, not carrier
semantics or registration. First attempt rejected Frida ABI name `cdecl`
before invocation; corrected Windows x86 identifier `mscdecl` passed.
Both attempts cleaned owned hosts. Evidence:
`LEGACY_CIPHER_SYNTHETIC_PROOF_20261008.json`. No installed DLL modification,
carrier import, camera session, production or release change.

### Complete import entry size/header map (2026-10-08)

The extractor now independently decodes and asserts header predicates for all
ten dispatch classes. Classes 1..9 require input sizes respectively
8164,8168,8528,16720,16744,16752,16752,78980,83076 bytes.
Every one checks marker 1 and declared body size `inputBytes - 40`.
These are importer requirements, not a model-support registry; classes6/7
share an entry and cannot be distinguished by size alone.
Class10 instead starts by allocating/copying the caller-supplied length and
then reading fields at fixed offsets. No fixed-size/header predicate is
observed in its entry window. This does NOT establish safe arbitrary-length
import or justify supplying truncated/synthetic carriers. Further control-flow
and property-store bounds must be mapped before any class10 import test.
Structured evidence: `allClassHeaderGates` in the private import-window JSON;
the known size map and every marker/body-size relation are asserted on rerun.

### Class10 body mapped, not a full33 import proof (2026-10-08)

Complete linear branch `0x52e24..0x52fa7` has fixed stores:
offset8/32bytes->1002, offset2c/2->1009, offset2e/32->1002,
offset50/4->1031, offset58/4->1032, offset5c/4->1033,
offset68/4->1034, offset6c/4->1035. The repeated 1002 property is observed
literally and must not be silently renamed. Offset54 contributes 1030 after
a comparison against7. A variable region at `0x28 + u16(offset70)` with
length `u16(offset72)` is passed to `0x50e20`.
No direct 1022/102a or large LUT-table store occurs in this branch body;
nested callees remain to inspect, so this is not proof that tables are absent
from the complete operation. Bounds of the variable region are not checked
in this body. No carrier import was executed. Exact store instructions and
complete body are now asserted/exported as `class10BoundedBody` in private
import evidence. Initial extractor window omitted part of terminal ret;
corrected to encompass all three ret bytes before accepting the evidence.

### Variable-region dispatch and return semantics (2026-10-08)

Complete `0x50e20..0x51073` loop dispatches parsed records: tags100a/100d
are stored via51500, tag2001 aliases100a, ffff terminates. A leading2fff
wrapper copies the remaining bytes, applies the same XOR transform with
seed22e1, and recursively invokes50e20. Unknown tags advance without a
direct property store. These are local dispatch facts, not proof of nested
decoder bounds or arbitrary opaque-record semantics.
The normal return is consumed bytes (`esi - inputStart`), not rc; recursive
path adds wrapper bytes. Class10 does not include this return in its result
accumulator. This further rules out treating import rc alone as proof of
complete ingestion. No direct large-LUT store appears in this dispatcher;
deeper4de70/4a120 record construction still needs examination.
Exact instructions now asserted in private `variableRecordParser` evidence.
Synthetic XOR equivalence extended to seed22e1: all50 native/reference cases
exact. Own hidden laboratory host cleaned; no carrier import or camera access.

### Typed record construction dispatch (2026-10-08)

`4de70` accepts types1,2,3,4,ffff; the four-entry jump table sends all1..4
to the same record initializer. `4a120` uses a separate dispatch:
1/2/ffff copy raw bytes; 3 copies16-bit elements; 4 copies32-bit elements
through8d70. Element loops use `length>>1`/`length>>2` after destination
zero-fill, so incomplete trailing elements are not copied by those loops.
The expected-size checks in4a120 concern the record's stored allocation
size/type, not the available source-buffer span. The routine receives no
source-end pointer. Thus these checks do not establish safe truncated
carrier parsing. Numerical endian/copy equivalence remains to test with
bounded synthetic records in an owned host; no malformed carrier executed.
Dispatch tables and relevant instructions now asserted in private
`typedRecordConstruction` evidence; production unchanged.

### Native 32-bit record reader endian proof (2026-10-08)

Bounded synthetic `record_word_probe.py` calls only known-hash8d70 in an
owned hidden x86 host. Twenty cases cover zero/asymmetric/high-bit/all-FF
words and modes0,4949,4d4d,1. Every value matches independent int.from_bytes:
0/4949 interpret little endian; nonzero non4949 modes tested interpret big
endian. Cursor advances exactly4 bytes and all input buffers stay unchanged.
This validates the shared32-bit reader, not full typed-copy behavior or safe
record bounds. Private evidence `RECORD_WORD_ENDIAN_PROOF_20261008.json`.
Reference functions were not promoted to production. Host cleanup completed;
no camera access or carrier import.

### Typed-copy numerical proof (2026-10-08)

Extended the owned-host word probe with140 bounded synthetic copies through
4a120: five types1/2/3/4/ffff, modes0/4949/4d4d/1 and lengths1/2/3/4/7/8/17.
All outputs, success flags, allocated lengths and unchanged input bytes match
an independent chunk-wise Python reference exactly. Types1/2/ffff preserve
raw bytes; types3/4 reverse each complete2/4-byte element for tested nonzero
non4949 modes and retain zero-filled incomplete tails. Every native allocation
was freed in finally, and the host cleaned. This covers unbounded-expected-size
record copies only; it does not prove source-span checking or full carrier
ingestion. Evidence `RECORD_TYPED_COPY_PROOF_20261008.json`;20 word-reader
cases also revalidated. No production or installed DLL changes.

### Expected-size restrictions checked (2026-10-08)

Synthetic typed-copy matrix extended to200 cases: expected size4 versus
input sizes2/4/6 for all five types and four endian modes. Type2 alone accepts
shorter input, allocating expected size and zero-filling the suffix; other
types require exact size. Oversized inputs are rejected before allocation in
these fresh-object cases. Rejections preserve source bytes and null output.
All200 match the independent reference, plus20 word-reader cases exact.
Added offline-only `camera_install/typed_record_reference.py` and four unit
tests for order, incomplete elements, expected-size behavior and rejected
unmapped inputs. Not used by production registration/export. This models
record copying, not source-span safety or carrier validity; zero-length input
is deliberately outside the reference's currently tested domain.

### Property metadata table and legacy-size copy controls (2026-10-08)

Private extractor now records all50 triples fromcf5e0 used by constructor
4dee0 (lookup masks property withffff7fff). This is a compiler record table,
not EDSDK registration metadata.1007 is type3/exact1460;1004 type4/exact300;
1005 type4/exact240.1002 is type2/max32;100a/100d/2001 type2/unbounded;
1022/102a/1f00/1f01/1f02 type4/unbounded;1070/1071 type3/unbounded.
These sizes/types alone do not reveal opaque semantics or generate missing
records. Extended native copy controls to the three legacy expected sizes,
with shorter/exact/longer inputs and four endian modes:236 total typed-copy
cases exact,20 word-reader cases exact. Legacy fixed sizes reject shorter
and longer inputs as expected. Only synthetic memory buffers were used;
no carrier import or camera access. Structured50-entry evidence in
`recordMetadataTable`, numerical evidence in the private typed-copy proof.

### Legacy carrier provenance re-audit (2026-10-08)

Read-only workspace scan found72 .bin files of oldest importer sizes8164/8168.
Every extracted1460-byte1007 region is entirely00 orFF. The alias-sweep
filenames explicitly identify SEED_00/SEED_FF controls; these are past synthetic
diagnostics, not genuine camera metadata despite directory names containing
OFFICIAL. No artifact in this size/content scan supplies a proven genuine
opaque record. Therefore importing them cannot settle the unresolved legacy
semantic question or justify compatibility claims. This inventory is limited
to .bin files under the current workspace, not all possible external archives.
Private `LEGACY_CARRIER_ORIGIN_AUDIT_20261008.json` retains path/hash/opaque
hash for each candidate; originals unchanged. Continue independent parser
and serialization work rather than promoting synthetic seeds to support data.

### Reusable reference checked against all native typed observations (2026-10-08)

New offline verifier compares the actual reusable copy_record function with
all236 retained native cases, not merely the inline probe expectations.
176 accepted outputs and60 rejected cases agree exactly; coverage has236
unique type/mode/expected-size/input-size tuples. Native evidence SHA256
135be936bf64f35ec1af04ec55a00f3ee272315b490b635133b0307bc3c4bca7;
reference SHA2564a1cca345024353fec3043ff0755fb67ef83c1c2bc3858e8d3924c2233a22e3d.
Private verification output stores both hashes and result counts. Added unit
checks for endian-swap involution on complete elements and legacy fixed-size
accept/reject behavior. Scope remains fresh typed records, not carrier parsing
or universal camera support. No native process needed for this replay check.

### Copy wrapper error meanings and exact lookup (2026-10-08)

Candidate4a2b0 is NOT a serializer: it calls46c10 to find an existing record,
then4a120 to copy. Hash-gated asserted instructions distinguish missing record
rc80, copy rejection rc100, accepted copy rc0.46c10 scans pointer entries and
compares the record property at+4 literally against the requested ID; no
masking/alias normalization appears in its complete body46c10..46c3c.
The constructor'sffff7fff mask and this lookup are distinct layers; applying
the constructor rule globally to lookup would be unjustified. This finding
does not redefine the cause of every observed legacy rc80: those require
their own caller traces. Serialization entry remains to locate. Production
unchanged; private typedCopyWrapper evidence added.

### Public Reflect serialization dispatch located (2026-10-08)

Editor serialization uses EdsCfpReflectProperty, not a separate Save export.
Static path: export3e70 calls13710; wrapper field+24 invokes virtual+c,
observed inner methodb0b0. It checks stream field+4 (absent returns22hex),
then content field+1c (absent returns0ahex), and invokes content virtual+28
with the stream pointer. Extended read-only owned-host observation confirms
third object slot+28 points to56ed0 (all12 sampled slots executable).
Thus the next serialization entry to map is56ed0, not nearby4a2b0.
No Reflect call was executed, so original PF3 remained read-only; this is
dispatch evidence, not byte-equivalence proof. Updated private object-method
JSON retains observed12-slot table. Host cleaned; no camera/EOS Utility access.

### Reflect sizing/writing/checksum mapped statically (2026-10-08)

Known-hash56ed0 invokes content slot20 (observed512a0) for property-stream
size and slot24 (observed51090) for writing. Both traverse existing record
pointers using shared predicate slot18 (observed56ea0). Included records add
8-byte header plus data length to sizing. Writer checks remaining space
against that same size, writes ID/type via520b0 and length with endian handling,
then copies data through46de0. Reflect sums serialized property bytes, builds
fffe checksum and ffff terminator, encrypts body with2db0 seed12, and writes
stream. Object state1 adds22e1 to checksum; its semantics still unproved.
Filter predicate and nested record-output copy remain next targets, as do
stream return/error propagation. No serialization executed this turn.
Private `REFLECT_SERIALIZATION_WINDOWS_20261008.json` retains exact bytes and
asserted call/checksum sites; dedicated extractor reproduces these checks.

### Serialization allowlist explains derived-record omission (2026-10-08)

56ea0 masks requested ID withffff7fff and checks31 IDs atbf118. This content
class retains source records including1018/1019,1021/1029,1070/1071, but excludes
1004/1005/1007,1022/102a,1f00/1f01/1f02. Therefore runtime materialization of
those derived nodes does not imply Reflect persistence; earlier seed omission
now has a concrete filter explanation. Do not apply this as a universal format
restriction: other content classes/routes may serialize differently.
Owned hidden-host object probe called ONLY this predicate for50 metadata IDs
and their8000-bit variants. All100 decisions match extracted allowlist exactly.
No Reflect, property mutation or carrier import executed; original source
remained read-only and host cleaned. Updated private object-method JSON has
filterRows; serialization-window JSON retains allowlist and assertions.

### Reflect stream return statuses are not propagated on normal tail (2026-10-08)

Hash-gated static assertions confirm stream virtual90 return is immediately
overwritten at570cd. After virtual8c write at570d9, the normal tail neither
branches on its result nor reads returned count; it frees buffers and sets
eax0 at570f7. Thus normal returned stream errors/short writes are not proven
by Reflect rc. Exceptions/callee side effects remain distinct and untested;
no fault injection or real-file write was performed.
Current production exporter already validates PSP header and exact434511-byte
length after releasing the reference (canon_engine.py export tail). The helper
checks only length>=12 and bytes4..6PSP, not complete record/checksum/content
equivalence. This identifies a future verification-strengthening opportunity,
not authorization to replace the validated serializer or modify production now.
Private streamStatusCaveat includes precise qualification and asserted sites.

### Output typed-copy asymmetry checked (2026-10-08)

46de0 is the output copy used by record serialization. Static path copies
raw1/2/ffff, complete16-bit type3 and32-bit type4 elements. Unlike input4a120,
it does not clear destination bytes. Owned-host synthetic probe now executes
output copies for176 accepted input cases, initializing destinations toA5.
All176 flags/bytes match independent reference: incomplete element suffixes
retainA5, rather than input copy's zero-fill.20 word and236 input-copy cases
also passed again. This does not prove uninitialized file bytes in actual
serialization: valid records may be aligned and caller allocation behavior
still needs tracing. No complete file serialization or camera access executed.
Private typed-copy proof now includes outputProof per accepted row; retained
evidence hash consequently changes from the earlier input-only replay.

### Reusable output reference validated (2026-10-08)

Added offline output_record to the typed reference, explicitly limited to
equal-length source/destination spans tested natively. It preserves existing
destination suffixes for incomplete elements and rejects unvalidated unequal
spans rather than guessing their behavior. The replay verifier now compares
all176 native output copies against this actual reusable function, along with
176 accepted inputs/60 rejections. All exact. Two additional unit tests cover
sentinel-tail preservation and unequal-span rejection;372 tests pass.
Reference SHA2562efc307251eddb8d45ed6b69d9942d5514a2f6635c39962dbf3d5313edb0833f;
native evidence31eac0cdc9cce5f436c3bff52b9ee3f4a1355be1654b68107352dd35d3a98fce.
No production serialization integration, fixture redistribution or camera access.

### Unequal output spans now tested and modeled (2026-10-08)

352 additional bounded native output requests (two per accepted typed input)
match independent expectations: shorter requests copy complete elements fitting
the request, leaving incomplete suffixes unchanged; longer requests reject
without writing for types1/3/4/ffff. Type2 instead clamps copied length to record
size and leaves destination remainder intact. Buffers were explicitly allocated
to each request length, so no out-of-bounds probes were needed.
Reusable output_record expanded only after these observations; verifier now
checks236 input cases,176 equal output copies and352 span cases exactly.
Empty requests remain outside tested reference domain.372 tests and syntax
checks pass. Native evidence464137e4a37d682d9b35e4f6f41070b39c48036a5d204b17f7a63dbddfc24076;
referenceb13ceb53ae96ae2ee222e6efca3d88ede6f411a16d3c0433608e582e328f47c1.
Own hidden host cleaned; no file serializer or camera calls executed.

### 16-bit header writer validated (2026-10-08)

Native520b0 writes low16 bits of its value argument and advances cursor2.
Twenty synthetic cases cover0/1/1234/ffff/12345678 and modes0/4949/4d4d/1.
All values/order/cursor match independent Python to_bytes exactly; two trailing
A5 sentinel bytes remain unchanged. This independently confirms the ID/type
header primitive used by51090, including truncation of a32-bit argument.
Prior20 word reads,236 input copies,176 equal output copies and352 unequal
span requests revalidated. Private typed-copy evidence now includes headerRows,
and replay verifier checks these20 too. No complete serializer execution,
original-file modification or camera access. Host cleaned.

### Complete single-record composition proved synthetically (2026-10-08)

511d0 composes ID/type/length/data and returns dataLength+8; insufficient
capacity returns-1. Owned-host probe added352 cases:176 exact-capacity writes
and176 capacity-short-by-one rejections. Header ID1234 is deliberately synthetic.
Every header/order/data/sentinel matches independent Python composition using
the reusable output reference. Short-capacity destinations remain entirelyA5;
successful writes preserve two trailing sentinels and incomplete element tails.
This validates single-record composition, not whole-file checksum/filter/order
or camera compatibility. All earlier primitive matrices revalidated; no PF3
file written. Private recordProofs retained and replay verifier checks all352.

Importer caller identified: internal setter51590 selects compiler
property0x01000203 (subtract0x01000001 then0x202) and calls52110 at51718.
This is the compiler's INPUT property, not a call to camera EDSDK and
does not authorize sending/importing captured carriers to a camera.
Export EdsCfpSetPropertyData delegates through object virtual slot0x1c.
Static aligned pointer search finds51590 in a data table, but inferred
eight-slot window includes non-executable data: NOT a proven vtable link.
Public reachability must still be checked through the real object
implementation/constructor or own-host read-only observation. Extractor
retains this rejected-vtable-candidate distinction, asserted property
gate and only one linear candidate direct caller. Syntax passes.

Legacy opaque importer attribution advanced: entry0x52110 calls family
classifier4eaf0, decrements class and dispatches ten slots at0x5320c.
Classes1/2 select0x5213b/0x5231b. Exact header gates respectively require
8164/8168 input bytes, firstword1 and secondword8124/8128. Their raw
1007 stores use matching0x4c/0x14c source offsets. Thus caller-provided
old carrier buffers are a concrete upstream source in this importer,
distinct from PF3 curve/LUT derivation. Classes6/7 share0x52faa; do not
infer their final behavior without tracing it. Private hash-gated
LEGACY_IMPORT_WINDOWS_20261008.json retains ten-way map and asserted
header gates. Public API reachability and genuine input provenance
remain unproved; no carrier reused or opaque metadata fabricated.

Legacy1007 raw-access join: verified every archived candidate-window
instruction byte against exact current compiler hash. Six sites are
NOT six getters: four call raw reader4ef20 and two call raw store51500.
All request1460bytes, buffer offset0x4c or0x14c; import/export windows
use matching offsets and OR status into aggregate. Thus these specific
store paths import opaque bytes from caller buffers, rather than deriving
1007 from the color tables. No inference that all1007 generation paths
are absent: function reachability and constructors remain open.
Private LEGACY_1007_READ_WINDOW_PROOF_20261008.json preserves source hash,
site RVAs, read/store distinction and exact sizes. Initial verifier's
all-read hypothesis correctly failed and was replaced by evidenced
read/store classification. No synthetic metadata seeded or camera write.

Restricted-combined-six pending native run now COMPLETED through the
same escalated approval path (not bypassed). Both sources/guards intact,
own hidden host cleaned up,217828-byte profiles. Independent full-chain
CLUT comparison exact for35,937nodes per selector. Separately the
geometry consumer reproduces all71,874 intermediate RGB outputs EXACTLY,
maxError0, so this is not only quantization hiding a discrepancy.
Capture6daff93114e83ae7eb2b65256aca9f9dd8e078497a2ec7fb0d58abe7d2ac10a6:
MODE_TWO_RESTRICTED_COMBINED_SIX_AXIS_GROUPS_OBSERVED_20261008.json.
Proofs MODE_TWO_RESTRICTED_COMBINED_SIX_AXIS_FULL_CHAIN_PROOF_20261008.json
and SIX_AXIS_GEOMETRY_restricted-combined-six_CONSUMER_PROOF_20261008.json.
This supersedes the native-pending item below, retaining its history.
364tests/py_compile pass. Domain remains one rotated geometry with
20..80 eligibility bounds, not arbitrary record layouts or cameras.

Restricted-combined-six control PREPARED, NOT NATIVE-VALIDATED:
same rotated/span20 geometry, saturation/lightness bounds20..80.
Exact agent guards and source verifier added. Native invocation did
NOT execute: automatic escalation review failed due account usage
limit, not a native DLL result or safety rejection. No host exists
for that rejected invocation; do not poll/restart a fictitious handle.
Node syntax/py_compile pass. Three pure-reference tests additionally
cover hue upper exclusion, closed saturation/lightness endpoints and
outside bypass;364tests pass. These tests support reference semantics
and static gates, NOT equivalence to unperformed restricted native run.
Next retry original approved-path invocation when review is available;
continue read-only/static or independent math branches meanwhile.

Noncanonical six-axis geometry full-chain control now verified:
centres15+60*i degrees, spans+/-20 degrees (gaps between sectors),
width20, first sector deltas(10,-10,5), others neutral. Exact per-word
native-agent guard before own-host execution. Both CLUTs match every
35,937node independently, zero differing bytes; source/guards unchanged.
Tracea19221e100ed37b2dee4bf794d29666d3921b0eefa34171ae37adbfa2fee0175,
MODE_TWO_ROTATED_COMBINED_SIX_AXIS_GROUPS_OBSERVED_20261008.json.
Proof MODE_TWO_ROTATED_COMBINED_SIX_AXIS_FULL_CHAIN_PROOF_20261008.json.
Full-chain verifier now uses neighbor-aware geometry reference also for
canonical six controls, replacing the reduced weight approximation.
This validates one noncanonical rotation/span, not arbitrary sector
records or camera compatibility.361tests and syntax checks pass.

Six-axis intermediate residual RESOLVED for captured canonical hue10:
existing neighbor-aware legacy_axis_geometry_reference.helper reproduces
all72 selected group outputs exactly. Its full transform, with explicit
fixed-point overshoot opt-in, then reproduces EVERY consumer RGB output
for both selectors:35,937/35,937 each, maxError0. No captured helper
outputs used as oracle in this full comparison; only original source
block and consumer input RGB. Proof SIX_AXIS_GEOMETRY_CONSUMER_PROOF_20261008.json,
capture7f4d303885d816e404a45c14b854d7667bdd72c37a2a77e575d96b77b17aea05.
Earlier13/9 residual arose in reduced direct-weight representation,
not unavoidable native floating-point opacity. Added exact numeric
wrap regression plus explicit overshoot test;361tests/py_compile pass.
Still canonical geometry and hue-only: arbitrary variable geometry,
full independent ICC construction and camera universality remain open.

Full kind1+kind2 composition captured and independently reproduced:
mixed matrix, post-red-mid96 curve, two combined-four records split
prefix1, plus intermediate global(10,10,5). Each selector executes
107,811 selective/axis consumer calls; both CLUTs match all35,937nodes
exactly, zero differing bytes. Trace SHA256
e274b1fd8edb76e85b1a306a6f63c26330e6966297626c550095cbb5b55cf448.
Private MODE_TWO_COMBINED_GLOBAL_AXIS_GROUPS_combined-four_PREFIX1_RECORDS2_mixed_post-red-mid96_CH0_OBSERVED_20261008.json.
Agent retains exact known geometry/delta guards; simultaneous six-axis
and kind1 remains excluded. Earlier pre-completion read saw incomplete
JSON; process was still live, polled same handle to completion (not
restarted), then verification succeeded. Driver now publishes reports
atomically via same-directory .pending replacement. Own host cleaned
up and sources intact.359tests pass; syntax checked.

Previously missing split-combined control now captured and verified:
two identical kind1 four-point(hue10,saturation-10,luminance5) records,
prefix1, so one initial and one later consumer. Identity controls:
0c6c3e00967e03269e4c36448ea165945c430535c18eb7c9da6b27b8c449fb05;
mixed matrix plus post-red-mid96 curve:
a02dabcda1a239e24abf4db6f2bf25b2457d3704fe51c7c419df45022e7ba5d3.
Each native selector executes71,874 selective calls; both217828-byte
profiles have unchanged sources. Both independent full chains match
all35,937 CLUT nodes per selector, zero differing bytes. Qualified
filenames retain the earlier identity fixture. Private *_PREFIX1_TWO_RECORDS*
captures/proofs retain parameters and source-validation evidence.
This resolves the specifically missing combination, not arbitrary
record types or simultaneous kind1/kind2 controls.359tests pass.

Evidence-integrity follow-up: verifier now validates exact global/six-axis
record geometry, deltas and unused padding, plus selective record count,
prefix, point records and source length. Unsupported simultaneous axis
and selective captures are rejected before comparison. Null results are
handled before source-integrity fields. Strengthened reruns pass for
mixed/post-curve combined-global, two hue records split prefix1, and
nonneutral hue-six (quantized equality only);359tests pass.
An attempted combined-four/prefix1/two-record run found NO capture;
it correctly failed with missing fixture, so no evidence is claimed
for that combination. Do not infer it from the existing hue-only split.

Cross-stage control: mixed polynomial(.75 current+.125 next channel),
post-polynomial red mid-point128->96 curve and global(10,10,5) axes
together reproduce both CLUTs exactly,71,874nodes, zero differing bytes.
Private trace9a1c6bce3e9f5b386a9681b781a41acc0df3899550ce4ec63baa375d8be789a2:
MODE_TWO_COMBINED_GLOBAL_AXIS_GROUPS_mixed_post-red-mid96_CH0_OBSERVED_20261008.json.
Own host cleaned up; source unchanged. Filename qualifiers preserve
earlier isolated captures instead of overwriting them. Verifier now
checks source mode/selector, all polynomial rows and all nine curve
buffers against requested control before accepting output comparison.
Strengthened verifier rerun passes;359tests and py_compile pass.
This supplies nonidentity compositional evidence, not arbitrary profiles.

Reference consolidation: legacy_axis_reference.transform now exposes
explicit allow_fixed_point_overshoot (default remains strict), matching
the mode2 internal endpoint evidence without loosening normal callers.
RGB checked before coordinate math. Private mode2 verifier now calls
this existing shared research reference instead of duplicating global
formula. Combined-global full CLUT rerun remains byte-exact for both
selectors. Three new tests cover overshoot opt-in/bound, malformed RGB
and combined controls' original-coordinate dependence.359tests pass;
py_compile passes. Research module only, not app preview/export changes.

Global kind2 luminance5 and combined(hue10,saturation10,luminance5)
each independently match both full CLUTs,35,937nodes per selector,
zero differing bytes (143,748 additional node comparisons). Luminance
normalized0.05 scales by original cone saturation before compose;
combined positive saturation also scales by that original coordinate,
not by the already saturation-adjusted result. Captures:
625fa25ccc0d628e3b858e0c170973dd00d90f420772ab74fe04dbecdff1fe78
MODE_TWO_LUMINANCE_GLOBAL_AXIS_GROUPS_OBSERVED_20261008.json;
77d48f4d37601ca269c2891300b5ef1f872e95bc00d2e80ae1400f1e6f128aed
MODE_TWO_COMBINED_GLOBAL_AXIS_GROUPS_OBSERVED_20261008.json.
Corresponding *_FULL_CHAIN_PROOF_20261008.json files preserve exact
CLUT comparison results. Both own hosts cleaned up; source/guards
unchanged. Global identity curves/matrix only, not variable geometry,
all control amplitudes or arbitrary PF3/camera support.

Positive global saturation10 independently matches both complete CLUTs:
35,937 nodes each, zero differing bytes. Known176-byte kind2 geometry,
only word38=10, source/guards unchanged in own hidden hash-gated host.
Reference scales normalized adjustment0.1 by existing cone saturation
before compose's positive-only gain5 and gamut compression; negative
control remains unscaled before gain. Capture SHA256
5fa564c2543a02d9baa6d4d5f8a07ae284c41c0c67264306aa1d1e4beb1ad20f,
MODE_TWO_POSITIVE_SATURATION_GLOBAL_AXIS_GROUPS_OBSERVED_20261008.json.
Proof MODE_TWO_POSITIVE_SATURATION_GLOBAL_AXIS_FULL_CHAIN_PROOF_20261008.json.
This verifies two global saturation signs, not all amplitudes/sectors.
Next extend luminance, then combined controls/eligibility geometry.

Global kind2 saturation control independently verified: known176-byte
geometry, only word38=-10 (hue/luminance neutral). Own hidden x86 host,
hash-verified DLLs, original inputs/guards unchanged. Both217828-byte
profiles produced. Full lattice chain with compose saturation_adjustment
of-0.1 matches all35,937 CLUT nodes per selector, zero differing bytes.
Capture b0ccd6b582149ae5125020bfcf29de32e482d82e4b932edbc8b5a88f0ce37be8:
MODE_TWO_SATURATION_GLOBAL_AXIS_GROUPS_OBSERVED_20261008.json.
Proof MODE_TWO_SATURATION_GLOBAL_AXIS_FULL_CHAIN_PROOF_20261008.json.
This is negative global saturation only: positive gain, selective
eligibility and nonuniform sector saturation are not proven by it.
No production changes, camera sessions or EOS Utility access.

Static helper gate expansion: unchanged-input early return0x11215 occurs
outside hue[lower,upper), lightness closed bounds or saturation closed
bounds (branches0x10f27/37/47/57/67/7b now asserted by extractor).
Transition width is restricted not merely to the current sector's
half-span:0x10ff9/0x10ffd combine neighboring half-spans and0x11006/0x1100b
apply configured width. Thus variable geometry needs neighbor-aware
limits; uniform60-degree sector assumptions cannot be generalized.
Saved as neighborGates in private AXIS_CONSUMER_STATIC_20261008.json.
Static checks and syntax pass; no independent variable-geometry numerical
claim yet. Remaining hue residual is retained rather than silently fitted.

Group-output caller replay now exact for all12 selected nodes (six per
selector), using all six captured group outputs, sequential delta
accumulation and independent cone reconstruction. Proof:
AXIS_GROUP_ACCUMULATION_PROOF_20261008.json. This locates the residual
upstream of final RGB reconstruction, within independent reproduction
of the helper's absolute hue, not a demonstrated caller/compose error.
Do NOT call this independent end-to-end equivalence: helper outputs
remain an oracle. A naive absolute-hue weighted blend was also tested
over all nodes and worsened exact counts to34,908/34,924; rejected.
Next inspect helper branch-local hue offsets before each weighted
blend, instead of fitting one global wrapping rule.

Own hidden x86 host group capture completed,2026-10-08. Six selected
nodes per selector, six group calls per node, original inputs unchanged;
each builder returned217828bytes. Private capture SHA256
6d347b3f58fa178304ca1e40510ad4926d3a98078e2f37261e3680e7db6f0980,
MODE_TWO_HUE_SIX_AXIS_GROUPS_OBSERVED_20261008.json. Prior captures retained.
Important distinction:0x10a00 returns absolute adjusted hue, NOT merely
a weighted hue delta. For selector1 node9838, first group returns
5.745615479124144; five remaining neutral groups return5.6250001490116475.
Caller0xfbc4 subtracts its baseline before accumulating. Thus independent
direct h+weightedDelta omits the rounded(absoluteHue-baseline)+baseline
sequence. Next replay this exact caller accumulation using captured group
outputs, then independently reproduce those outputs. This is internal
evidence, not yet an independent mathematical equivalence claim.
Own process exited/cleanup completed; no camera/EOS Utility access.

Wrap-first hypothesis tested against all captured hue-six inputs:
for h>=5.5, evaluating(h-6)+delta then wrapping back reduces maximum
error to3.34e-16 but worsens exact counts to35,046/35,259 (versus
35,924/35,928 for ordinary pre-divide). Therefore do not adopt this
global wrap-first rule: a smaller error bound is not stronger exactness.
Private attribution now records all18 weight/order combinations.
Pending: observe individual0x10a00 group outputs in the isolated host,
particularly the22 previously residual calls, to distinguish group
delta subtraction/accumulation from final cone reconstruction. Existing
whole-CLUT byte equality remains a separate, narrower proven result.

Rejected residual hypothesis,2026-10-08: helper0x11039 subtracts0.5,
0x11048 adds0.5 back before using the linear interpolation component.
Replaying that centered/recovered t operation in the private attribution
does NOT change the exact-output counts (35,924/35,928 pre-divide).
Thus that operation alone does not explain the13/9 consumer residuals.
The examples concentrate in the red/magenta wrap transition; next useful
test is native per-group hue wrapping/accumulation versus a single h+delta.
No tolerance accepted as exactness and no runtime formula changed.

Neighbor-helper normalization established statically for this exact revision:
0x10a00 loads60.0 from0x31088 and100.0 from0x31090. Record integer
components are converted to doubles and divided before the later weight
multiplications (e.g.0x10a81 hue,0x10a95/0x10aa7 other components;
type3 hue at0x10b19). The bounded helper extraction reaches its return
and retains all instructions plus referenced doubles. Other constants:
6,0.5,2,4,1,-12, consistent with the preceding wrap/logistic hypothesis.
This supports pre-normalizing components rather than multiplying the
integer hue by a weight then dividing. It does not resolve the13/9
remaining intermediate residuals: branch-specific accumulation and
transition evaluation still need independent replay. No production edit.

Static follow-up: extract_axis_consumer.py reads but never loads the
hash-verified MLib revision a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a.
Private AXIS_CONSUMER_STATIC_20261008.json retains the bounded window.
At0xfb4a kind2 selects the neighboring-record route;0xfbb6 calls0x10a00
with current/adjacent record pointers. The consumer accumulates returned
components at0xfbc4..0xfbe2 before final reconstruction at0xff01.
This identifies0x10a00, rather than just final compose, as the next
normalization/transition candidate. The linear window does not yet prove
its complete control flow or coefficient arithmetic. Syntax verified;
no installed DLL modification, execution, camera or EOS Utility access.

2026-10-08 follow-up verification (offline; no native process or camera):
Neutral six-axis full lattice-to-CLUT comparison now passes both selectors,
35,937 nodes each, zero differing bytes. Private proof:
MODE_TWO_NEUTRAL_SIX_AXIS_FULL_CHAIN_PROOF_20261008.json, using capture
c5a57d882499a34896ab6850ba248dd30072c1bc903d2dfb3414d98fbb16b58e.
This supersedes the earlier neutral full-chain pending item below.

Arithmetic attribution against the captured hue-six consumer inputs:
preceding weights with pre-divided hue increment w*(10/60) reproduce
35,924/35,928 outputs exactly; multiply-then-divide reproduces
35,809/35,841. Residuals remain <=6.67e-16. Modern weights retain substantive
errors up to3.87e-5/6.44e-5 regardless of that arithmetic order.
Private attribution: MODE_TWO_SIX_AXIS_ARITHMETIC_ATTRIBUTION_20261008.json.
This narrows the hypothesis, but does NOT establish native coefficient
scaling order or bit-exact consumer equivalence. No production formula
changed. Both private scripts pass py_compile; all356 tests pass.
Next: inspect native coefficient normalization/order to explain the
remaining13/9 outputs before extending nonneutral saturation/luminance.

Nonneutral six-axis CLUT residual resolved by preceding-sector weights:
legacy_six_axis_reference.sector_weights preserves wrap coordinate and
native weighting multiplication/division order instead of modern default
weights. With hue increment weight*10/60, full lattice chain matches both
CLUTs byte-for-byte against7f4d303885d816e404a45c14b854d7667bdd72c37a2a77e575d96b77b17aea05.
Important precision distinction: consumer RGB outputs are exact for
35,809/35,841 of35,937 calls; remaining errors <=7.78e-16/6.67e-16.
Thus final quantized table equivalence is proven for this control, not
bit-identical intermediate doubles. Retain that residual for future
stronger controls instead of globally claiming exact axis arithmetic.

Nonneutral six-axis control: same canonical512-byte geometry, only first
sector hue delta10. Native returns valid ICC for both selectors, sources
unchanged. Independent default-axis whole-chain hypothesis is NOT exact:
selector1 differs2 bytes/2 nodes; selector2 differs84 bytes/63 nodes.
Capture7f4d303885d816e404a45c14b854d7667bdd72c37a2a77e575d96b77b17aea05.
Verifier deliberately fails;356 general tests pass independently. Neutral
equivalence must not be extrapolated to sector transitions. Next compare
captured consumer outputs with preceding-sector arithmetic (wrap/weight
order differs from modern default reference) before changing any formula.

Neutral six-axis kind2: canonical512-byte block at0x480, six sectors
centres0/60/120/180/240/300, widths20, all delta triplets0. Strict
per-word agent validation before native call; source/guards unchanged.
Both selectors execute35,937 companion calls; independent default-axis
reference with fixed-point overshoot enabled reproduces EVERY captured
output exactly, maxError0. Capture SHA256
c5a57d882499a34896ab6850ba248dd30072c1bc903d2dfb3414d98fbb16b58e.
This is neutral geometry/consumer-output evidence only; nonneutral sector
transitions and independent full-chain six-axis proof remain open.
Scripts compile and356 general tests pass.

Nonneutral kind2 global hue10 control: known176-byte geometry, changed
only word37 at0x480+148. Complete independent chain, including cone
reconstruction in its selector-dependent position, matches both CLUTs
byte-for-byte (71,874 nodes). Capture SHA256
8109969498e4c9d89ceab2a11e03d340f390d74cde77b1d8789406c7936077e1.
Source/guards unchanged, syntax and356 tests pass. This confirms one
nonneutral global-axis control; six-group geometry remains separate.

Neutral kind2 resolved independently: composition with cone_hue and
zero deltas, explicit fixed-point overshoot allowance (input reaches
1+1/2^24), reproduces all71,874 captured fa40 outputs exactly. Whole
independent lattice chain places this operation between fixed round trips
for selector1, after postcurves for selector2; both CLUTs now match every
byte. The53-byte deviation from no-axis baseline is fully accounted for,
not ignored. Capture6c589b0c14252635d75afdc7dca83617348ed8ae2b1a3ffadd1c6edebf46c9f4.
Only neutral known global geometry proved; nonzero kind2/six-axis open.
Syntax validated and356 tests pass; camera/runtime code unchanged.

Companion kind2 first native control: exact known two-group global axis
block176 bytes at0x480, all deltas0, empty kind1 records. Each selector
executes35,937 fa40 calls, caller88bb for selector1 (between fixed round
trips), caller89d3 for selector2 (no fixed round trips). Even neutral
axes reconstruct RGB:16,500/16,070 output triples differ in floating bits.
Selector1 CLUT differs by53 bytes from no-axis baseline, selector2 by0.
Do not algebraically remove this neutral transform: later integer
quantization can expose reconstruction differences. Capture
6c589b0c14252635d75afdc7dca83617348ed8ae2b1a3ffadd1c6edebf46c9f4.
Source/guards unchanged; syntax and356 tests pass. Next compare kind2
math independently and include its exact stage placement in whole chain.

Combined four-point control deltaH10,deltaS-10,deltaL5,prefix0,total1:
complete independent chain matches both CLUTs byte-for-byte (71,874
nodes). Captureca528465f534f3aedec2ee75bdd8f582952cd2928518439bd408ddcedc9ae902.
This verifies joint composition for this bounded triplet, not arbitrary
strengths or full gamut coverage. Source/guards unchanged, syntax and
356 tests pass. Companion kind2 remains a distinct unvalidated mode2
branch; do not infer its equivalence from these kind1 controls.

Luminance selective control: identical four-point geometry with deltaH/S0,
deltaL5,prefix0,total1. Complete independent lattice chain reproduces both
CLUTs exactly (71,874 nodes), including the translated composition/gamut
handling already present in legacy_sector_reference. Capture SHA256
41e06730cf42e38b2bfcd0418b74c28b2c85ef6a3ea793b903d935d670e29f4d.
Inputs/guards unchanged, scripts compile,356 general tests pass. Three
components now have separate bounded controls; stronger gamut and mixed
ordered adjustments still require evidence, not universal extrapolation.

Saturation selective control: same four-point selector geometry, deltaH0,
deltaS-10,deltaL0, prefix0,total1. Each selector executes35,937 calls;
full independent lattice-to-CLUT chain matches all71,874 nodes exactly.
Source/guards unchanged; capture
02a702df217adeb8a06d98f18bba5e73f8c064d1d54367727e974e050a641668.
This extends exact equivalence beyond hue to one bounded desaturation
control, not arbitrary saturation/gamut limits. Syntax and356 tests pass.

Two-record split validated: total2,prefix1, two identical full-capacity
kind1 hue10 controls. Each selector executes35,937 calls at initial84ec
and35,937 at later89ec; source/guards unchanged. Full independent lattice
chain with one adjustment in each stage matches both CLUTs byte-for-byte.
Capture674e25022af8612cfa0132001a7db8d5c3423380a986977ff9ce585db2e9a139.
This proves bounded two-record split/placement/output, not partial-capacity
records or arbitrary multi-group order. Syntax checked;356 tests pass.

Early selective full-chain proof: prefix1 hue10 is independently applied
after polynomial and before second cached curve group, then established
fixed-roundtrip/color chain. Both selectors match all35,937 CLUT nodes
byte-for-byte against68ecde5efca1ea02c9b526020a8acf2aa27ac151b8b66b340efa81c6ac5756d0.
No captured RGB boundary values used. Prefix0 later-stage regression is
rerun separately; early/later differences are now explained by verified
stage order for this bounded control. Two-record split remains unproved.

One-record prefix1 follow-up moves every fa40 call from later0x89ec to
initial0x84ec (35,937 each selector). Thus prefix0 and prefix=total1,
although both allocation paths are unsplit, route the record to different
consumer stages. Selector1 ICC changes; selector2 ICC remains identical
for this identity-curve/matrix control (not a general order equivalence).
Capture68ecde5efca1ea02c9b526020a8acf2aa27ac151b8b66b340efa81c6ac5756d0.
Bounded placement verifier retains both traces and source guards.
Next validate two-record split and full independent early-stage chain.

2026-10-08 full selective chain: independent lattice -> cached curves ->
identity polynomial -> two fixed round trips where applicable -> later
hue10 four-point selective group -> clamp -> floating color/Lab16 matches
all71,874 CLUT nodes byte-for-byte. No captured intermediate INPUT is
used to construct expected values in this proof. Source native trace
f11fb56bcc99ab995afda3ff231fa6b2308fb95f5ea235a51defd04d09db179f,
private MODE_TWO_SELECTIVE_FULL_CHAIN_PROOF_20261008.json. This closes
the whole-chain gap for this one unsplit kind1 control, not other deltas,
record splitting, companion kind2 or all cameras.

2026-10-08: bounded legacy_sector_reference reproduces every fa40
output exactly for hue10 control (35,937 calls each selector, maxError0).
Using independent selective output, clamp and floating color/Lab16 also
reproduces both complete CLUTs byte-for-byte. Private verifier
verify_mode_two_selective.py retains trace hash and coverage checks.
Captured INPUTS are still the boundary: preceding whole-chain equivalence
is not claimed by this proof. This establishes shared selective arithmetic
for this four-point control, not all record kinds/deltas. Syntax checked,
356 general tests pass; native/camera application path unchanged.

Nonzero selective hue control (deltaH10, deltaS/L0; otherwise exact
neutral four-point layout) confirms 35,937 fa40 calls per selector,
all returning to0x89ec: unsplit prefix0 places this record in the LATER
selective set. RGB changes in35,746/35,185 calls respectively; CLUT
differs from empty baseline at171,303/174,086 bytes. This is measured
activation/effect, not independent mathematical equivalence. Source
guards unchanged, capture SHA256
f11fb56bcc99ab995afda3ff231fa6b2308fb95f5ea235a51defd04d09db179f.
Next compare fa40 output against bounded legacy selective reference and
validate prefix/split placement. Scripts compile;356 tests pass.

First native nonempty selective control: mode2 unsplit prefix0,total1,
kind1,width4; exact full-capacity four-point record centre(180,50,50),
low(0,0,0),high(360,100,100),delta(0,0,0). Source length0xf54,
strict agent checks every record word before native call. Both selectors
return valid ICC, unchanged source/guards, and CLUT is byte-identical to
empty-record baseline. Capture SHA256
b487d26bfbe3baf379386f76274482eb632bf5d2d3ebb5a91e064a1863243d01.
This establishes bounded neutral-record acceptance, NOT nonzero-delta
behavior or successful consumer activation; next capture fa40 call sites
and apply one bounded nonzero adjustment. 356 general tests pass.

Static selective consumer order is now explicit in research-only
mode_two_consumer_plan: kind1 first-set before second curves; kind2
companion between the two fixed round trips for selectors other than2;
kind1 second-set afterward; then clamp/floating color. Selector2 skips
both fixed round trips but retains the companion kind2 gate. 625
selector/kind combinations and strict word rejection are automated in
two new tests (356 total pass). This is NOT validation of record bodies,
allocation geometry or camera transport, and is not used by installation.

Third-group channels1 and2 isolated mid96 controls leave full CLUT and
all 768 output-curve entries unchanged for both selectors. Channel1 trace
eac54893ae51bd7516a335c33feb2b4189c7dccd2d5fc6ba619c873f4c560a50;
channel2 trace 105d9de881a40b84bfe4df4e6985cf3a1eb2a8cc61d229848d784c71c658296e.
The channel0 effect is therefore not evidence that all three group3
curves are applied to RGB. These are bounded mode2 ICC observations,
not a global claim that corresponding PF3 properties are irrelevant.
All source/guard buffers remained unchanged; scripts compile and 354
general tests pass. Next inspect selective records and their kind gates.

Third curve group channel0 at0x25c, bounded mid96 control: CLUT unchanged
for both selectors; 254/256 entries of first ICC output curve change.
Independent BSpline/finalization/cache sampling produces exact 768-entry
output curves (first nonlinear, other two identity). Capture SHA256
d7c97daf70018eea3c629e43a014c1fde1c46b6d5d9b4ad7da0223a0b96cff1c.
This separates third-group output-Lab curve from group2 post-RGB curve;
channel1/2 semantics still need independent controls. No camera evidence
or whole-ICC padding equivalence claimed.

Second group red nonlinear curve at0x130, same three-point mid96 control:
exact full CLUT for both selectors with identity matrix (capture
ba3d9802450c75432737e91feb9aaedfceb01b2c4ba097c66edd64f00d5520bb).
Identity matrix alone cannot distinguish placement, so repeated with
cyclic mixed matrix: also exact for both selectors, capture
1411a4ff3fb0d3615c7b357efb99a4c586858b5b14ff559926ae06c78350744c.
Reference places group1 before polynomial and group2 afterward; these
bounded controls agree at all 143,748 nodes across four CLUTs. Third
group and selective records remain independent open branches.

Nonlinear input curve: first group red channel at offset4 changed only
to three points (0,0),(128,96),(255,255), identity polynomial/other curves,
empty selective records. Independent quadratic BSpline/finalization and
cached interpolation plus the established downstream chain match every
CLUT byte for both selectors, 71,874 nodes. Capture SHA256:
773ea5e086440fdc1f172b68a2f38b5cf91eaadd4ec55c05017df28394f62a01.
Source and guards unchanged. This validates one bounded nonlinear curve,
not all point counts, third curve group or selective record layouts.

Mixed-matrix residual resolved without tolerance changes: evaluate the
256-point identity cache before polynomial and again afterward, rather
than algebraically removing identity curves. Static 0x851e..0x85a1
performs weighted interpolation of adjacent cached samples; floating
rounding can lower a subsequent 24-bit truncation by one. Reusing the
independent cached_curve_reference yields exact CLUT bytes for both
selectors with the cyclic mixed matrix (71,874 nodes), against trace
0fe981f714a62f78436259e7414645d0f8d68c3b63943734e47cec0332c031e9.
The original identity control is rerun as a separate regression. This
does not validate arbitrary polynomial coefficients or selective records.

Mixed-matrix attribution: all captured first-round forward/inverse
helpers again match independent integers (35,937 each). However, the
first forward INPUT differs from ideal linear matrix *2^24 at 2,032 nodes,
typically one integer lower; node1 expected [0,65536,393216], native
[0,65536,393215]. Therefore investigate curve/interpolation arithmetic
between polynomial and first quantization rather than changing Lab
formulas or rounding to force the 18-node final residual away.

Nonidentity extension: synthetic cyclic matrix output[c]=0.75*input[c]
+0.125*input[(c+1)%3], exactly representable signed16.16 coefficients.
Native control completed for both selectors with unchanged source/guards.
Selector2 remains byte-exact over 35,937 nodes; selector1 differs at 18
nodes/19 bytes. The verifier remains failing and does not relax tolerance.
Trace SHA256 0fe981f714a62f78436259e7414645d0f8d68c3b63943734e47cec0332c031e9.
Next attribute this new residual using existing per-helper captures,
including second-round helper callers; identity equivalence alone must
not be generalized to nonidentity transforms.

Resolution for the bounded identity/empty-record control: static calls
0x8921/0x894f perform a SECOND 24-bit round trip (helper modes 11 then
10), followed by RGB clamp to [0,1] before floating color conversion.
Both fixed helpers still select numeric mode 2 for these arguments.
The first inverse may produce 16,777,217, one above 2^24; the private
second-stage formula supports this internal endpoint without widening
the public reference's validated input contract. With both round trips
and clamp, independent construction matches ALL 35,937 nodes for each
selector, zero differing bytes, against original uninstrumented trace
a2422c3d26aba19c9a2b4ace6afb87422b3936c9e9335d72fb21fe9314a30f1b.
This proves the identity curves/polynomial, empty-record control only.
Nonidentity curves, polynomial and selective records remain to validate.

Further isolated capture of 0xf070 (return 0x8806) and 0xee40 (return
0x8834) provides 35,937 forward and 35,937 inverse calls. Independent
fixed-point references match every output integer using captured inputs.
Forward inputs also match identity lattice RGB times 2^24 exactly.
However, inverse output divided by 2^24 differs from final pre-color RGB
at 29,292 nodes: the remaining change is AFTER the fixed round trip.
Trace SHA256 a7b955d1397bce8c7f05182217fede385b31467e71b7e86d546c050cb0edcf6a.
Selector 2 makes zero calls to these two caller-scoped helpers. This rules
out their integer quantization as the source of the current residual;
next inspect intervening post-curve processing and its arithmetic.

Follow-up isolated native observer at RGB/XYZ entry 0x1000, restricted to
return address 0x8a6b, captured all 35,937 pre-color RGB values per selector.
Independent floating RGB/XYZ -> Lab -> Lab16 matches every CLUT byte for
both selectors (71,874 nodes total). Trace SHA256:
bc67d2ecac72191c0b681d446926c6af2b10e40af5743d665848657a819c2369.
This localizes the remaining selector-1 identity-reference differences
before the final floating color conversion, not its Lab16 writer. It does
not prove the preceding fixed-point round trip. Input buffers/guards were
unchanged; only our hidden host was instrumented and terminated afterward.
Private scripts passed py_compile and the 354-test suite remains green.

Read-only static inspection of SHA-verified MLib identifies constants at
0x30fc0=2 and 0x31058=24. Calls at 0x8801/0x882f perform a
24-bit RGB/Lab/RGB round trip. Helpers 0xf070 and 0xee40 reduce their
mode argument to 1 only for argument 1, otherwise 2; arguments 10 and
11 here therefore do not select floating-point matrix modes 10/11.

Adding this stage to the private identity-control verifier reduces
selector-1 disagreement from 625 bytes/619 nodes to 323 bytes/322 nodes
out of 35,937 nodes. Selector 2 remains exact. This is partial attribution,
not equivalence: the verifier deliberately still fails. Next isolate native
pre-color RGB and fixed-helper intermediates, especially rounding/order.
No application, camera path or installed DLL changed.

## Getter error-gate revalidation (2026-10-08)

After the inventory harness refactor, reran the owned-hidden-host
`checksum_state_probe.py`: all 18 bounded property reads passed again.
Invalid checksum vectors still produce content state -1 and data rc=0x2D;
the three destinations are zeroed, with both trailing sentinels preserved.
This is an error-path buffer observation, not a valid black transform.
Original input hash was preserved; the host was detached and terminated.

Two additional synthetic wrapper tests prove that a size-query rc=0x50
prevents any data read, and that rc=0x2D rejects nonzero partial data too.
Thus rejection relies on return codes, not an all-zero heuristic.
py_compile passed and the full suite passed 382 tests. No production
implementation or camera transport was changed. State-1 serialization
origin and selector-1 fixed-point differences remain unresolved.

Static constructor attribution now narrows the state question:
`find_content_constructors.py` hash-checks the DLL and finds four executable
vtable references, then verifies bounded instruction-aligned methods.
PF2 constructor 0x53290 writes content state +0x10=0 at 0x532b0.
PF3 constructor 0x53f70 calls that PF2 constructor at 0x53f82 and replaces
the vtable at 0x53f8c. Neither bounded constructor initializes state 1.
The other references are destructor vtable resets, not state setters.
Private evidence: `CONTENT_CONSTRUCTOR_CANDIDATES_20261008.json`.
This excludes constructor initialization as the source of the 0x22e1
state-1 checksum branch; later transitions still require attribution.
No native execution was used for this result. py_compile passed.

The PF3 constructor entry is precisely 0x53f70 (0x53f60 is the previous
method's return followed by padding). Constructor evidence was regenerated
from the correct entry, with assertions at the shared call and vtable store.
The shared base constructor 0x4de20 initializes +4 from its argument, +8=0,
and +0xc=0x1000; PF2 then writes +0xc from its second argument and +0x10=0.

`find_state_one_stores.py` extends the earlier bounded scan across the
executable section 0x1000..0xb6400 and includes byte/word stores: 713
candidate memory writes at displacement +0x10. Immediate-one examples at
0x11839/0x292af target stack temporaries (ecx=esp), not content objects.
Candidates at 0x18867 and 0x86c03/0x86d1d need separate receiver attribution;
they are not evidence of a PF3 state transition. Linear scanning includes
embedded-data false positives and does not cover pointer aliases or block
copies. No claim that state 1 is unreachable follows from this scan.
Private output: `STATE_ONE_STORE_CANDIDATES_20261008.json`.

Receiver attribution now excludes the three remaining immediate-one
candidates from being direct evidence of a content-state transition.
At 0x18790, esi is the caller's output argument, cleared for 0x20c bytes;
+8 is a count and +0xc holds indexed values, so the write at +0x10 is
the second array element. At 0x86bd4 and 0x86cec, +8 is a narrow/wide
character input pointer and the methods inspect NUL/format tokens.
Assertions on input-pointer loads, output clearing and indexed writes
passed in the hash-gated static extractor. These are distinct structures,
not PF2/PF3 content objects. Alias writes and block-copy paths remain open;
this does not prove the state-1 checksum branch is dead. py_compile passed.

Address-taking extension found 92 `lea ... [base+0x10]` candidates over
the executable section. The two in 0x4de00..0x57400 are at 0x4efc5 and
0x536ea, both `[ebp+0x10]` stack arguments supplied to property lookup,
not pointers to the content state. Pointer arithmetic/block copies remain
outside this negative result's scope.

Read-only public getters were then tested for the three low IDs and their
0x8000-bank counterparts on both hash-verified Emerald references.
PF2 low 0x1010/0x1023/0x102b return identical eight zero bytes; PF3 low
0x1010 fails size lookup rc=0x50 while 0x1023/0x102b return [1,0].
All six high-bank lookups (0x9010/0x9023/0x902b across the two files)
fail size lookup rc=0x50 and do not call the data getter.
Thus serialization-filter masking with 0xffff7fff must not be promoted
to a universal public-getter alias rule. These observations concern
these references; they do not prove high-bank properties are always absent.
Private CONTENT_CLASS_PF2/EMERALD_20261008.json inventories regenerated.
Both owned hidden hosts were released/detached/terminated; no setters,
Reflect, compiler calls or camera access were used.

Present-bank follow-up distinguishes lookup absence from alias behavior:
public getters successfully read 0x1002/0x9002, 0x1009/0x9009 and
0x1031/0x9031 from original Emerald PF3. `verify_bank_getters.py` compares
all six outputs against the exact original record IDs, reversing each
typed 16/32-bit element from file big endian to getter little endian;
raw type-2 metadata remains byte-for-byte unchanged. All six comparisons
pass. In particular 0x1002 and 0x9002 differ and each getter preserves its
own bank; collapsing IDs would silently discard real metadata here.
Equal values in the other sampled banks do not imply aliasing.
Private evidence: `BANK_GETTER_EQUIVALENCE_20261008.json`; the inventory
now includes twelve properties. One owned hidden host used read-only
getters and was cleaned up. py_compile passed; no production changes.

Three fixture-free regression tests now cover the inventory consequence:
different metadata banks retain IDs/data/order in either order; repeated
exact IDs remain separate records instead of being silently overwritten;
checksum observation sums both original banks, and changing a high-bank
ID without updating the checksum no longer matches the byte-sum candidate.
These test the independent research parser, not native duplicate-ID policy
or camera acceptance. py_compile passed and all 385 tests passed.

## Second fixed-point round trip attribution (2026-10-08)

Optional `--second-stage` adds read-only observations at MLib helper
returns 0x8926/0x8954, retaining prior reports under a separate filename.
Owned hidden-host synthetic identity-mode2 inputs produce 71,874 captured
calls for selector 1 and none for selector 2; guarded source buffers remain
unchanged. `verify_second_fixed_stage.py` reproduces every forward/inverse
helper output exactly. Forward mode=11 and inverse mode=10 both use the
helper's mode-2 math; 228 forward inputs include nominal 24-bit overshoot.
The private forward extension reproduces that internal domain without
weakening the production/public reference's domain contract.

First inverse output -> second forward input is exact at all 35,937 nodes.
Second inverse output /2^24 with clamp -> captured pre-color RGB is also
exact at all nodes. This isolates the remaining identity whole-chain
difference to lattice/curve/polynomial/integer preparation before the first
round trip, rather than either fixed helper or the between-stage handoff.
It is intermediate attribution, not whole-chain equivalence or physical
camera evidence. Private reports: MODE_TWO_FIXED_STAGES_SECOND_STAGE_
OBSERVED_20261007.json and SECOND_FIXED_STAGE_ATTRIBUTION_20261008.json.
No camera session, installed DLL edit or production change occurred.

## Current full-chain reconciliation (2026-10-08)

`verify_first_fixed_inputs.py` compares the retained first-forward inputs
against lattice preparation with scales 2^24-1, 2^24 and 2^24+1.
All 35,937 nodes match 2^24 exactly, for direct lattice and one/two cached
identity-curve evaluations. The other scales differ at 35,936 and 3,169
nodes respectively. Identity curves make those three preparation paths
indistinguishable here; this is not a nonidentity-curve proof.

Crucially, rerunning the current `verify_mode_two_empty.py` independently
from lattice through both round trips and final CLUT produces ZERO byte
differences for BOTH selectors, with identity AND mixed matrices:
four cases x 35,937 nodes = 143,748 exact nodes. Both regenerated reference
proof reports pass their final exactness assertion. The earlier statement
that a residual difference remained before the first helper relied on an
obsolete partial result; it is superseded for these bounded controls.
The new second-stage capture confirms intermediates but is not itself what
changed the mathematical implementation this turn. Nonidentity curves,
arbitrary color-axis combinations and broader formats remain separate
requirements; this does not establish universal compiler equivalence.
Private evidence: FIRST_FIXED_INPUT_ATTRIBUTION_20261008.json and refreshed
MODE_TWO_EMPTY/MIXED_MATRIX_REFERENCE_PROOF_20261007.json.

Nonidentity follow-up: input-red-mid96 and post-red-mid96 with identity
matrix, plus post-red-mid96 with mixed matrix, all match the current
independent whole-CLUT reference exactly for both selectors (six additional
cases, 215,622 nodes). Identity matrix makes before/after placement commute,
so that equality alone would not establish order.

Added `--counterfactual-order`, restricted to mixed/post-red/empty-axis
control. It uses the SAME source-checked native trace but deliberately
evaluates the red curve before the mixed matrix in the independent chain.
Both selectors differ at 35,904/35,937 nodes (195,599 and 202,265 bytes),
and the negative-control assertion requires this mismatch. The separate
COUNTERFACTUAL_ORDER_PROOF report does not replace the exact proof.
This provides a discriminating test of curve placement rather than only a
passing identity example. No native execution this follow-up; py_compile
and the 385-test suite pass. Arbitrary curve geometry remains unproved.

Third-group follow-up strengthens the existing mid96 controls: the verifier
now checks full synthetic source equality against baseline except the one
selected 100-byte curve block, selector pairing, and complete profile
equality outside the 1,536-byte output-curve region. All six channel/selector
controls pass. Channel 0 changes exactly 254 output-curve entries; channels
1/2 change none, and the 33^3 CLUT is unchanged in every case.
The ICC header is explicitly checked as RGB input / Lab PCS. Thus the
affected first output curve is in the PCS-side stage, not an additional
pre-CLUT RGB/red transformation despite the fixture's `third-red` name.
This is bounded evidence, not a claim that the other curve fields are
globally unused in every MLib route. No native code executed this follow-up.
py_compile and 385 synthetic tests pass; production remains unchanged.

Combined third-output control now also passes for BOTH selectors with
mixed matrix plus nonidentity post-red curve. A new bounded runner option
`--third-output-curve` permits exactly that combination and writes a
separate THIRD_OUTPUT observation, preserving the baseline capture.
Full-source comparison proves only the third channel-0 curve block differs.
The resulting profile changes exactly the expected 254 first-output-curve
entries; the entire pre-existing transformed CLUT and every byte outside
the output curves remain identical. Both input buffers/guards were unchanged.
Relative proof: MODE_TWO_MIXED_POST_THIRD_OUTPUT_PROOF_20261008.json.
This establishes separation of that output stage under a nontrivial input,
not independent reconstruction of arbitrary ICC headers or all curve shapes.
Owned hidden host terminated; no camera or installed-file writes.
py_compile and the 385-test suite pass.

Five-point geometry expansion: new private input/post controls encode
[(0,0),(64,48),(128,144),(192,208),(255,255)] in the existing 100-byte
curve block. The independent chain constructs its own quadratic spline,
finalizes 256 samples and evaluates the cached curve; full-source checking
verifies all curve words/padding and mixed-matrix coefficients.
New owned-host mixed/post-red-fivepoint capture passes for both selectors:
71,874 total CLUT nodes, zero differing bytes. This extends the bounded
geometry beyond the previous three-point mid96 control, without claiming
arbitrary nonmonotonic/duplicate-x curves. Guarded inputs remained unchanged
and host cleanup completed. Private observation/reference reports are
MODE_TWO_mixed_post-red-fivepoint_OBSERVED/REFERENCE_PROOF_20261007.json.
No production or camera change. py_compile and 385 tests pass.

Quadratic coefficient expansion adds, per output channel, 0.75*own input
+0.125*next input +0.125*own-input squared (16.16 words 49152/8192/8192,
basis square indices 3/6/8). Both selectors' full 33^3 CLUTs match the
independent 19-term polynomial reference and downstream chain exactly:
71,874 additional exact nodes. Full-source checking covers all 60 coefficient
words including padding. Reference evaluation now uses the already-tested
sequential polynomial accumulator, not a special linear-only expression.
The previous mixed-linear control was rerun and remains exact for both
selectors. Private QUADRATIC_MATRIX observation/proof reports retain the
new synthetic case separately. No claim about all 19 terms follows from
this one case. Owned hidden host cleanup completed; source guards intact.
py_compile and 385 tests pass, with no production changes.

Dense cubic follow-up activates all 19 polynomial terms in each output
row: own linear coefficient 32768/65536, the other 18 coefficients
1024/65536, and the unused twentieth word zero. All coefficients are
positive and their sum is 0.78125, deliberately excluding clipping from
this attribution. The independent sequential 19-term reference matches
both selectors' complete CLUTs exactly (71,874 nodes), including final
integer encoding. Full-source assertions validate all 60 words.
Separate DENSE_CUBIC observation/proof reports record the synthetic case.
This covers nonzero cubic/cross-term accumulation together, not arbitrary
signed coefficient ranges or clipping behavior. Owned hidden host cleaned
up; guarded inputs unchanged; py_compile and 385 tests pass.

Signed/clipping expansion uses 16.16 coefficients 81920 and -16384:
1.25*own channel -0.25*next channel, spanning [-0.25,1.25] before clamp.
Hash-gated static window verifies polynomial call 0x83e7, argument==1
branch 0x83f2, three clamp components at 0x840d/0x8421/0x8437, followed
by cached post-curve evaluation. Other argument branches remain separate.
The independent chain now clamps polynomial outputs before post curves;
the controlled SIGNED_CLIPPING full CLUT matches both selectors exactly
(71,874 nodes, zero bytes different). The cached-curve reference's negative
domain guard was NOT relaxed. Native source buffers/guards stayed intact;
the owned hidden host was cleaned up. Static MODE_TWO_CLAMP_WINDOW and
SIGNED_CLIPPING observation/reference reports retain evidence privately.
This covers bounded signed linear/clamp behavior, not arbitrary extreme
coefficients or every gamut branch. py_compile and 385 tests pass.

Complete ICC structural audit of the five newest bounded controls (ten
profiles) now passes `inspect_profile`: envelope length/acsp, unique tag
signatures, aligned tag bounds, overlap rules, mft2 geometry, curve sizes
and padding are checked independently of CLUT comparisons. Observed
A2B0/A2B1/A2B2 tags share exactly offset/size/hash, one 3-input/3-output
33-node mft2 with 16-entry input and 256-entry output curves, RGB/Lab.
The initial private audit incorrectly expected one tag; corrected to
three rendering-intent signatures sharing one payload, not three profiles.
Private NEW_PROFILE_GEOMETRY_PROOF_20261008.json retains all hashes.
Two fixture-free tests explicitly permit three shared intent tags while
rejecting duplicate signatures. No native execution or production change;
py_compile and 387 tests pass. This is structure validation, not independent
ICC header serialization or physical camera acceptance.

Whole-chain verifier now obtains the CLUT from structurally validated
A2B0 tag/declared LUT16 geometry instead of hard-coded tag index 9 and
relative offset 148. The bounded expected dimensions/color spaces remain
explicit. An optional reversed-tag-table control copies the profile in
memory and reverses complete directory entries without changing payloads
or original evidence. Dense-cubic CLUT remains exact for both selectors
under this permutation, proving lookup is not tied to table ordinal.
Separate REVERSED_TAG_TABLE proof retains the result. A fixture-free
regression test also verifies identical signature-indexed metadata after
reordering. py_compile and 388 tests pass. No native execution, original
file change, production serializer or camera operation occurred.

Physical-offset independence control copies retained profiles in memory,
inserts four zero bytes before tag payloads, updates envelope length and
every tag offset, and verifies signature-indexed payload hashes unchanged.
Signed-clipping CLUTs remain exact for both selectors with BOTH reversed
directory and relocated payloads (CLUT file offset 672 instead of 668).
Separate REVERSED_TAG_TABLE_RELOCATED_PAYLOADS proof records this structural
control; it is not a profile sent to Canon or a general ICC writer.
Two fixture-free tests cover valid shared-tag relocation and rejection when
only one shared tag's offset is updated (partial overlap). py_compile and
390 tests pass. No native execution or original-file mutation occurred.

### 17-node packer receiver attribution (2026-10-08)

Static hash-gated evidence PACK17_RECEIVER_20261008.json establishes that
4bb40 calls 470f0 while retaining incoming ECX. The latter searches property
0x1009 through 46c10, which immediately dereferences receiver+4 and walks
record pointers comparing record+4 IDs. It copies two bytes through 46de0.
Consequently this is an object-context style lookup, not a global getter.
The packer's ret 0xc does not distinguish stdcall from thiscall by itself.

The preceding owned-host boundary attempt failed with access violation at
0x4 when invoking the getter without a receiver; it did not establish any
numeric packing equivalence. Its host was cleaned up. Failure persistence
was added afterward, so no failure JSON from that original attempt is
claimed. Next prerequisite: obtain a valid receiver from an owned offline
compiler invocation and verify the calling convention before retrying.
Static extractor assertions and py_compile pass; 390 automated tests pass.
No camera, installed-DLL modification, or production-path change occurred.

PACK17_CALLER_20261008.json now records the aligned caller at 492a0:
492bf saves incoming ECX in ESI; 4934a restores ECX before the call at 49357,
with three stack arguments. This independently supports a receiver-based
thiscall contract. The receiver's originating type remains to be attributed;
no fabricated object or further native invocation was used. Extractor
assertions and py_compile passed.

PACK17_CONTEXT_CONSTRUCTION_20261008.json follows all four direct callers
of 492a0: two construct the stack wrapper with 46be0, two with 4c610.
Each passes owner+4 as its constructor argument. 46be0 stores this at
wrapper+4 and installs vtable bb5e4; 4c610 delegates to it and replaces the
vtable with bc544. Thus passing the public reference/content pointer directly
is not justified: the normal receiver is a wrapper over the record container.
Next attribution is the owner+4 container's provenance. Hash-gated static
assertions and py_compile passed; no native code was invoked this turn.

### 17-node owner provenance (2026-10-09)

RTTI and constructor attribution now identifies CPseInterface (bd3a4),
CPseInterfaceVer2 (be224), CPseInterfaceVer3 (bf0d4). Their carrier method
slot+c is4f2d0/54cd0, retaining incoming receiver inEDI/EBX; those are the
owners supplying+4 to the packer stack wrappers. Base constructor4de20
stores caller's collection at+4, Ver2/Ver3 delegate through53290/53f70.
Normal creation in ad00/ae00 supplies embedded collection at owner+10 and
retains constructed interface at owner+1c. This closes container provenance
one level beyond prior wrapper-only evidence. Does not establish that a
public API pointer can be passed directly to the packer. Reproducible RTTI,
table and aligned instruction assertions saved in
PACK17_OWNER_PROVENANCE_20261009.json; DLL hash verified, no native execution.
Next: observe the normally constructed packer receiver in an owned offline
invocation before numerical boundary comparisons. Prior failed probe remains
a failure, not an equivalence result. Production path unchanged.

### 17-node matrix selection and archival replay (2026-10-09)

4bb40 chooses alternate coefficients only when internal uint16 property1009
is81/84 AND its third stack argument equals1. Otherwise standard coefficients.
This is not a camera-model rule or a UI style index. Exact double constants
extracted from both instruction branches agree with the reference decimals;
PACK17_MATRIX_SELECTION_20261009.json retains addresses/branch evidence.
Added pack17_for_style with explicit bounded internal code/table selector;
rejects bool/float/string ambiguity. Synthetic joint-condition tests and
py_compile pass; full suite448 tests. Existing lower-level boolean API retained.

Replayed PACK17_ALL_VECTORS_TRACE with hash-verified existing private payloads:
96 captured native packed tables equal independent output and decoded payload
blocks byte-for-byte (PACK17_REPLAY_20261009.json). Two original trace entries
contain file-exists output errors and are excluded, not successes. Replay
selects matching matrix numerically; it does NOT independently verify1009
selection for those traces, which did not capture that property. No new DLL
execution, physical camera access or complete independent carrier claim.
