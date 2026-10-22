# PF2/PF3 cipher dependency — static evidence

Scope: offline examination only; no DLL execution or camera access.
EdsCFParse SHA-256:
`7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0`.

At RVA `2db0`, the routine initializes pointers into two on-disk tables:
`ce000..ce1ff` (512 bytes) and `ce200..ce400` (513 bytes).
The first starting index is `seed & 511`; multiply-high by `ff803fe1`,
shift-right 9 and multiply by 513 derive the second remainder.
Each byte is XORed with both table bytes and `37`; pointers wrap at the
inclusive table ends. This confirms the existing modulo-based decoder for
the ordinary non-overflowing seed/length ranges used by the fixtures.

Both tables are present in the writable `.data` section. A linear executable
section disassembly found direct references to the table starts only at
`2dca`, `2dd5`, `2e08` and `2e17`, all within this cipher routine.
This is not an exhaustive indirect-reference or initialization analysis:
it does not prove the tables are never modified or reveal a generator.

The combined index cycle repeats after 512 × 513 = 262656 bytes because
the lengths are coprime. This is an upper period bound, not a claim that
the actual XOR stream has no smaller period.

Remaining dependency: the numerical tables are still read from the user's
known-hash local DLL. No proprietary table bytes have been embedded in code
or included in this note. A portable algorithm alone does not remove this
dependency; a clean derivation or independently reviewed alternative remains
necessary before claiming Canon-runtime independence.

## Cross-version and reconstruction experiment

Seven archived DLL files represent five distinct SHA-256 revisions. All contain
the exact same contiguous 1025-byte tables. Besides the reference x86 revision,
the distinct hashes are `df821f193048603962b282e593503a87fa1072a966e7a1583af85239d96d4848`
(x64, table RVA522b0), `70c6e6baa60389f223341898068acf890a0945a90752f34fe82fd4f52bfe7304`
(x64, RVA71000), `783964dbe80b26db7c4ac2b28205d1b8fb09ba6bb40562984b84fa168f43e83d`
(x86, RVA3d218), and `8837dc1094941d345b7d0cc798e2a64e75f0bcf31ef22a708dfcb5c061d632ff`
(x86, RVA20198). This supports sharing across these revisions only.

The reference revision's relocation entries pointing into the tables occur
only at2dcb/2dd7/2e01/2e09/2e11/2e18. No PE TLS directory is present.
Neither observation excludes indirect initialization or mutation.

`cipher_known_plaintext_reference.py` solves a bipartite XOR-constraint graph
from aligned plaintext/ciphertext, rejects disconnected/inconsistent evidence,
and fixes one free common-XOR byte to produce *equivalent*, not original, tables.
It contains no Canon table constants. Synthetic tests cover seven seeds and a
held-out entire index cycle. A private oracle-assisted proof recovered from
2048 bytes at file offset3182 and matched all12 archived PF3 files (5213988
encrypted bytes compared). Recovered tables were not persisted.

Critical limitation: the private proof obtained its known plaintext from the
existing local-DLL decoder. It proves reconstruction mechanics, not a clean
independent bootstrap. The archived file named IDENTITY was not assumed to
contain a mathematically exact identity table: simple grid hypotheses failed.
An independently established known-plaintext source is still required.

## Constant-table construction proof

The12 archived probe files contain no contiguous zero-plaintext runs of at
least1024 bytes. Their names do not establish exact known contents.
Their original builder applies probe LUTs to a pre-existing base table;
therefore `01_IDENTITY` means an identity *operation*, not necessarily an
identity-valued final table.

`verify_constant_table_bootstrap.py` separately constructs a zero-sample1070
table in memory, preserving its12/3/33 header and all other records, updates
the observed additive checksum, and encrypts with local tables during setup.
The recovery function receives only that constructed encrypted file and the
known sample offset; it uses2048 explicitly zero-valued plaintext bytes.
Recovered keys decode the entire constructed file exactly, the checksum
matches, and unrelated records remain unchanged. No scratch PF3 or keys were
persisted. Report: `CONSTANT_TABLE_BOOTSTRAP_20261011.json`.

This removes the circular plaintext-oracle dependency from the *recovery
stage*, not from test preparation. It is not a distributable bootstrap file,
does not recover arbitrary unknown files automatically, and has not been
accepted by the native parser or camera. Production export is untouched.

