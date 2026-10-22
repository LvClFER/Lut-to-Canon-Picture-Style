# Independent registration integration checkpoint

This is offline evidence, not a standalone release or camera validation.

Implemented linkage:

- Strict version3000 PF3 reader with caller-supplied cipher tables: exact
  envelope, typed host conversion, uniqueness, checksum and termination.
- Explicit compact16752 cache compilation from both dense source records.
  Normal parameter-based full33 is excluded because it ignores arbitrary
  dense LUTs. No automatic model/route guessing is introduced.
- Native-shape wire plan and9189 content comparison, excluding the desktop
  caption. Content equality does not prove freshness, slot or visual output.
- WPD no-data/data-phase senders for an explicitly supplied COM device.
  No COM initialization, enumeration or device open occurs on construction.
  Caller owns apartment/device lifetime. Writes are disabled by default.
- Linked compiler/controllers/COM-marshalling test with fake COM, five write
  chunks and one read chunk. Partial acknowledgement terminates once without
  retry or attempted readback. This does not model the registration state.

Evidence:

-12 source files decoded to exactly the same host records as prior reference.
-12 whole cache-route carriers match archived native output,201024 bytes.
  Report: workspace tmp/PF3_FIELD_EXPERIMENTS_20261004/
  INTEGRATED_COMPACT_SOURCE_20261011.json. This uses a borrowed descriptor
  archive; it is not physical7DII or RP support evidence.
-Isolated interpreter executes integrated compact path while imports of
  compiler_regression, virtual_compatibility and Frida are blocked.
-577 tests pass; changed modules compile. No Canon DLL execution or camera
  access occurred. Archive comparison setup still reads keys from local DLL.

Remaining before a real independent build:

1. Independent cipher bootstrap/derivation; do not embed local Canon tables.
2. Establish correct route from actual negotiated camera data, including RP;
   explicit offline route selection is not an automatic family registry.
3. Own Windows COM session lifecycle and complete Canon event/state sequence.
4. Obtain fresh opaque registration state; never replay captured115 buffers.
5. Confirm operation ordering, write, fresh readback and actual image result
   under separately authorized physical tests. UI/fallback remain unchanged.

Do not replace these requirements with green synthetic tests or rc=0.

## Physical Windows session checkpoint — 2026-10-16

The corrected WPD transport has now completed the authorized diagnostic on a
physical EOS RP without executing Canon components: own Open/capabilities,
remote/event enable, completed event data transfer, remote/event disable and
Close. The command12 IOCTL access mismatch was corrected in the shared
marshaller; control access at Open remains separate from style-data write
permission. Both the integrated sender and older opt-in probes use the fix.

The startup batch yielded12816 event bytes, D116=80000433 and slot handlers
21/22/23. No D17F descriptor was observed. This establishes physical session
communication, not route selection or freshness of registration control.
No style was sent, no camera bytes retained and no new build published.
See `RP_INDEPENDENT_SESSION_20261011.md` for evidence and remaining boundaries.

The independent cipher bootstrap remains unresolved; PF3 preparation still
requires externally supplied keys. The editor's independent mode remains off,
its Canon fallback is untouched, and RAW/DPP independence remains unresolved.
System-COM marshalling, malformed/optional response handling and the control
versus style-write boundary are covered by regression tests.

Follow-up: explicit9127 requests now physically retrieve the RP's D17F
descriptor and D170 slot1 style through the same session/COM adapters.
`RP_LIVE_INPUTS_20261016.md` records the completed reads and their boundaries.
Actual DeviceInfo does not advertise9189/9192/918a; do not interpret the existing
synthetic9189 comparison as a working RP confirmation route. D170 event content
can be acquired, but post-write freshness and visual LUT acceptance remain
unproven. The cipher checksum experiment described in
`CIPHER_DEPENDENCY_20261011.md` reconstructs a candidate without reading a DLL,
under explicit archive-layout assumptions; it is not an editor bootstrap yet.

## Archived registration order

The RP V25 log contains five complete, nonoverlapping EDSDK triplets with
paired successful returns and the same explicit handler21:

114(4bytes) ->01000203(16752bytes) ->115(32bytes).

This establishes upper API call order in that recording. The115 state write
follows completed payload submission; it must not be blindly placed before
the payload because it is called a state/control blob.114 is a distinct
selector/cache operation whose wire behavior requires separate attribution.
Neither control contents nor captured state are replayed by this analysis.

