# Canon PF3 reverse-engineering summary

This is an offline research summary of the work and evidence under `research/`
and the private `tmp/PF3_FIELD_EXPERIMENTS_20261004` directory. The DLLs were
used read-only. No camera session, EDSDK registration, production compiler
patch, UI change, build, or release was performed during this research.

## What the evidence establishes

- One installed x86 Canon compiler revision was tested against 87 recorded EOS
  IDs and one recorded R8 descriptor. 73 virtual offline compiles succeeded,
  14 returned errors. They exercise nine routes with output sizes 8,528,
  16,720, 16,744, 16,752, 78,980, 83,076, and 431,616 bytes. This is a map of
  that compiler's behavior for those exact inputs, not proof of each camera's
  own descriptor, firmware support, physical acceptance, or safe installation.
- The best-established path is not to fabricate a camera payload. Starting
  from a suitable Canon PF3, the installed Canon compiler often produces a
  family-shaped output from edited PF3 fields. Its result must be checked for
  that route; equal return code or byte length alone does not prove a LUT was
  applied.
- PF3 `0x1023` and `0x102b` are structured kind-1 selective-color group lists.
  An empty list is the eight-byte `(kind=1,count=0)` header. Complete
  four/five-point groups alter compiled output. Editing a count without the
  full variable-length group data can crash the isolated compiler.
- On tested modern paths, `0x1023` feeds one selector profile and `0x102b`
  another. A bounded independent reference verifies 24/24 17-node variants
  and 8/8 full33 variants through their final output blocks.
- On the compact path, an extra per-pixel route through `EdsCFParse 0x475c0`
  and `MLib 0x1cab0` explains why earlier sampled grids appeared unchanged
  when selectors changed. A separate pixel reference now reproduces native
  results and packed payload blocks.
- The compact reference passes 48/48 selector contexts (48,000 pixels) and
  the 5DS scale-255 branch passes 8/8 contexts (8,000 pixels). Additional
  non-neutral stock PF3 checks pass 8/8 matrix, 20/20 nonlinear-curve, and
  24/24 axis contexts with final packed bytes exact.
- Direct bounded replay exercised 84 contexts and requested 15,808 samples.
  With the explicit research-only selector margin 0.25, 15,794 samples passed
  at max error `1.15e-14`; 14 were rejected before calling native code because
  they would index before the cached curve buffer. None are silently clipped
  or counted as successful. A fresh rerun of the 0.25 case is in
  `COMPACT_PIXEL_DIRECT_MARGIN025_RECHECK_20261005.json`.
- Curves, polynomial transform, six color axes, fixed/float RGB/Lab conversion,
  9/10/17/33-node resampling, and compact/17/full33 final packing have
  independent bounded references. Native floating operation order matters:
  one-ULP differences can change integer truncation and final bytes.
- Six existing base-style fixtures (Neutral, Standard, Portrait, Landscape,
  Faithful, Fine Detail) produced distinct overall outputs in three tested
  routes. Fine Detail carries base selector `0x0088`; its native blocks differ
  from Neutral in compact 16,752-byte, modern 83,076-byte, and full33
  431,616-byte virtual compiler outputs. The five-style block-sharing findings
  still apply: one shared block does not mean a base style was ignored.
- The Fine Detail source fixture compiled successfully via the recorded
  compact, modern17, and full33 routes. This validates local compiler
  transformation only; it does not prove camera installation or in-camera
  appearance. Its source/payload hashes and block comparison are in the private
  `tmp/PF3_FIELD_EXPERIMENTS_20261004/FINE_DETAIL_BASE_STYLE_20261005/`
  outputs.
- An expanded six-style × nine-route matrix produced 44 strict passes out of
  54 virtual cases. The 10 flagged cells split into six `rcGet=1` cases
  (Faithful/Landscape on M3, 450D, and 7D Mark II; the 10-node validator saw
  only output index 1) and four Fine Detail cases where `rcId=7` prevented
  target-ID validation on M3, 1D Mark III, 450D, and 7D Mark II. Those four
  nevertheless returned a carrier and the observer identified a legacy-direct
  compiler route; they remain unvalidated, not proven camera incompatibilities.
  The other 44 cases passed both the PF3 API calls and route acceptance check.
  All remain virtual runs against one recorded R8 descriptor.
- Descriptor sensitivity explains why those ten cannot be called model
  incompatibilities. On M3, changing only the descriptor from the recorded R8
  15,076-byte fixture to the recorded 1300D 7,772-byte fixture made
  Faithful/Landscape pass and Standard fail; with the latter descriptor, M3
  and 1300D virtual IDs had identical pass/fail states for those tested styles,
  and identical whole-payload hashes for Neutral, Faithful, and Landscape.
  This shows descriptor-dependent route selection in these tests, not that
  either fixture is the M3's real descriptor.
