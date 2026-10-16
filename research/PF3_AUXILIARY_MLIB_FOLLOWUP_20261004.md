# PF3 / MLib follow-up — isolated research

No camera session, production transport change, DLL patch, build or release.

## Evidence

Compared all twelve previously decoded 1300D PF3 vectors. Only records `1002`
(name), `1070`, `1071` and `fffe` vary. All remaining observed records are constant
in this dataset; this does not prove that they are irrelevant for other styles.

`1008` is structurally a nested BE TLV stream: record `0010`, type 4, 440 bytes,
followed by the exact eight-byte terminator. Its 110 words comprise header `[6,6]`
and six groups of 18 words. Candidate signed 16.16 interpretation yields central
values 0,60,120,180,240,300 and neighbouring limits -30/30,30/90,...,270/330,
alongside 50/100 values. This strongly suggests six colour sectors, but individual
field semantics and their effect on compilation remain unvalidated. Do not wire
these fields into production UI based on this structural hypothesis alone.

Expanded static analysis of observed MLib callbacks into twelve direct callees,
including `11220` (1742 reachable instructions) and `14bd0` (1256).
`196a0` explicitly distinguishes destination counts 9 and 10. For count 10 it
uses 32 and 255 constants; count 9 uses 40 and 320; the other branch references
256, 255.75 and 0.9990234375. These are branch operands, not yet a complete
sampling formula. Floating-to-integer truncation instructions occur at several
stages, so substituting a generic rounding rule is unsafe.

Before that conversion, `f490` receives three structures separated by 100 bytes.
It reads a count and pairs of unsigned 32-bit values, normalizes the coordinates
by the last pair, and builds a helper representation. This is consistent with
curve preparation, not proof of which serialized curve corresponds to each input.

Referenced non-executable qwords also include familiar transfer/matrix constants
(0.0031308, 12.92, 2.4, 0.2126, 0.7152, 0.0722). Their presence alone does not
identify the active colour-space branch or prove sRGB semantics for every call.

## Next experiments

1. Observe actual arguments/results at the three converter callbacks in an isolated
   compiler process and correlate the 100-byte curve inputs with PF3 getters.
2. Change one nested-sector field in a Canon-serialized scratch clone, compare
   intermediates and original/corrected output; never write to a camera for this.
3. Repeat single-field experiments for `1021/1029` and the three curve records.
4. Translate interpolation/quantization only after those observations establish
   layouts; compare against all twelve independent vectors and both table indices.

Private evidence: `tmp/PF3_BLOCK_RESEARCH_20261004/AUXILIARY_COMPARISON.json`
and `MLIB_CALLEES.json`. These and decoded buffers are not distribution assets.

## Controlled stock-compiler experiments

Canon-serialized copies of `01_IDENTITY.pf3`, one field changed per copy.
No compiler correction or camera access. Recorded RP and R8 descriptors are
inputs, not simulations of actual camera firmware. R8_VERIFIED additionally
checks every serialized property and refuses unrelated field changes.

| Change | RP changed bytes / 16752 | R8 changed bytes / 83076 |
| --- | ---: | ---: |
| `1008` candidate first-sector centre 0 to 10 in signed 16.16 | 0 | 0 |
| `1019` last curve ordinate 255 to 230 | 14712 | 76920 |
| `1018` last curve ordinate 255 to 230 | 12527 | 71318 |
| `1065` last curve ordinate 255 to 230 | 13597 | 75084 |

All outputs retain their baseline size and all compiler calls succeed. Comparison
is of encoded payload bytes; counts are not pixel differences or effect strength.
The curve records causally affect stock compilation. Their channel/stage mapping
is still unresolved. The single nested-sector mutation has no observable effect
in these two tested stock paths, not proof that the entire nested record is unused.

Evidence: `tmp/PF3_FIELD_EXPERIMENTS_20261004/{RP,R8,R8_VERIFIED}/FIELD_EXPERIMENTS.json`.
Research runner refuses existing scratch paths, hashes inputs/DLL/descriptor and
checks compiler errors. Existing production export and camera transport unchanged.

## Read-only MLib curve tracing

Four isolated stock R8 compiles, baseline plus each curve mutation. MLib hash and
actual loaded path checked before fixed-RVA observation. The first exploratory
trace saturated its shared 256-event cap with initialization calls; it is not
evidence of missing later calls. The bounded/order reruns count functions
independently and capture only initialized curve count/pairs (not stack tails).

Each compile calls `f490` 9045 times. Baseline includes 27 default curves ending
at (300,300) and 9018 curves ending at (255,255). Each mutation produces exactly
1002 preparations ending at (255,230), and 8016 unchanged (255,255) preparations.
First changed call indices: `1018`=10/28/46/55; `1019`=13/31/49/58;
`1065`=16/34/52/61. This establishes distinct positions within repeated nine-call
groups, not their RGB identity. No `196a0` calls occur in these stock R8 compiles.

The observed compiler payload hashes remain useful for comparison to unobserved
runs, but no physical camera result is inferred. Next: follow the callers of
`f490` in this active path rather than assuming `196a0` is used, establish which
three-curve groups correspond to each stage, then map mathematical channels.

Evidence: `tmp/PF3_FIELD_EXPERIMENTS_20261004/R8_CURVE_TRACE_ORDER.json`.