## Sparse bootstrap and compact padding bound

The solver now accepts independently known sparse byte triples, with explicit
stream position (seed+offset), not file offset. A synthetic CRT spanning tree
of1024 disjoint observations reconstructs an equivalent stream and passes a
held-out262656-byte cycle. No real Canon keys are embedded in this test.

The10-node packing geometry leaves24 of1024 words unused. Across the two
observed block seeds b8ed/33137 these give192 distinct zero-byte stream
positions, touching only48/512 first-table and36/513 second-table nodes.
Even before testing connectivity,192 constraints cannot connect1025 nodes
(minimum1024 edges). Repeated carriers with the same geometry/seeds do not
add new positions. Therefore unused compact slots alone cannot bootstrap
the full cipher. This is a structural negative result, not a camera test;
other independently known bytes or constraints would still be required.

### Combining12-bit restrictions with compact padding

A further structural graph experiment combines the192 compact-padding byte
positions with the known zero high nibble of each big-endian12-bit sample.
This assumes an explicitly located, even-aligned215622-byte sample region;
it does not infer a record location from ciphertext or assume a file name
establishes its contents. The test uses positions only, no DLL or secret keys.

For bits0..3, the largest connected component has42 nodes and943 components
remain. For bits4..7, the largest has793 nodes with233 components remaining.
One component across all1025 nodes would be needed for full stream recovery
under these XOR constraints. Thus12-bit bounds plus compact padding still
cannot independently bootstrap the cipher. Additional known plaintext or
independent numerical constraints are necessary; synthetic solver success
must not be presented as a solution to this real input-dependency gap.

## Bounded generator hypotheses

`test_cipher_generator_hypotheses.py` tests three specified LCG outputs:
MSVCRT(214013/2531011), ANSI(1103515245/12345), Delphi(134775813/1),
each taking state bits16..23. Higher state bits cannot affect this window;
all65536 low-state possibilities below the first observed byte are enumerated.
All256 common XOR-byte variants are tested independently for both tables.
None survives the first8 observed bytes. Three synthetic512-byte held-out
self-tests verify the recovery mechanics, including a nonzero XOR transform.

Report: CIPHER_GENERATOR_HYPOTHESES_20261011.json in the private lab.
No table bytes or inferred states are persisted; only counts and provenance.
This rejects these exact hypotheses, not arbitrary PRNGs or all clean
derivations. It does not establish that the constants are truly random.

## Both PF3 tables and all observed record headers

`analyze_pf3_header_bootstrap.py` adds the eight-byte headers of every record
in the explicitly assumed 434511-byte layout, both 12/3/33 table headers,
and the known zero high nibble of every sample in both tables. This is a
position-only experiment; it neither reads a DLL nor assumes encrypted
contents can establish their own plaintext.

The full-byte constraints cover 236 positions but leave 793 components
(largest 56 nodes). Adding sample high nibbles leaves 161 components
(largest 865 nodes) for bits4..7. Thus even both tables and all headers do
not connect the cipher graph. Repeated files with exactly this layout add
no structural positions. Different independently established layouts or
known sample values remain possible sources of new constraints.

Report: private lab `PF3_HEADER_BOOTSTRAP_20261011.json`. This is not a
successful independent bootstrap and does not change production decoding.

## Archive layout diversity

`analyze_archive_layout_coverage.py` scanned529 archived PF3 paths and found
141 distinct file hashes, including12 checksum-valid version3000 layouts;
9 distinct/oversized inputs were rejected by the bounded envelope/parser
checks. No native DLL was executed and no camera was accessed. The known
DLL was read as a private oracle to locate records; hence these locations
are not yet autonomously established by the independent reader.

Combining headers across these layouts yields1157 full-byte positions:
92 components remain, largest883 nodes. Adding the independently bounded
high nibble of12-bit samples yields20 components, largest1006 of1025 nodes.
Layout diversity materially increases coverage but does not complete even
the high-bit graph. Low bits remain more underconstrained. Simply adding
duplicate files cannot resolve those missing positions.

Private report `ARCHIVE_LAYOUT_COVERAGE_20261011.json` stores layout sizes,
record IDs/types and source hashes, not keys or decoded property values.
Next useful evidence must add independently known bytes connecting these
components, not reuse oracle-decoded values as proof of independence.

