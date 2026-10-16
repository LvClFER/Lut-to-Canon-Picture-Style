# PF3 structure and Canon DLL investigation — 2026-10-04

Scope: twelve controlled PF3 vectors, seven scratch-only control experiments,
EdsCFParse x86 3.20.20.0. No camera access, installed-DLL modifications, production
compiler changes, or public packaging of Canon-derived captures.

## Observed file format

- 12-byte envelope. Bytes 4–7 are `PSP\0`; bytes 8–11 are the big-endian body size.
- The DLL transforms the body from file offset 12 using the observed XOR routine
  with seed 12. An independent Python decoder and its inverse match the observed
  transformation byte-for-byte on all twelve vectors. It still reads the cipher
  tables from the installed, hash-checked DLL; this is not a dependency-free release.
- Decoded records: big-endian `uint16 ID`, `uint16 type`, `uint32 payload length`,
  then payload. No alignment padding was observed.
- Types: 2 preserves bytes; 3 swaps 16-bit elements; 4 swaps 32-bit elements;
  `0xffff` preserves opaque bytes. Every observed normal record matched the
  corresponding `0x40000000 | ID` property through this conversion.
- 26 normal records, checksum record `0xfffe`, and terminator `0xffff`.
- Checksum record: type 4, length 4, big-endian unsigned sum of every decoded
  byte before that record (modulo 2^32). This candidate matches all twelve vectors.
- Terminator: ID/type `0xffff`, length 0. Entire body accounted for; no leftover bytes.

These observations establish the format of the tested vectors, not every historical
PF2/PF3 revision or every possible Canon record.

## Record inventory

| IDs | Payload | Status |
| --- | --- | --- |
| `1009` | 2 bytes, type 3 | Base-style identifier; tested vectors are Neutral (`0x84`). Changing this ID alone is **not** a validated base-style conversion. |
| `1030`–`1035` | 4 bytes each, type 4 | Six scalar controls; serialization and PF3 aggregate offsets experimentally verified. |
| `1002` | 32 bytes, type 2 | Name. |
| `100a` | 64 bytes, type 2 | Metadata/opaque semantics unresolved. Preserve, do not infer a text-only schema. |
| `1021`, `1029` | 240 bytes each, type 4 | 60 32-bit elements; mathematical role and scaling still require tracing. |
| `1019`, `1018`, `1065` | 300 bytes each, type 4 | Curve-like data; complete channel/stage semantics unresolved. |
| `1061`, `1062` | 512 bytes each, type 4 | Structured parameter data; semantics unresolved. |
| `1023`, `102b` | 8 bytes each, type 4 | Two 32-bit elements; semantics unresolved. |
| `1008` | 456 bytes, opaque type | Structured nested-looking data; semantic interpretation unresolved. |
| `1012` | 4 bytes, type 4 | Flag/parameter semantics unresolved. |
| `1070`, `1071` | 215628 bytes each, type 3 | Six-byte `[12,3,33]` header plus 107811 12-bit samples in 16-bit containers. Two distinct 33³ RGB tables, not assumed interchangeable. |
| `100d` | 3 bytes, type 2 | Short metadata, semantics unresolved. |
| `100c` | 2 bytes, type 3 | Flag/parameter semantics unresolved. |
| `1011`, `1080` | 4 bytes each, type 4 | Flag/parameter semantics unresolved. |
| `fffe`, `ffff` | 4 and 0 bytes | Checksum and terminator. |

## PF3 aggregate, not EDSDK state

No record `0x0115` exists in these PF3 bodies. The parser exposes a synthesized
32-byte PF3 property `0x00000115`. Six separate scratch-file mutations plus one
aggregate mutation confirmed these relationships:

| PF3 API aggregate offset | File record | Corrected meaning (2026-10-05) |
| --- | --- | --- |
| 0 | `1031` | Contrast |
| 4 | `1030` | Sharpness Strength |
| 8 | `1032` | Saturation |
| 12 | `1033` | Color Tone |
| 24 | `1034` | Fineness |
| 28 | `1035` | Threshold |

Aggregate offsets 16 and 20 remain zero in these tests; no broader meaning is claimed.
The earlier application labels for offsets0/4 were inverted. Stock compiler
sweeps preserve signed-4..+4 for1031 but clamp negative1030 to unsigned7;
omission experiments expose sharpness defaults at aggregate offset4. The editor
writer/parser now use the corrected mapping. Canon serialization verifies all
six intended values on five existing private bases. See PF3_BASIC_NATIVE_FIELDS_20261004.md.
This has no bearing on the EDSDK camera-registration `0x00000115` binary control
blob, which remains untouched.

## Actual conversion code location

Observed after Canon initialization, rather than inferred solely from file strings:

| EdsCFParse callback slot RVA | Effective MLib.dll target RVA |
| --- | --- |
| `d11d4` | `1bd30` |
| `d11d8` | `1c190` |
| `d11dc` | `1b670` |

`MLib+1b670` is a ten-instruction wrapper that forwards to `MLib+196a0`.
Bounded direct-branch analysis found 1630 reachable instructions in that converter;
the arithmetic and stage semantics have **not** yet been translated or independently
reimplemented. The other two targets have 201 reachable instructions each and call
`11220` and `14bd0`, respectively. Raw disassembly windows are explicitly marked
as windows, not complete/proven function boundaries.

## Next investigation

1. Follow `MLib+196a0`, `11220`, `14bd0` and their helpers: channel ordering,
   interpolation, fixed-point scaling, profile composition, clamping and rounding.
2. Trace controlled single-field changes to the compact matrices, curves and
   nested parameter structures; correlate effects with compiler intermediates.
3. Map serialized records separately from derived 10-node/17-node/full33 camera
   representations. Do not treat camera payload blocks as literal PF3 records.
4. Test other bases and format/DLL revisions before generalizing this schema.

Evidence stays under workspace `tmp/PF3_BLOCK_RESEARCH_20261004` and
`tmp/PF3_BASIC_RESEARCH_20261004`. Private decoded buffers and scratch PF3s are
research fixtures, not public release assets. Production exporter still uses Canon.