- A second six-style × nine-route sweep with the 1300D descriptor gave 35/54
  strict passes. R5 and 1D X Mark III failed all six styles with `rcGet=81`
  (they passed all six with the R8 descriptor); that 7,772-byte descriptor is
  not a valid proxy for those modern routes. On M3, 450D, and 7D Mark II,
  Standard failed while Faithful/Landscape passed—the opposite pattern from
  several R8-descriptor cells. This is direct evidence that a borrowed
  descriptor can invert route/style results or make a route fail entirely.
- The detailed `rcGet=81` trace shows R5 produced only 10-node index 1 and no
  modern17 builder; 1D X Mark III used an `unvalidated-no-grid-conversion`
  path and no grid builder. The shorter fixture does not exercise their
  observed modern routes; the rc value alone does not identify its exact cause.
- For the four old IDs whose Fine Detail (`0x1009=0x0088`) case returned
  `rcId=7`, scratch-only replacement of that one selector with Neutral
  (`0x0084`) changed the result to `rcId=0` and a validated direct carrier on
  M3, 1D Mark III, 450D, and 7D Mark II. This strongly ties the failure to the
  Fine Detail selector/base-ID path on those virtual inputs; it does not
  establish physical body capability.
- Repeating the original `0x0088` Fine Detail fixture with either the R8 or
  1300D descriptor kept `rcId=7` on M3, 1300D, 450D, 1D Mark III, and 7D Mark
  II. M3's output hash was identical across both descriptors; the other IDs
  also produced their direct legacy-size carrier, but remained target-ID
  unvalidated. This strengthens the evidence that Fine Detail selection is
  unsupported by these specific virtual ID/selector paths, rather than caused
  by descriptor size. Do not silently replace the requested style with Neutral.
- Replacing Faithful's `0x1070`, `0x1071`, `0x1021`, or `0x1029` individually
  (or the two table / matrix pairs together) with Neutral's values did not
  clear the M3/R8-descriptor `rcGet=1`. Those fields are not sufficient to
  explain that partial 10-node build.
- Two archived Fine Detail PF3 variants have the same selector `0x0088` and
  28 records but are not byte-equivalent: 15 records differ, including both
  33³ tables and the selective-color group records. Treat the older original
  Canon fixture and the generated cache as distinct assets; do not substitute
  one for the other without verifying provenance and intended use.
- A scratch-only Canon-serialized experiment changed generated-cache Fine
  Detail's empty `0x1023` and `0x102b` records from all-zero bytes to Canon's
  explicit empty kind-1/count-0 header. The compact, modern17, and full33
  compiled output hashes were unchanged. For these empty-list variants, the
  tested routes treat the encodings equivalently; this says nothing about
  nonempty selector groups.
- The 1300D fixture comparison found only a small set of varying records in
  those twelve files. That sample does not establish that other records are
  globally irrelevant.
- The 14 repeatable `rc=80` failures divide into two specific compiler-side
  failures: 10 older IDs cannot read derived `0x1022/0x102a` 4096-byte nodes;
  four (`5D`, `1D II N`, `30D`, `400D`) cannot read the 1460-byte `0x1007`
  legacy field. These are compiler input/materialization errors under the
  recorded descriptor, not evidence of those cameras rejecting a registration.
  Testing PF2 inputs and synthesizing zero/FF `0x1007` showed the old field is
  passed through into 1,460 carrier bytes. Such made-up data is diagnostic only
  and does not produce a validated style.
- A byte comparison of archived EOS RP and R8 descriptors found both are
  15,076 bytes, but their SHA-256 hashes differ (`2bff34bc...aec60` vs
  `27c73781...65642`) and 1,415 bytes differ (9.386%). Thus equal descriptor
  length is not a shared descriptor schema/value set; the bytes are
  camera/session-specific inputs. This makes descriptor sensitivity a
  concrete reason that virtual tests with a borrowed descriptor cannot stand
  in for the target body's actual transaction data. The comparison is
  private research data and does not identify the semantic meaning of each
  changed field.
- An archived EOS R8 install report records a live camera ID `87040080`, the
  same 15,076-byte R8 descriptor hash above, an 83,076-byte incoming carrier,
  and an outgoing patched carrier where PF3 regions `0x1f00`, `0x1022`, and
  `0x1f02` were modified. The report says registration returned `rc=0`,
  `patched=true`, and the user reported “The Aerochrome look is correct.” This
  is valuable physical evidence for that R8 test and that payload/slot, but
  not proof for every R8, every firmware, every 83,076-byte route, or all
  Canon families. It should be kept distinct from virtual compiler success.