### Actual masked constraint consistency

The archive experiment now supplies225560 normalized position/mask
constraints to the portable `recover_masked_tables` implementation, not
merely to a connectivity counter. All overlapping constraints agree and
all eight bit graphs pass cycle consistency checks. Recovery correctly
rejects the remaining disconnected components (`consistent-but-incomplete`).
Only header values and12-bit high-nibble bounds are admitted; arbitrary
oracle-decoded sample values are never promoted to known plaintext. The
oracle is still used for record location and geometry validation, so this
is a private algorithm-validation experiment, not independent bootstrapping.

## Historical PF2 evidence (not a production format change)

The private archive inventory optionally includes observed2000/2001 PF2
envelopes and the existing research parser's9000..90ff record branch. Both
declared file length and the observed additive checksum remain mandatory.
This does not relax `pf3_source_reference` or select PF2 for installation.

689 paths yielded244 distinct file hashes and16 accepted layouts.107 inputs
were rejected:96 envelope/declared-length failures and11 checksum-rule
mismatches. Rejection means unsupported by this experiment, not corruption.
The accepted constraints agree:225695 masked positions, no contradictory
cycles. Low bits now have44 components (largest976 nodes); high bits have12
components (largest1014). Reconstruction remains incomplete.

Report: `ARCHIVE_PF2_PF3_LAYOUT_COVERAGE_20261011.json`. Locations still use
the local DLL as a read-only oracle, with no native execution or key output.

### Declared PF2 bodies with unexplained trailing bytes

Envelope-only inventory (no DLL) identifies95 version2001 files whose actual
body is exactly four bytes longer than declared. A separate private oracle
test finds all95 declared bodies parse into11 records endingffff, with zero
tail and matching additive checksum. Decoding the actual body instead leaves
four bytes after the same valid terminator. Those bytes remain unexplained;
this does not authorize discarding them in a serializer or installer.

The explicit research-only `--include-pf2 --historical-tail` option analyzes
only the checksummed declared bodies. Combined coverage increases to18
layouts and225717 masked positions, still consistent but incomplete: low
bits39 components/largest983; high bits10 components/largest1016.12 unique
inputs remain unsupported (11 checksum mismatches, one4000 envelope).
Production PF3 envelope/length validation remains strict and unchanged.

Reports: `STYLE_ENVELOPE_INVENTORY_20261011.json`,
`PF2_EXTRA_TAIL_20261011.json`, and
`ARCHIVE_PF2_PF3_TAIL_LAYOUT_COVERAGE_20261011.json` in the private lab.

## Checksum constraints without a table oracle — 2026-10-16

New private experiment: `checksum_cipher_constraints_20261016.py`. It reads
encrypted PF2/PF3 files and explicit layout hypotheses from the existing
18-layout manifest. It does NOT read or execute a Canon DLL, take known cipher
tables, obtain sample plaintext from a decoder or persist recovered tables.
Z3 is installed only in the private lab's research_dependencies directory;
no application dependency or public runtime requirement has been changed.

The disconnected XOR graph is represented by unknown per-component bits.
Each plaintext-byte sum is expanded into constant terms plus weighted Boolean
component-pair parities. The encrypted checksum word is expanded by the same
rule, including big-endian positional weights. Sixteen synthetic weighted-sum
self-checks verify this expansion independently of Canon data.

Two additional explicit grammar hypotheses apply only to matching record
geometries already consumed by portable references: 1061/1062 type4 size512
as kind2/count6 with six five-point group headers; 1023/102b type4 size8 as
kind1/count0. No axis coordinates or numerical LUT samples are assumed known.
These structural bytes agree across the selected files and reduce the nibble
graphs from39/10 to13/4 components. Their applicability to arbitrary files is
not inferred just from a byte length.

With the original18 representative source hashes, the18 checksum equations
have one solution after fixing the irrelevant common-XOR gauges. A second
solution is UNSAT. The recovered candidate validates232 unique files,
including214 held out of the equations;12 remain rejected. The strict public
PF3 reader accepts132 and rejects two additional historical layouts even though
their generic checksums pass. Its domain was not relaxed. Report:
`CHECKSUM_CIPHER_AXIS_CONSTRAINTS_20261016.json`.

