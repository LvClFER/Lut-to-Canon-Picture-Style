# Old dense9 whole-carrier reference — 2026-10-11

The offline reference now reproduces all 48 LUT-vector carriers and all 20
five-base carriers (four explicitly observed old layouts/selectors per source).
Whole SHA-256 equality covers 555,288 bytes, not merely the grid fields.
See the private lab reports `LEGACY_DENSE9_WHOLE_CARRIER_20261011.json` and
`LEGACY_DENSE9_WHOLE_CARRIER_FIVE_BASES_20261011.json`.

The five-base sources expose intermediates above the earlier Neutral-only
286 bound. The explicit research helper `pack9_dense9` accepts the native
dense9 clamp domain 0..320. Four isolated native math comparisons (black,
white320, ramp320 and random320) matched in
`PACK9_DENSE_RANGE_PROOF_20261011.json`. Existing default and observed-only
packer bounds remain unchanged. No production caller was modified.

Both whole-carrier replays execute no DLL and use no captured numerical
grid inputs. They still explicitly require genuine external 1007 resources
and cipher tables read from the known local DLL. This is compiler equivalence,
not zero-Canon-dependency operation or physical camera acceptance.

Validation: py_compile succeeded; full unittest discovery passed 546 tests.
The persistent investigation remains active. Remaining independent branches
include the opaque resource semantics, cipher bootstrap without DLL-derived
preparation, and fresh registration-state/transport reconstruction.

## Resource structure follow-through

Private `LEGACY_RESOURCE_STRUCTURE_20261011.json` compares all 24 old BIN
resources without persisting their bytes. They contain 21 distinct payloads:
103=104, 109=110 and 115=116, but 121 differs from 122. Thus equality of
Portrait/Landscape resources in three families must not be generalized to all.

Interpreting the resource solely as 730 little-endian words for differential
analysis (not as a claimed semantic schema), Standard -> Landscape and
Neutral -> Faithful have identical modular word deltas across all four
families. Eight held-out reconstructions match the complete 1460-byte hashes:
the donor transition is inferred from another family before the held-out
target resource is consulted. No resource or delta constants are embedded.

Standard -> Portrait, Neutral, Faithful and Monochrome do NOT admit that same
whole-resource family-independent additive model. Their family-dependent word
counts are respectively 76, 194, 194 and 190. The Neutral/Faithful difference
changes 48 bytes within offsets 110..232 in every family. This narrows a
possible shared style-dependent region but does not identify its semantics.
No universal resource generator, physical validation, or modern-camera
mapping follows from this four-family inventory. The analyzer passed
py_compile and all eight held-out checks; production code remains untouched.

## Source-field reconstruction hypothesis checked

`match_legacy_resource_fields.py` checks seven hash-identified sources (six
base PF3s plus official Emerald PF2) against all 24 resource records. It
searches aligned resource spans of at least 32 bytes in non-dense source
records of 32..8192 bytes, excluding low-information samples with fewer than
eight distinct bytes. Source records are converted to their host byte order.
No qualifying exact span was found.

The same search explicitly tests the hypothesis of 16.16 int32 source words
narrowed to signed 6.10 int16 words, with both arithmetic shift and truncation
toward zero. No qualifying match was found in these variants either. This
rules out only those bounded direct-copy/narrowing hypotheses, not arbitrary
numerical reconstruction. Dense tables, short constants and low-information
regions were deliberately excluded; absence of a match is not proof that
the resource cannot be derived. The report stores source/segment hashes and
offsets only, not resource or PF3 bytes. No DLL executed and no camera access
occurred. The script passed py_compile.