The1300D V32 log has overlapping/unpaired attribution at this granularity;
the analyzer refuses to infer ordered transactions from it without thread or
call identity. This is missing ordering evidence, not a camera failure.
Report: private lab REGISTRATION_CALL_ORDER_20261011.json. No DLL execution,
device access, binary copies or proprietary byte output.

## Post-attempt checkpoint — 2026-10-16

One explicitly authorized Classic_Cuban_Neg/User Def.3 experiment reached a WPD
data-phase completion timeout80070079; temporary-mode cleanup also failed. It
was not retried. After user power/USB recovery, a new own-transport D172 session
returned exactly the original baseline style hash and completed both cleanups.
There is no confirmed style change, compiler-route acceptance or visual result;
the editor's independent mode stays off. The private style backup is intact and
excludes opaque115 state. See `RP_LIVE_INPUTS_20261016.md` for the evidence.

The strengthened cipher experiment now reconstructs a unique candidate using
automatic envelope/length corpus selection, structural-majority nibbles and
checksum alternatives per explicit schema.232 files validate,111 held out;
no Canon DLL is read/executed and no recovered table is persisted. This removes
manual representative choice for this corpus, but still requires the18 known
schemas and sufficient user-supplied encrypted data; single arbitrary-file
bootstrap, editor integration and packaging are not established. Details and
negative generator hypotheses are in `CIPHER_DEPENDENCY_20261011.md`.

All615 discovered tests pass after the content-free registration-phase exception
notes. No additional camera writes, fallback changes, RAW/DPP replacement or
new build/publication occurred. The full objective remains incomplete.

## Err70 supersedes transport-only success

A separately authorized single unchanged-style transfer subsequently returned
PTP2001 and identical requested D172 content, then failed temporary-mode
cleanup. The user reported Err70 and later confirmed normal startup without
USB after power/battery recovery. All device access stopped; no post-recovery
slot read, restore or additional write occurred. Both private experimental
write flags are now blocked before device access. Transport completion did
not establish safe camera acceptance.

Offline Windows IWpdSerializer decoding/roundtrip of all39 archived V25 input
buffers exposed four complete UI-lock/style/state/UI-unlock cycles missing
from the injected executor. It now requires a command adapter and follows the
observed911B(1)/911C() boundary with one release attempt on failures.616 tests
pass, including fake-COM order and failure handling. The missing boundary is
established; its relationship to Err70 and the revised physical flow are not.
`RP_LIVE_INPUTS_20261016.md` contains exact scope and metadata report names.
The editor mode/build gate stays closed and the goal remains incomplete.

## Portable identity calibration checkpoint

The cipher dependency now has a standard-library implementation using a single
supplied mathematical-identity PF3: `identity_pf3_bootstrap_reference` locates a
known-plaintext record by a key-independent XOR rectangle, reconstructs an
equivalent stream and validates the complete file, checksum and identity table.
It uses no Canon runtime, embedded tables, position manifest, solver or device.
The private proof validates137 PF3s with131 outside the6 calibration files and
reproduces all8 current experimental carrier compilations.622 tests pass.

The editor's six existing runtime-generated base files also independently pass
this bootstrap. They can supply the reference locally without asking the user
for an additional file in this restored project. They were previously created
with Canon serialization; this does not make the whole workflow asset-free on
a fresh machine. No such PF3 is bundled by the new code and no recovered keys
are persisted. The existing GUI still uses its Canon paths: binding this core
to the existing base/export/install flow is outstanding. An arbitrary modified
PF3 such as Classic_Cuban_Neg is not itself a validated calibration source.

All RP access remains stopped after Err70 and user-confirmed normal boot. The
revised UI-lock protocol, compiler route, post-registration freshness and image
result still require review and explicitly authorized physical validation.

## Editor PF3 generation and export checkpoint

The existing editor now has a portable PF3 read/write path when EdsCFParse is
unavailable. The writer constructs the typed records, checksum and encrypted
envelope itself. Base generation builds the six styles from
`generated_pf3_properties`, rather than copying the fields of a prior template.
The existing local identity PF3 is used only to recover the cipher stream.
All six generated bases reproduce the existing434511-byte files exactly in an
offline check with EdsCFParse forbidden. No keys or PF3 assets were added to
the public package; its source allowlist includes the required portable modules.