An envelope/declared-length-only selection experiment removes source hashes
from representative selection. Choosing the first encrypted candidate per
layout hypothesis produces UNSAT, retained as negative evidence. Choosing the
second candidate gives a satisfying candidate that again validates232/214
files, but the second-solution check times out: uniqueness for that selection
is not yet proved. A bitvector alternative also times out on uniqueness; it is
not stronger evidence than the integer/Boolean result.

This is materially stronger than recovery with DLL-decoded known plaintext,
but it is not yet an autonomous bootstrap for an arbitrary user's PF3. The
18 explicit layouts still originate in oracle-assisted format investigation;
candidate selection, uniqueness and acquisition of a sufficient corpus remain
integration requirements. No recovered constants, source PF3s or calibration
corpus have been embedded in the application. The editor still receives no
independent keys and its independent mode remains disabled.

The envelope-selected candidate was also passed in memory to the existing
`offline_registration_reference.prepare` for all8 current project exports:
8 experimental16752-byte cache-route carriers compile without a Canon import,
with9110 plans selected from the actual RP DeviceInfo operation list. None of
their normalized content hashes equals the observed live slot1 style. This
does not validate the cache route on RP or authorize a write. No key/carrier
was persisted; only source/output hashes and counts appear in the private report
`CHECKSUM_CIPHER_ENVELOPE_OFFSET1_20261016.json`. Its uniqueness result remains
timeout/unknown, distinct from the original hash-selected experiment's UNSAT
second-solution result.

## Nested grammar closes envelope-selected uniqueness

The private checksum experiment now has an opt-in `--nested-geometry`
hypothesis for456-byte1008 fields: inner BE TLV header0010/type4/size440 and
the final eight-byte terminator. It assumes no sector coordinates, coefficients
or decoded calibration arrays. These16 grammar bytes reduce the graph from
13/4 to6/2 low/high nibble components, leaving24 unknown component-gauge bits
after anchoring. Compact unused-slot positions alone would reduce this to5/2;
no live bytes were used by this experiment.

With `--select-by-envelope-size --selection-offset 1`, the strengthened model
is SAT and its second solution is UNSAT. It again validates232 unique files,
including214 held out, with132 accepted by the strict public PF3 reader. Report:
`CHECKSUM_CIPHER_ENVELOPE_OFFSET1_NESTED_20261016.json`. This replaces the
previous timeout only for this stronger, separately recorded hypothesis. It
does not remove explicit layout assumptions or justify choosing offset1 for
an arbitrary input corpus.

`check_rand255_hypotheses_20261016.py` separately exhausts the three previous
LCGs using `(31-bit state >>16) %255`, followed by any common XOR byte. All
relevant31-bit initial states are enumerated by high15 congruences and low16
values; three512-byte synthetic held-out checks exercise the search. No eight-
byte prefix candidate survives for either table/any generator. The tables were
reconstructed in memory from the checksum proof, with no DLL reads/execution,
camera access, key persistence or application dependency change. Report:
`CIPHER_RAND255_HYPOTHESES_20261016.json`. This rejects only the named generators
and output rule, not arbitrary PRNGs or other clean derivations.

## Automatic corpus selection with held-out verification

`--robust-envelope-selection` now considers all encrypted candidates matching
the18 explicit envelope/length schemas. Alternating computed-hash ranks form
training/hold-out partitions within each schema; no pre-recorded source hash or
hand-picked selection offset chooses an exemplar. Known structural nibbles use
a strict majority across training observations (ties fail). Each schema requires
at least one candidate checksum equation, represented by a disjunction; damaged
or unsupported training files therefore need not all satisfy the model.

With axis and nested grammar enabled,125 training candidates yield6/2 graph
components and18 groups of checksum alternatives. The result is SAT and a second
solution is UNSAT. Full independent parsing/checksum validation accepts232 files,
including111 held out;4 training files are rejected. Every schema has at least
one fully validated training candidate. The strict PF3 parser still accepts132,
with12 generic rejections and2 checksum-valid historical PF3 layouts outside its
domain. Sixteen checksum-expansion checks and two strict-majority checks pass.
Report: `CHECKSUM_CIPHER_ROBUST_ENVELOPES_20261016.json`.

The first private harness run stopped because its old assertion required every
training file to be valid, contradicting the disjunctive policy. The corrected
check requires a fully parsed/checksummed candidate for every schema and records
all rejected training files. The completed result above comes from a fresh run.

