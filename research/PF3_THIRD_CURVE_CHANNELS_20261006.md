# Curve1065 channel sensitivity — private compiler evidence

Correction: the historical experiment name said "THIRD_CURVE", but native
initialized arguments show1065 changes `postCurvesHex`, not `thirdCurvesHex`.
It is the post-RGB curve group. The original run names remain intact for audit.

Exact-known EdsCFParse/MLib revisions, own hidden x86 laboratory host only.
No camera session, installed DLL patch, EOS Utility attachment or public assets.

Source: archived `01_IDENTITY.pf3`. The 300-byte1065 record contains three
100-byte two-point identity curves. Independently change only one endpoint
from255 to230, leaving the other two curves and every other source record
unchanged. Canon serializes each scratch file; API readback and independent
decoded records confirm only1065 changes.

Private evidence: `THIRD_CURVE_CHANNELS_FULL33_20261006/FIELD_EXPERIMENTS.json`
under the private field-experiment root. Recorded C50 ID40000227, shared R8
descriptor; all create/ID/descriptor/size/get gates succeed,431616-byte output.

| Modified1065 channel | Changed native payload bytes |
| --- | ---: |
| 0 | 141201 |
| 1 | 141042 |
| 2 | 137185 |

The positive channel0 control and both other channels affect the full33 output.
This demonstrates post-RGB channel sensitivity, not chromatic Lab curves.
The existing guard against nonidentity Lab-group channel1/2 remains justified
as an unmapped case; this run does not exercise those guarded channels.

Next: independently identify1018/1019/1065 native parameter placement and replay
the captured outputs. No physical camera compatibility claim follows.

Generator regression tests and py_compile pass; full suite278 passing.

## Corrected native placement and independent replay — 2026-10-07

Nine single-channel mutations across1018/1019/1065, each captured in both
native modes, establish placement from actual initialized arguments:

| PF3 record | Native argument group | Changed output bytes by channel0/1/2 |
| --- | --- | --- |
| 1018 | preCurvesHex | 223168 / 243769 / 228273 |
| 1065 | postCurvesHex | 141201 / 141042 / 137185 |
| 1019 | thirdCurvesHex | 411703 / 0 / 0 |

Both1019 channel1/2 outputs have exactly the baseline SHA256, not merely zero
differences over a prefix. These two mutations are unused in this particular
full33 output path; do not generalize to every other context or family.
NativeMLib11220 disassembly corroborates luminance-only use: float RGB→XYZ
at11bdd, XYZ→Lab at11c04, the cached curve evaluator1de30 at11c24 for the
L component, then Lab→XYZ at11c5b and XYZ→RGB at11c83. This is separate
from the three-channel pre/post evaluator1dd50 calls.

`curve_stage_research` checks initialized curve sizes, native API gates,
single-field serialization and consistent slot placement in both captures;
it does not infer stages from source filenames or historical labels.
Private slot proofs are `${EXPERIMENT_DIRECTORY}_SLOT_PROOF.json` for the
original1065 run and `CURVE_CHANNELS_0x1018_FULL33_20261006` /
`CURVE_CHANNELS_0x1019_FULL33_20261006`.

Independent replay results:

- `CURVE1065_CHANNELS_INDEPENDENT_FULL33_20261006.json`: all6 captures exact.
- `CURVE1018_CHANNELS_INDEPENDENT_FULL33_20261007.json`: all6 captures exact.
- `CURVE1019_LUMINANCE_INDEPENDENT_FULL33_20261007.json`: both captures exact.

Each comparison covers35937 nodes×3 components and final packed bytes at the
actual native payload offset (372 or215994), with zero numeric mismatch.
The1019 comparison explicitly selects channel0 only; channel1/2 are not
claimed by the independent replay. Their nonidentity guard remains intact.
New `--case-name` emits selectedCaseName in the report and rejects missing
or duplicate names.282 tests and py_compile pass. Production UI/RAW/export
paths were not modified.

## Shared11220 third-group behavior:17-node and full33

New private stock compilation `CURVE1019_R8_20261007` uses the same identity
source and recorded descriptor with R8 ID80000487. All three mutations pass;
channel0 changes76920 bytes in the83076-byte payload, while channel1/2 match
the complete baseline SHA256. Slot proof confirms1019 enters `thirdCurvesHex`
in both native modes, just as in the full33 captures.

Research-only opt-in `--experimental-unused-third-channels` allows the
independent11220 model to normalize but not apply third-group channels1/2.
Without explicit opt-in the old unsupported-case guard remains unchanged.
The flag is saved in the final report; this is not a universal PF3/camera rule.

Both private independent reports ending `_INDEPENDENT_UNUSED_CHANNELS_20261007.json`
cover three channel mutations×two modes. Full33: six grids,zero numeric
mismatch, final packed payload regions exact.17-node: six grids, max numeric
error2.161e-12, below1e-10 comparison tolerance,zero mismatched nodes; packed
bytes match the appropriate final native blocks. This supports the modeled
luminance-only use for these tested11220 paths, not every Canon context.

283 automated tests and py_compile pass. No production processing change.

## Ten-class1019 sensitivity matrix

Private `CURVE1019_TEN_CLASSES_20261007/HIGH_BANK_RESULTS.json` covers40
stock compiles: identity and three separately Canon-serialized channel changes
against one representative of each of the ten native classes. Driver verifies
all original input hashes remain unchanged. SummaryV2 is produced by
`curve_family_sensitivity`; failed groups cannot be counted as equal outputs.

- Classes1/2: all four sources fail; no sensitivity conclusion.
- Classes3/4/5/6: all four native output hashes equal their route baseline.
- Classes7/8/9/10: channel0 differs; channels1/2 equal the full baseline hash.

Read-only record lookup observations corroborate the boundary: classes3–6
do not look up1019 at the observed lookup paths during compilation, while
classes7–10 do. Classes3–7 prepare dense source1070/1071 during ID setting;
classes7–10 subsequently generate modern tables during output. This is
consistent with the previously mapped dense-versus-polynomial selection,
not evidence that the ignored serialized curve was rejected or corrupted.

The class6 7DII and class7 M50 both emit16752 bytes but have different1019
sensitivity. Payload size alone therefore cannot identify full processing
semantics. These are representative ID/source/shared-descriptor combinations,
not a claim covering every ID in a class or physical camera behavior.

286 tests and py_compile pass. No installer or application processing change.
