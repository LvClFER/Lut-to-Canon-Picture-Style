# Observed Canon compiler routes and independent curve translation

Scope: installed x86 EdsCFParse 3.20.20.0 / MLib hash `a36f3cea...922a`,
87 recorded EOS IDs, identity Neutral PF3 and recorded R8 descriptor. No camera
sessions, no EDSDK, no compiler acceptance correction. Model IDs plus one recorded
descriptor establish compiler behavior for those exact inputs, not each body's
actual descriptor, firmware support or camera acceptance.

## Complete baseline run

87 attempted, 73 compiled, 14 returned errors. Nine observed stock routes:

| Payload bytes | Models | Converter `196a0` | `14bd0` calls | `11220` calls |
| --- | ---: | ---: | ---: | ---: |
| 16744 | 23 | 2 | 0 | 0 |
| 8528 | 3 | 2 | 0 | 0 |
| 16720 | 4 | 2 | 0 | 0 |
| 16752 direct | 3 | 2 | 0 | 0 |
| 16752 resampled | 24 | 2 | 4 | 0 |
| 16752 5DS/5DS R | 2 | 2 | 2 | 0 |
| 78980 | 1 | 0 | 2 | 2 |
| 83076 | 10 | 0 | 3 | 2 |
| 431616 | 3 | 0 | 0 | 2 |

All model names/IDs and failures remain in private `ALL_MODELS_MLIB_SUMMARY.json`.
The baseline observer was refined during the run (caller lookup caching and an
optional normalization observer for the last cases). Route grouping uses only
the common observed counters, not that optional counter. Later controlled runs
record the exact observer hash per case and hold it constant.

## Common curve machinery

`f490` accepts a count followed by uint32 X/Y pairs. It divides both axes by the
last X and prepares an X+1 sampling domain. Independent Python normalization
matches every captured input's float64 results byte-for-byte in 36 cases across
nine route representatives (baseline plus each of three scalar curve mutations).

Callers identified at `196a0`, `11220`, `14bd0` and `a7f0`. Modern callers prepare
nine curves in three groups. This is not yet a validated RGB/stage label mapping.
The three PF3 records are 300-byte structures; do not infer semantics from size.

Two-point sample generation matched byte-for-byte for every captured sample in
the four R8 baseline/single-field traces. For nonlinear curves, the independent
candidate is an interpolating order-3 (quadratic) B-spline. Its interior knot j
is `(X[j] + X[j+3])/2`, with three repeated endpoint knots. Adjacent-X average
knots failed at five and six points. Canon disassembly `1f450` confirms the
separated-X rule. Curves with 3/4 points matched every float64 Y byte; uneven 5
and zigzag 6 point curves match within 2.23e-16, not byte-exact.

`1df30` finalization applies, for each sample after the first: advance control-point
index once when normalized X exceeds the current point X; constrain Y using
previous sample, upper bound 1 and current control-point Y. A downward control
point can still lower the result, so calling it globally monotonic would be wrong.
The independent translation matches all 17 observed finalization cases byte-for-byte,
including 115, 88 and 138 changed samples in the nonmonotonic/uneven/zigzag curves.
These checks isolate finalization using captured pre-finalization samples; they
are not proof of a complete independent PF3-to-camera compiler.

## Stock path limitations

In the 36 single-field cases, curves change payload hashes for representatives of
five routes: resampled 16752, 5DS, 78980, 83076, 431616. They do not change payloads
for representatives of 16744, 8528, 16720 and direct 16752. Do not interpret
successful compilation or unchanged payload size as evidence arbitrary data was
included. Production compiler correction and export remain untouched.

## Remaining research

Map curve groups to stages/channels and all matrix/sector fields; independently
translate colour conversions, table interpolation and quantization; investigate
old failing branches separately; repeat across bases and real descriptors.
Physical acceptance and image appearance remain separate validation steps.

## Nine-route nonlinear replication

Completed 54 isolated stock compiles: nine route representatives times baseline
plus five 3/4/5/6-point nonlinear variants, using one constant observer revision.
54/54 normalization checks passed. All 108 distinct observed finalizations match
the independent translation byte-for-byte. In the five routes that consume the
modified curves, all 25 nonlinear spline checks pass: 15 float64-byte-exact
(3/4 points) and 10 within 2.23e-16 (5/6 points). The four other routes only expose
their default curves, and all five nonlinear variants leave their payload hashes
unchanged. Do not count those as successful arbitrary-curve incorporation.

Evidence: `NINE_ROUTES_NONLINEAR_TRACE.json`,
`NINE_ROUTES_NONLINEAR_NORMALIZATION.json`, `NINE_ROUTES_NONLINEAR_SPLINE.json`,
`NINE_ROUTES_NONLINEAR_FINALIZATION.json`, `NINE_ROUTES_NONLINEAR_SENSITIVITY.json`.
Research unit tests: 44 passed. Application regression suite: 31 run, 7 skipped
for unavailable fixtures/runtime dependencies, remaining tests passed.

Private evidence is under `tmp/PF3_FIELD_EXPERIMENTS_20261004`, including
`ALL_MODELS_MLIB_TRACE.json`, `ALL_MODELS_MLIB_SUMMARY.json`,
`NINE_ROUTES_CURVE_TRACE.json`, `NINE_ROUTES_NORMALIZATION_CHECK.json`,
`NONLINEAR5_R8`, and `R8_FINALIZATION_CHECK.json`. Do not package these captures,
scratch PF3s or Canon-derived resources into public releases.