- Audit of the current-workspace install reports found an important logging
  distinction: `fixtureHashes.descriptor` is the bundled 1300D descriptor
  fixture hash (`649693d6...b3f0`), confirmed byte-for-byte against
  `camera_support/.../1300D_DESCRIPTOR_7772.bin`; it is not the live descriptor
  hash. The reports record live descriptor length (15,076) and camera ID, but
  mark `descriptorStored=false` and do not log a live descriptor hash. The
  report's `familyStatus` string is therefore not itself proof that both RP
  and 1300D were physically validated by that transaction. The current local
  reports show live ID `33040080` (RP); use separate physical evidence for any
  1300D claim. This also means the earlier RP-v-R8 byte comparison comes from
  separate archived captures, not these install report fixture hashes.
- There are five complete `SUCCESS` install reports in this checkout. All five
  record live camera ID `33040080`, native/outgoing size 16,752, `rc=0`, and
  `patched=true`; all leave `0x115` unchanged. They document repeated successful
  style registrations on the same RP, not five camera models. Their common
  descriptor *fixture hash* must not be misread as five live descriptor hashes.
- The standalone build manifest labels `EOS 1300D / 16744`, `EOS RP / 16752`,
  and `EOS R8 / 83076` as **offline** validated transactions and separately
  sets `physical_revalidation_required=true`. The 1300D evidence found in the
  release notes is a 12-vector compiler-reference matrix, not a physical
  camera-install report in this checkout. The wording should not be summarized
  as “three bodies physically validated.”

## Route map (virtual offline compiler output)

| Output size | Recorded route count | Observed path notes |
| ---: | ---: | --- |
| 8,528 | 3 | Compact/legacy representation |
| 16,720 | 4 | Direct compact-like representation |
| 16,744 | 23 | Legacy direct; tested controls may be baked or ignored |
| 16,752 | 3 direct + 24 resampled + 2 5DS | Several distinct paths share this size |
| 78,980 | 1 | Compact and modern stages both observed |
| 83,076 | 10 | Compact representation appended to modern output |
| 431,616 | 3 | Full33 tables |

Counts are per recorded EOS IDs in the fixture, not counts of all Canon bodies
or proof of physical compatibility.

## Still unknown / next investigations

Follow-up locates the initialization gate at `53b40`: ten old IDs return
before derived-record creation; four take a legacy list that includes the
empty `1007`; the other 73 baseline IDs take the common list. The extracted
table agrees with 87/87 recorded baseline outcomes. Exported reflection did
not resolve the failures in 24 controlled compiles with PF2/PF3 and two
descriptors. The broader survey now fully decodes all 231 unique archive
sources (660 files) after recognizing the PF2 `2001` zero trailing word and
PF3 high-bit `90xx` record variants. No serialized `1007` was found. 220 source
checksums match, five are absent, and six mismatch; structural decoding does
not certify those six sources' integrity. The `90xx` records preserve distinct
values from their `10xx` counterparts and are retained separately.
Details and exact limits are in the legacy failure map below.

1. Determine each route's complete PF3 field dependencies and what makes some
   older stock routes ignore table edits. Trace property getters/setters and
   the default/base PF3 selection logic across every route, with controlled
   one-field fixtures.
2. Obtain genuine descriptors for the affected bodies and explain the six
   incomplete 10-node builds; do not infer model limits from the shared R8
  descriptor. Map which exact PF3 property causes partial conversion and
  capture the real descriptors from actual bodies before evaluating support.
3. Repeat the known-size and base-style matrix on remaining identity PF3
   fixtures and verify each final payload block independently.
4. Keep reversing the older `rc=80`, failing, and unmapped branches in fresh
  isolated compiler hosts. Separate a compiler crash/error from camera-body
  incompatibility.
5. Examine the full33 and modern17 record selection/packing branches and any
  route not yet represented by a verified reference. Keep truncation,
  endpoint, negative-index and integer overflow domains explicit.
6. Physical camera registration and in-camera rendering remain the final
   evidence for installation behavior. Offline compilation cannot simulate
   unknown camera descriptors or firmware responses.
7. Compare the RP/R8 descriptor fields against repeated captures from the
   same body and across slots/firmware before assigning meaning to changed
   bytes; keep session-varying and model-varying fields separate.

The older-branch failure breakdown and further PF2 comparisons are detailed in
[PF3_LEGACY_FAILURE_MAP_20261005.md](PF3_LEGACY_FAILURE_MAP_20261005.md).

The complete detailed work log is [MLIB_COLOR_GRID_PROGRESS_20261004.md](MLIB_COLOR_GRID_PROGRESS_20261004.md), with separate route and auxiliary
PF3 notes in the adjacent research files. Private Canon-derived inputs and
payload captures stay in the private research directory and must not enter a
public release.