This removes source-specific exemplar choice on this corpus, not the remaining
format/corpus assumptions. The18 schemas originate in the earlier format
investigation, structural-majority consistency is assumed, and arbitrary single
PF3 bootstrap is not established. No source corpus, key tables, descriptor or
camera carrier is bundled; no editor/build path is enabled by this experiment.

## Single mathematical-identity calibration, no layout/key oracle

`camera_install/identity_pf3_bootstrap_reference.py` now recovers equivalent
stream tables from one explicitly supplied identity PF3. Its expected33³/12-bit
RGB data is generated mathematically with nearest quantization; no Canon table,
PF3 base, descriptor or decoded calibration array is embedded. The module uses
only the standard library and the existing strict PF3 reader/XOR graph solver.
It performs no file discovery, persistence, OS/device access or native loading.

For the stream K(p)=A(p mod512) XOR B(p mod513) XOR37, the rectangle
K(p) XOR K(p+512) XOR K(p+513) XOR K(p+1025) is zero: each entry of both tables
occurs twice. Applying this rectangle to ciphertext therefore reveals the same
fingerprint as applying it to plaintext, independently of key values and seed.
The implementation searches a64-byte fingerprint of the mathematical identity
record, recovers from2048 aligned bytes at each candidate's discovered absolute
position, then strictly validates the entire PF3/checksum and an entire identity
record1070/1071. A matching prefix alone is insufficient. At most32 candidates
are examined; multiple differing verified equivalent streams fail closed.

Six synthetic tests cover random-stream rectangle cancellation, unannounced
record offsets, both dense IDs, repeated candidates, correct-checksum files
with only a known prefix, bad checksums/envelopes/types and a fresh interpreter
that blocks native, device, NumPy and Z3 imports. The integrated fake-COM test
now begins with this calibration before compilation/session/UI lock/style/state/
unlock/requested-content comparison.622 discovered tests pass; the10 focused
bootstrap/integration cases also pass after that integration change.

The private `verify_identity_bootstrap_20261016.py` independently considers249
encrypted inputs without reading a layout manifest, decoded oracle, key table
or DLL. Six files calibrate independently to the same equivalent stream;137
strict PF3 files validate,131 outside those calibration inputs. All8 project
exports compile through the explicit experimental cache route; the reviewed
Classic_Cuban_Neg carrier hash is reproduced exactly. No keys or decoded table
bytes are persisted. Report:`IDENTITY_PF3_BOOTSTRAP_PROOF_20261016.json`.

This is a single **identity reference file** bootstrap, not bootstrap from an
arbitrary style. Structural classification found no identity table in the5
unique current exports and no2048-byte zero runs in the137 accepted PF3s. The
saved camera-style backup matches none of the tested mathematical identity
cache variants; it must not be assumed to provide that known plaintext.

## Existing editor bases can supply that reference locally

In response to the user's clarification, all6 existing files under the editor's
`app_data/cache/generated_pf3_bases/` were checked directly by the new portable
bootstrap. Faithful/Fine Detail/Landscape/Neutral/Portrait/Standard all validate
and recover the same stream. Using that recovered stream reproduces all8
experimental export compilations, including the reviewed Classic carrier hash.
No Canon runtime was loaded. Metadata-only report:
`EXISTING_EDITOR_BASES_BOOTSTRAP_20261016.json`.

These are the editor's previously generated mathematical-identity bases, not an
assumption about every hash-validated genuine Canon template or arbitrary PF3.
`canon_engine.generated_pf3_properties` already generates their identity grids;
the current fallback uses Canon serialization to create the encrypted files.
The new recovery only needs one file that already exists. On a clean computer
without such a file, bootstrap still needs a user-supplied reference; do not
generate it by covertly loading Canon or bundle a private PF3/key as a shortcut.

The user did not understand the initial calibration choice and asked whether it
meant the bases already used by the editor. The existing generated bases do
work; the question was clarified on that evidence rather than treating the
confusion as consent. Product integration remains unfinished. No new physical
operation, executable build, RAW/DPP replacement or independent-mode enablement
occurred during this work.

## Follow-up: the application now serializes its own PF3 files