The editor's base resolver can generate a missing selected style from another
local identity reference. Open-PF3, export, controls, LUT composition and working
preview use the portable reader when the DLL is absent. The Canon fallback
remains. Tests exercise synthetic cipher tables, six generated selectors,
changed Basic fields and an inverse LUT, reimport, failed atomic replacement,
and export through the existing Qt dialog with Canon discovery/parser disabled.
The full offline suite passes628 tests with the installed Qt dependencies.

This is not a clean-install independence claim: no identity PF3/reference still
means no portable cipher bootstrap. RAW/DPP replacement is also unresolved.
The native camera dialog and independent send gates are unchanged; all physical
access remains stopped after Err70. No executable build was produced.

## One editable file and one Documents folder

Following the user's storage requests, exports now default directly to the
system Documents folder, `Canon Style Studio PF3/`, with no per-style folders.
Existing names get a numbered filename. The existing `.canonstyleproject` ZIP
format now embeds the compiled PF3, source base, adjustments, LUT files and
snapshots; its manifest version2 still reads version1 archives and legacy JSON.
No external `.manifest.json` or `.canonstyle.json` is written. Plain PF3 export
remains available explicitly, and old PF3 files remain editable as baked bases.

The bundle may contain an identity PF3 generated from the recovered stream so
an imported nonidentity style can reopen without the old local cache. It does
not embed cipher tables in application code or remove the initial bootstrap
dependency when creating a style from nothing. Reference photos remain external.

The editor save/open actions and camera preparation use the same format.
Camera PF3 extraction and reports stay in internal logs, while the user-facing
folder receives only one style document. Physical transports and post-Err70
gates remain unchanged.635 offline tests pass, including removed original
assets, re-edit/re-export byte parity, an imported style carrying its own cipher
reference, redirected Windows Documents, naming collisions, legacy formats and
Qt save/reopen/preparation with the installer fully mocked. No new build or
camera access was performed.

Existing exports from the restored editor and the standalone export folders
were consolidated into10 distinct style documents in the new Documents folder
(13 original PF3 paths,10 unique hashes). Each bundle preserves the exact old
PF3 bytes and its Basic controls; baked LUT layers are explicitly not invented.
Every bundle was re-read with an empty runtime cache and EdsCFParse forbidden.
All original PF3s remain unchanged. The older standalone executable has not been
rebuilt and does not yet contain the new reader/UI.

## Bounded diagnostic and post-Err70 UI-lock cycle

The independent diagnostic now owns a child process. Parent waits are bounded
even after a termination request; cleanup remains unknown on timeout, crash or
interrupt. It never starts a replacement worker. The private worker report
contains metadata only, and numeric PTP command failures survive serialization.
The shared UI-lock context preserves the registration executor's original
failure and one-release policy. The diagnostic offers an explicit empty-cycle
test after both vendor and DeviceInfo capability checks.

After a new specific user authorization and confirmation that the RP was ready,
one45-second-deadline diagnostic was executed. Private report:
`RP_UI_LOCK_DIAGNOSTIC_20261016_01.json`. It completed normally, with911B(1)/911C(),
two requested D172 observations equal to the pre-Err70 baseline SHA256
`0c6086390683ab343936da8bf27be2f4c9ed78add8ba9d7fd63b2c3d39d820c9`,
both temporary-mode disables, connection close and worker exit0. No style or115
was written, no Canon runtime was loaded and no retry occurred. The user then
confirmed separately: "Sim, continua normal", without Err70 or a lockup.

This proves the empty UI-lock cycle on the recovered body, not the cause of
Err70 or safety of a complete style/state transfer. Previous experimental write
gates remain blocked. No further physical operation is authorized by that run.

## Application-owned fields remove a reference for newer plain PF3s

The owned2968-byte mathematical record block can now bootstrap an exported PF3
whose LUTs are nonidentity. Standalone checks of10 existing exports with empty
caches accept superia400/c200/NC from the file alone and conservatively reject
the seven older nonmatching styles; their one-file bundles retain a reference.
No copied Canon tables, source-layout manifest or runtime load is needed.
Completely fresh generation without any encrypted input remains unresolved.

A new integration test now creates an editable project with a real CUBE asset,
exports its PF3, deletes the originals, reopens the single archive, bootstraps
from owned records and links the explicit experimental cache compiler to the
9110 property route, opaque-state plan, UI lock/unlock and requested D171
comparison through fake COM. The capabilities intentionally exclude9192/9189,
matching the observed RP operation boundary. This remains a synthetic complete
chain, not negotiated compiler-route or physical arbitrary-LUT acceptance proof.
The final discovered suite passes642 tests; changed sources compile and the
diff whitespace check passes. No additional camera operation or build followed
the one authorized empty-cycle diagnostic.

