# Scalar PF3 controls — private stock compiler evidence

No camera access, installed DLL patch or transport changes. The editor's
Basic aggregate writer/parser offsets are corrected following the evidence below.
Nine route representatives use a recorded R8 descriptor; virtual compilation is
not a firmware simulation or physical camera-acceptance proof.

63 stock compiles: identity plus six independent scalar mutations per route.
Source and private payload hashes are checked before comparison. Offsets below
are zero-based bytes in the complete native payload, not PF3 file offsets.

| Virtual route | Contrast / Strength / Saturation / Tone | Fineness / Threshold |
| --- | --- | --- |
| M50, 7DII, 5DS | 76 / 80 / 84 / 88 | 100 / 104 |
| M3 | 76 / 80 / 84 / 88 | No changed bytes in these experiments |
| C50, R5, 1DXIII | 80 / 84 / 88 / 92 | 104 / 108 |
| 1DIII, 450D | No changed bytes in these experiments | No changed bytes |

All observed compact/integer/17-node packer outputs remain identical. C50 has
no captured packer, so packer equality is explicitly unknown; its full payload
comparison still confines changed bytes to the scalar header. This separates
native Basic parameter transport from LUT baking, not proof of rendering order
inside the camera. No change on an old route does not establish lack of camera
support: a different registration/API path may carry those controls separately.

The initial eight nonzero candidate contrast values in -4..+4 are Canon-serialized scratch PF3s.
Their API readback and decoded field are exact signed values. Stock M50 output
preserves +1..+4, but ALL -1..-4 become unsigned header value7 at byte80.
The labels in that initial sweep inherited the old app's wrong assumption.
A second sweep of1031 preserves every signed value-4..+4 at byte76. Static
code4f9e3/4f9e8 reads1030, then4fa19/4fa1c uses an UNSIGNED comparison against7
and clamps larger values to7. Equivalent clamps occur in the other native
builders. This is the unsigned sharpness-strength record, not contrast.
The parser's aggregate1031->offset0 and1030->offset4 mapping is independently
confirmed by Canon serialization and controlled file omission. Missing Basic
records expose Standard default words[0,3,0,0,0,0,4,4], with Neutral[0,0,...].

Correction: canon_engine.modify_basic_0115/parse_basic_0115 now put/get contrast
at0 and strength at4. All other offsets and opaque words are preserved. Backup
is private BASIC_MAPPING_FIX_BACKUP/canon_engine.py. Five Canon-serialized
scratch exports generated with the actual editor function have exact fields
1031=-2,1030=5,1032=2,1033=-1,1034=2,1035=3 and unchanged unrelated properties.
Original PF3s remain intact. Older exported PF3s can contain inverted values;
do not silently rewrite user assets based only on their numeric values.

Native validation of the corrected actual editor writer passes15/15 cases:
five bases across compact1042, modern17R5 and full33C50 virtual routes. Intended
six controls are exactly[-2,5,2,-1,2,3] at the native header, ALL native color
blocks equal the same base's earlier output, and no bytes outside the six
intended scalar words change. This checks serialized records AND compiled
headers, not merely an exporter/parser roundtrip sharing the same mistake.

Official Canon control domains corroborate the interpretation: strength0..7,
contrast-4..+4, fineness/threshold1..5:
https://cam.start.canon/en/C004/manual/html/UG-03_Shooting-1_0150.html

Evidence under private workspace tmp/PF3_FIELD_EXPERIMENTS_20261004:
- BASIC_CONTROLS_NINE_ROUTES_TRACE.json
- BASIC_CONTROLS_NINE_ROUTES_COMPARISON.json
- CONTRAST_SIGNED_SWEEP/FIELD_EXPERIMENTS.json
- SCALAR_1031_SIGNED_SWEEP/FIELD_EXPERIMENTS.json
- BASIC_OMITTED_DEFAULTS/BASIC_DEFAULTS.json
- EDITOR_BASIC_MAPPING_SERIALIZATION/BASIC_DEFAULTS.json
- EDITOR_BASIC_MAPPING_NATIVE_TRACE.json
- EDITOR_BASIC_MAPPING_NATIVE_CHECK.json

Camera EDSDK registration0x00000115 remains untouched. The PF3 parser's
synthetic Basic aggregate with the same ID is a separate file/API context.

## Four auxiliary zero/one flags

45 additional stock compiles: baseline plus individually toggled100c,1011,
1012,1080 across nine route representatives. Canon serialization verifies each
requested single-field change. Only100c changes native bytes: one byte at364
(M50/7DII/5DS),356(M3),332(1DIII/450D),368(C50/R5/1DXIII). All observed packers
remain identical; full33 comparisons also confine changes to the header.
1011/1012/1080 toggles0->1 produce byte-identical native outputs in all nine
tested contexts. This does not establish their rendering/API meaning or justify
removing them. They are retained in original/exported PF3s.