The user's requirement is generation by the application, including the bases.
`pf3_source_reference.write_source_fields` now constructs the envelope and typed
records, recomputes the checksum and encrypts with recovered in-memory tables.
`canon_engine.create_generated_base_pf3(None, ...)` builds all fields from the
existing mathematical property generator, using a prior identity PF3 only for
cipher recovery. Each of the six generated files exactly matches the hashes
listed above. This is independent serialization, not a copied-template export.

The existing editor's no-DLL base/open/export paths now use this implementation;
the Qt export test disables discovery and rejects any EdsCFParse load. An edited
PF3 with an inverse LUT and changed Basic fields reopens with the same controls
and expected table endpoints. Missing calibration and atomic replacement errors
preserve existing user output. Native fallback remains available.

The cipher bootstrap on a machine without any reference PF3 is still unresolved.
No embedded cipher constants, encrypted calibration asset, Canon runtime load,
hardware access or executable build was introduced to hide that dependency.

## Own generated records also bootstrap nonidentity LUT exports

The application-generated property set has a2968-byte contiguous record block
constructed from its own identity matrices, two-point curves, default control
buffers and typed headers (1021,1029,1019,1018,1065,1061,1062,1023,102B,1008,1012).
These are algorithmically generated fields, not copied Canon constants. A LUT
edit changes1070/1071 without requiring that block to change.

`recover_known_fields_calibration` now accepts this caller-owned ordered block,
locates it using the same key-independent rectangle, solves the stream from2048
known bytes and verifies all complete supplied records plus the whole checksum.
A matching prefix alone is rejected. The strict identity-only function keeps
its previous domain; nonidentity data is not reclassified as an identity LUT.

An offline check put each of10 distinct existing exports in a separate folder
with an empty runtime cache and EdsCFParse forbidden. The three newer
application-generated files (superia400, c200, NC) bootstrap from themselves.
The seven older styles have different matrix/control records and correctly
fail that route, retaining their explicit identity-reference/bundle path.

New bundles omit an additional cipher-reference PF3 when their base itself has
the exact contiguous application-generated records. Other styles retain the
owned identity reference inside the project. Tests reimport a lone modified
PF3 with no identity table or external cache, preserve the older reference path,
and reject partial-prefix and wrong-record evidence.

This removes an external-reference requirement for our generated nonidentity
exports, not for every PF3, and not for the first file on a completely clean
machine without any supplied encrypted PF3/camera evidence. Initial zero-asset
bootstrap remains unresolved. No proprietary stream tables were embedded.
## Structural bound for the observed RP read-only positions,2026-10-16

Private `RP_READ_ONLY_BOOTSTRAP_BOUND_20261016.json` considers even completely
known matrix/control plaintext at the observed descriptor/control seeds plus
unused packed-grid words. The resulting916 full-known byte positions leave267
components for bits0..5. Including packed high-bit zeros leaves7 components for
bits6/7. Repeated matrices at the same seeds add no distinct positions.
Consequently these linear known-bit constraints alone cannot recover the full
equivalent cipher stream. This is not an impossibility claim for nonlinear
constraints, different observations, or a future generator. No key, Canon
binary, ciphertext or camera access was needed for this position-only bound.

## Bounded linear-generator hypothesis, 2026-10-18

The private `test_cipher_linear_generator_20261018.py` checks a different
hypothesis from the previous LCG experiments: each bit plane of either table,
optionally inverted, follows a binary linear recurrence of degree at most 64.
Equivalent stream tables are recovered in memory from the user's owned project;
the experiment neither reads a Canon DLL nor opens hardware.

Six synthetic recurrence/inversion cases predict their complete held-out suffixes.
For the real tables, all 32 plane/polarity cases require degree 126–130 already
within their first 256 bits; none predicts its held-out 256/257-bit suffix. This
rejects the stated low-degree linear family only. It does not exclude nonlinear
generators, prove randomness or establish that zero-input initialization is
impossible. No table bytes, fitted polynomial or initial states were persisted.
Report: `CIPHER_LINEAR_GENERATOR_HYPOTHESIS_20261018.json` in the private lab.

An external implementation was also reviewed as a possible independent lead:
[Canon LUT Lab](https://github.com/EdwinjJ1/canon-lut-lab). Its documented R7 path
uses a user-created PSE template and a fixed Canon parser; it therefore does not
provide the missing zero-asset independent initialization. Its reported camera
results are external evidence and do not validate this application's R7 path.