## Older PF3 reference records and archived RP framing

The strict version3000 reader/writer now preserves the separate9000..90ff
reference bank with its original IDs, values, types and record order. Basic
edits still target1000..10ff; reference fields are not aliases. Export preserves
the original file size, and portable archives accept bounded version3000 PF3s
up to16MiB instead of assuming434511 bytes. Unchanged titles retain bytes after
their terminator. Camera installation gates were not relaxed.

Private report `PF3_OLD_REFERENCE_BANK_PRESERVATION_20261016.json` verifies the
435532-byte archived Emerald file:14 reference fields, byte-identical no-op
export, all reference values preserved after a Basic edit, and a single project
archive reopened with an empty cache and Canon parser forbidden. This extends
supported old-file editing; it does not establish support for every PF3 version.

`RP_ARCHIVED_SOURCE_WIRE_COMPARISON_20261016.json` separately verifies our9110
framing against all five archived native RP input packets by exact length/hash.
The experimental cache compiler did not match their carrier/LUT blocks. Framing
parity does not prove the cache route is the RP's correct arbitrary-LUT route.
Captured state was not replayed. No additional physical operation followed.

After the reference-bank/title preservation changes, the full discovered suite
passes644 tests in40.339 seconds, including the Qt integration. The whitespace
check passes. No executable was rebuilt.

## Native RP numerical-route evidence expanded

The normal pixel route now covers the actual RP Standard descriptor's kind2
seven/eight-group axes under the existing experimental-geometry opt-in. All
four blocks match the original Emerald registration3 and Superia registration5;
the final serialized9110 packets match their archived WPD input hashes exactly.
Cipher recovery used an owned generated PF3, with Canon loading forbidden.
External caption padding differs but is excluded by the verified serializer;
no captured bytes are substituted. See `RP_COMPACT_SOURCE_20261010.md` and the
private `RP_ARCHIVED_PIXEL_ROUTE_WIRE_VERIFIED_20261016.json` report.
The33 focused axis/grid/carrier tests pass. This supports the normal route for
these real source/descriptor inputs, not arbitrary dense-LUT compilation or
post-write freshness. No additional camera access or build occurred.

The independent dense10/pixel override now also reproduces all12 archived RP
whole-carrier digests exactly, including Superia/Aerochrome and local LUT edits.
The explicitly named offline route `compact16752-dense-pixel` uses dense source
tables only for the first pair, followed by normal pixel processing; the second
pair remains parameterless. This differs from the old all-cache candidate.
`RP_DENSE_PIXEL_SOURCE_PROOF_20261016.json` records source/descriptor provenance
and12/12 equality, with no Canon loading or captured numerical inputs. All647
discovered tests pass in44.771s, including Qt; changed sources compile and the
whitespace check passes.

Source-domain work remains: generated bases' empty kind2 axis blocks are still
rejected by the pixel-settings decoder. The current tests assert that boundary
and separately exercise supported six-axis source records through compilation
and slot3/9110 packet planning. Do not enable independent installation or choose
the new route automatically before addressing that case and physical validation.

## Generated empty-axis PF3s now reach the dense/pixel compiler

The zero-count boundary above is now resolved for the exact application-owned
512-byte kind2/count0 record with zero padding. Static instruction assertions
show that fa40 returns the copied RGB unchanged, while its caller retains both
mode1 fixed-point round trips for a nonnull pointer. The evaluator preserves
that distinction; it does not treat an empty block as a missing optional axis.
Nonzero padding and other unobserved layouts remain rejected.

`GENERATED_DENSE_PIXEL_PROOF_20261016.json` verifies all6 owned generated bases
and all10 existing single-file user projects compile, pass compact packed-table
grammar checks, have nonzero table luminance and produce a slot3/9110 offline
plan. Each project was reopened in a temporary directory with an empty cache;
Canon parser loading was forbidden. The12 historical complete native output
digests still match exactly. New empty-axis results have static attribution and
synthetic numerical tests, not a new native numerical capture or physical
acceptance proof. `EMPTY_AXIS_PIXEL_STATIC_PROOF_20261016.json` retains21 checked
instructions from the hash-known binary without loading/executing it.