Raw getter4ef20 captures actual1030..1035/100c reads and caller RVAs. The earlier
4ef70 observer captured no scalar reads in this compiler path; that empty trace
is retained as a failed observer hypothesis, not absence-of-use evidence.
Static46f90 reads100c as a two-byte property; native builders copy it near the
table headers. Do not invent a color-space or rendering label for this flag.
Evidence: AUXILIARY_FLAGS_NINE_ROUTES_TRACE.json and
AUXILIARY_FLAGS_NINE_ROUTES_COMPARISON.json.
# Bounded fineness transport sweep — 2026-10-06

Private evidence: `SHARPNESS_1034_M50_20261006_V2/FIELD_EXPERIMENTS.json`
under the private field-experiment directory. Stock, hash-verified compiler;
Fine Detail source, recorded M50 ID 1042 and borrowed recorded R8 descriptor.
No camera access, compiler patch or source changes.

The source's 0x1034 scalar is zero. Canon-serialized single-field mutations
1 through 7 pass the native API gates. Value 1 produces identical output to
the zero baseline; 2/3/4/5 produce the corresponding byte at offset 100;
6/7 produce 5. Each non-identical output differs by only that one byte.
Thus this particular transport clamps fineness to 1..5, including the observed
zero sentinel. This proves transport behavior, not native preview sharpening
or physical M50 support. The initial Threshold runs did not produce reports
and remain unvalidated attempts; the successful follow-up is recorded below.

Research generator tests and full suite: 271 passing; py_compile passed.

## Completed sharpness boundaries across three output geometries

Private reports: `SHARPNESS_1034_M50_20261006_V2`,
`SHARPNESS_1035_M50_20261006_V3`, `SHARPNESS_1034_R8_20261006`,
`SHARPNESS_1035_R8_20261006`, `SHARPNESS_0x1034_C50_20261006`,
`SHARPNESS_0x1035_C50_20261006`. All use the same untouched Fine Detail
source and recorded R8 descriptor. These are virtual compiler tests, not
camera sessions or individual model support validation.

42 independently serialized scalar mutations (seven values per field/route)
confirm both fields clamp to 1..5. Zero baseline equals value 1; values 6/7
equal 5. M50 16752-byte output offsets are 100/104; R8 83076-byte and C50
431616-byte outputs use 104/108. All other payload bytes are identical.
`camera_install.sharpness_transport_reference` independently re-reads private
payloads, checks hashes/API gates/complete sweep and compares every byte,
rather than trusting the changed-offset claims in the native report.

Read-only disassembly of the known compiler revision supplies corroboration:
PF3 output block reads 1034 at RVA558b9 and 1035 at558d3 via4ef20. Unsigned
upper/lower comparisons at55909/55917 and5594c/5595a clamp the corresponding
header words at offsets64/68 to5/1. The executable-section candidate scan is
retained privately as `SHARPNESS_CLAMP_STATIC_CANDIDATES_20261006.json`;
its other matches are candidate references, not fully traced execution paths.

274 automated tests pass; modified Python files compile. No production
sharpness rendering claim or camera-install behavior was changed.

## Basic getter coverage across all 87 recorded IDs

Private evidence: `BASIC_READS_TEN_CLASSES_20261006` and
`BASIC_READS_ALL_RECORDED_IDS_20261006/HIGH_BANK_RESULTS.json`, with
`BASIC_READS_ALL_RECORDED_IDS_SUMMARY_20261006.json`. All original input hashes
were rechecked by the driver; no modified inputs. Identity PF3, shared recorded
R8 descriptor, stock exact-known compiler, no EDSDK or camera session.

The new separate bounded observer records only successful/failed four-byte
1030..1035 reads through raw getter4ef20, without using up the existing grid
observer's capacity. Summary distinguishes a missing observer from an empty
observed read list and keeps native compilation failure separate.

Observed read sets match internal classes across all87 recorded IDs:

| Internal classes | Recorded IDs | Observed Basic reads during output |
| --- | ---: | --- |
| 1/2 | 4 | None at4ef20; compilation fails |
| 3/4 | 7 | None at4ef20; compilation succeeds |
| 5 | 23 | 1030/1031/1032/1033, no1034/1035 |
| 6/7/8/9/10 | 53 | All six1030..1035 |

Among the53 six-field cases,43 compile successfully and10 remain failed
old-initialization cases. Reading all Basic fields therefore does not imply
a usable carrier. Overall73 compile and14 fail, preserving the prior baseline.
Absence at the two observed lookup/getter paths is not a proof that a camera
lacks such controls or cannot receive them through a separate transaction.

Reproduce the compact summary with `python -m camera_install.basic_read_coverage
PRIVATE_REPORT PRIVATE_EXCLUSIVE_OUTPUT`.277 tests and py_compile pass;
`node --check camera_install/high_bank_probe.js` passes.
