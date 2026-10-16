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