The editable-bundle integration now traverses the new route through fake COM,
state planning, UI lock/unlock and requestedD171 comparison. All649 discovered
tests pass in55.642s; changed sources compile and whitespace checks pass. User
projects were not modified. No further RP session, write, build or automatic
compiler-route selection occurred.

## Read-only compiler preflight integration

The diagnostic can load an owned PF3 or single-file project before device
discovery, then request the descriptor and selected slot and compile locally
only after remote/event cleanup. The candidate requires the observed RP
descriptor hash, event identifier, advertised operations, slot-style grammar
and pixel-processing gates. Reports explicitly leave write authorization,
state freshness and physical acceptance false. This is an offline candidate,
not a registration operation or a generic camera-family selector.

Boundary tests now prove that source-loading failure occurs before discovery
or Open and omits private exception details. A rejected compiler profile
retains completed remote cleanup and cannot start a data-phase write.24
focused preflight/diagnostic tests and657 full-suite tests passed; changed
Python sources compile. No physical session, style write, build or publication
was performed during this verification. The earlier Err70 experiments remain
unvalidated and must not be retried without separate authorization.

## Self-contained bootstrap does not require a global cache

The shared independent PF3 reader now attempts the supplied file before
enumerating neighboring references or creating/accessing the runtime cache.
Previously both searches occurred eagerly, even when self-bootstrap succeeded;
an inaccessible cache could prevent an otherwise valid portable source opening.
Fallback reference order and duplicate suppression remain unchanged when a
reference is necessary. No keys or proprietary resources are embedded.

Tests prohibit both neighboring-file searches and cache access for a synthetic
self-contained calibration. The portable-project preflight test also reopens
its embedded PF3 with global-cache access raising PermissionError and the Canon
parser forbidden.660 full-suite tests and changed-source py_compile pass.
No new executable, physical session or release was created for this change.

## Integrated extended17 route without Canon cipher dependencies, 2026-10-17

The explicit offline route `modern83076-dense` now links source PF3 validation,
accepted dense17 compilation, transport planning and content comparison. Its
scope is Neutral/extended83076 only, matching the archived evidence. Missing
descriptors, other bases and inferred camera selectors are rejected rather
than selecting a route by payload size. The live independent controller still
accepts only the RP profile; no other camera writes were enabled.

The private `verify_integrated_dense17_no_canon.py` reproduces all12 complete
archived accepted carriers exactly, including local edits, Superia and
Aerochrome, then checks the explicit send framing. Keys are recovered from the
owned self-contained NC PF3 with neighboring searches/cache access forbidden.
No Canon DLL is read or executed; native research-loader modules remain absent.
The older fixture merely named IDENTITY was rejected as a calibration rather
than assuming its name proved mathematical identity.

Evidence: `INTEGRATED_DENSE17_NO_CANON_20261017.json`, with hashes for the source,
descriptor and expected carrier of each case. This extends offline compilation
integration, not physical R8 registration, base-style coverage, modern78980,
full33 or automatic live-family detection. Existing public/experimental builds
were not regenerated for this change.

## Exact observed-profile read-only dispatch, 2026-10-17

`family_preflight_reference` now dispatches read-only preparation between the
existing RP profile and the archived extended17 profile. The latter requires
the observed compiler identifier, exact descriptor hash/length, advertised
operations and a normalized Neutral83076 style with verified envelope, control
markers, reserved packed bits and auxiliary padding. Unknown identifiers or
changed descriptors fail closed; size alone never selects the compiler.

The12 archived carriers pass this complete preflight and still compile exactly
without reading a Canon DLL. Evidence is
`OBSERVED_DENSE17_PREFLIGHT_NO_CANON_20261017.json`. Its operation lists are
synthetic caller inputs, not measured R8 WPD capabilities or live evidence.
No new physical operation was performed. The report explicitly disables live
registration; the RP state planner now rejects every other compiler route.
Tests verify malformed17-node data, wrong profiles/capabilities and diagnostic
behavior where a candidate is valid but state/write authorization remains false.
The actual registration controller still calls only the RP preflight and has
not been broadened. No executable was rebuilt for this change.

## RC1 editor packaging and flat independent exports, 2026-10-17

Current physical evidence is retained in `RP_AUTHORIZED_REGISTRATION_02.json`,
`RP_AUTHORIZED_AEROCHROME_02.json` and `RP_VISUAL_ACCEPTANCE_20261017.json`.
These record successful requested readback, completed cleanup and subsequent
user-reported NC/Aerochrome appearance without errors. No new physical session
was performed for the following UI/package changes.

Independent installation now first saves one editable project directly in the
Documents style folder. Temporary PF3s, baseline backups and reports remain in
`app_data/logs/camera_install`. The editor asks for write approval only after
the concrete project is prepared; declining keeps that file and launches no
camera worker. Tests verify the ordering, captured editor state, flat output,
technical-log location and cancellation. The full suite passed682 tests before
the release-only version/name update.

The new local folder is
`../PUBLIC_ALPHA_STANDALONE/CanonStyleStudio_1.0.0-rc.1_Windows_x64`.
It has a distinct RC1 build ID and does not overwrite any earlier release.
`EDITOR_RC1_BUILD_VERIFICATION_20261017.json` records executable SHA256,
successful offscreen startup, required independent modules, forbidden-file audit
and a frozen missing-source failure before device Open. No Canon resources or
owned style files are bundled. No publication or GitHub change occurred.

Windows Sandbox is absent on this host, so clean-Windows deployment remains
unverified. The current computer has Canon software installed; independent
transport/compiler evidence must not be described as a clean-machine test.
Fresh generation without any owned encrypted input, Canon-equivalent RAW
independence and physical validation beyond the exact RP profile remain open.
The goal is therefore still active; RC1 is not a stable-release completion claim.

## RC2 owned-project initialization and cache validation, 2026-10-17

A first-use regression found that changing the base after opening an owned
project still searched only the generated-base cache for cipher calibration.
The generator now accepts the opened PF3/project base as its explicit cipher
reference. It constructs all new fields mathematically rather than copying the
imported LUT or source properties. Existing Canon callers retain their behavior.
Independent resolution also reuses the complete generated-base validator, so a
stale zero-matrix cache is regenerated instead of passing identity-table checks
alone. Source projects and imported PF3s remain unchanged.

Three regression tests cover all6 bases from a nonidentity owned PF3 with an
empty cache, regeneration of an invalid zero-matrix cache, and actual editor
project reopening/base selection with Canon discovery and parsing disabled.
All685 tests pass in80.471s; changed sources compile and whitespace checks pass.

The new local build is
`../PUBLIC_ALPHA_STANDALONE/CanonStyleStudio_1.0.0-rc.2_Windows_x64`.
`EDITOR_RC2_BUILD_VERIFICATION_20261017.json` records its digest, frozen version,
included calibration API, successful offscreen startup, forbidden-file audit
and missing-source rejection before device Open. RC1 was preserved. No camera
session or publication was performed for RC2.

The user confirmed no second Windows machine is available. Sandbox is absent;
clean-Windows deployment is still unverified. Tests with Canon discovery/parser
disabled are source-path evidence, not a replacement for that deployment test.
Generation with no encrypted input at all and independent Canon RAW/DPP
rendering remain unresolved and are not claimed by RC2.

## Source runtime packaging closure, 2026-10-17

The source-package allowlist still omitted the independent controller and its
compiler/protocol dependencies, even though the frozen RC2 contained them.
The source builder now includes those runtime modules, the isolated worker
entry point and the platform-neutral USB PTP codec. Source archive names no
longer contain Public Alpha, and storage metadata matches the Documents style
folder and private application logs.

The full33 planar conversion was moved from the native research runner to the
portable packing module, retaining the research import as a compatibility alias.
This removes a production-core dependency on the native-oracle runner without
changing numerical behavior. Research/fixture loaders are not source-package
runtime dependencies. The source launcher/About wording now distinguishes
optional Canon RAW requirements from independent style installation.

A new regression builds and audits a complete package in a temporary folder,
then launches a fresh isolated Python process from that copy. Windows DLL
loading and EdsCFParse are prohibited. The process generates a base from an
owned synthetic PF3 with an empty cache, compiles the dense/pixel route, creates
a slot3/9110 plan and checks portable PTP framing. Native research modules remain
absent. The packaged worker's help also runs without site packages.19 focused
packaging/packing/protocol tests pass, including all12-bit quantization values.

This is isolated-source/runtime evidence, not a clean-Windows deployment test.
No camera operation, new executable build, source publication or GitHub change
was performed for this packaging correction. Delivered RC2 remains unchanged.
