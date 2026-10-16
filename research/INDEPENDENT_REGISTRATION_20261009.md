# Independent registration checkpoint — 2026-10-09

## Primary user-directed objective

Remove installed Canon applications AND runtime DLL requirements for registering
prepared PF3 styles. Prioritize a general compiler/transport implementation for
Windows, Android, iOS and macOS, not per-model hardcoded carriers. Continue safe
offline work autonomously; request only genuinely necessary physical evidence or
user decisions. Preserve working production behavior until replacements have
equivalence evidence. The previous product-managed research goal remains paused;
creation of a replacement was rejected because that goal is unfinished. Do not
claim automatic continuation has been enabled until its state is actually active.

Goal: remove the installed Canon-app requirement for prepared-style registration,
not merely hide EOS Utility or bundle Canon DLLs. Mobile creation remains out of
scope. Production registration unchanged; no camera/session/native host used.

Re-ran ptp_capture against the five original V25 RP slot-1 registrations:
all five match exactly. Observed command is 0x9110; property records are D170
(style) and D163 (registration state). WPD serialization is not USB framing.
D170's tested transformation retains carrier[:4] and carrier[40:], excluding
36 bytes of the EDSDK envelope. This is not evidence for other family layouts.

The five state blobs have two distinct SHA256 values, while selector hashes
are identical. Thus state is neither demonstrated constant nor demonstrated
a unique per-transaction nonce. Its interpretation/acquisition still requires
evidence; do not manufacture it or replay saved state in a new transaction.

Added a platform-neutral parser for the observed Canon property-record data
phase, with length bounds and independent checks on both length words. Three
fixture-free tests reject corruption/truncation and verify synthetic roundtrips.
py_compile and 397 discovered tests pass. Parser validates framing only.

Required remaining edges:

1. Obtain current registration state through an independent read/event path;
   map the exact command sequence and successful response/confirmation behavior.
2. Generate camera-selected style representation without Canon compiler DLLs.
   Prepared PF3 is not automatically a ready-to-send camera payload.
3. Adapt and validate transport on each OS, then physically test acceptance.

Next offline work: inspect acquisition of EDSDK registration 0x115 and correlate
its fields with captured D163 and event records. Keep PF3 0x115 handling separate.
Do not infer general slot/model support from these five same-RP slot-1 captures.

Continuation: product goal is now confirmed active (get_goal), superseding the
paused-state note above. Existing WPD probe uses remote/event enable 9114/9115,
drains 9116, requests D163/D170 with 9127, then polls 9116 up to six times.
This is an implemented acquisition hypothesis, not evidence that it works for
every camera or that an observed value is equivalent to registration 0x115.
Moved its C189 decoder into platform-neutral canon_events.py, preserving the
WPD wrapper. No device calls were made. Existing 397-test suite passed; the
four new pure decoder cases and 15 WPD cases passed together (19 tests).
py_compile passed. Next: replay retained event captures against this decoder,
then attribute state fields before implementing an independent write path.

Archived-event audit: scanned all 39 V25 WPD output buffers read-only. Found
66 bounded syntactic C189/D163 candidates across 33 buffers, each with 44-byte
value; no D170 candidates in this scoped scan. Private report stores only file
and value hashes, lengths and candidate offsets. These are not yet attributed
WPD data boundaries or independent transactions (duplicates possible).
The 44-byte event value must not be treated as the earlier 40-byte D163 write
value: determine its extra field/length convention before extracting 0x115.
Next: correlate candidates against captured selector/control values and trace
the enclosing WPD read metadata. No device operations; py_compile and all 401
discovered tests passed.

Correlation breakthrough: all 66 bounded candidates decode as three uint32
prefix words (44, 1, 65) followed by 32 control bytes. Every control matches at
least one of the five captured EDSDK 0x115 writes exactly; selector 65 matches
captured 0x114. Match count 181 includes repeated identical controls and is NOT
181 transactions. The extra event word is the declared 44-byte value length;
the captured write value starts with marker+selector instead.

Added strict decode_observed_rp_d163, preserving the 32-byte control and hiding
it from dataclass repr. It rejects the 40-byte write representation and unknown
length/marker. All 66 candidates pass the decoder and equality assertions.
py_compile and 403 tests pass. This supports extracting the opaque control from
this observed event representation, not its freshness, exact temporal pairing,
availability through 9127 on other cameras, or permission to replay archive data.
Next: attribute the WPD data boundary and request/response chronology.

Completion audit correction: all 39 V25 output capture metadata entries report
NTSTATUS 0x103 (STATUS_PENDING), including all 33 candidate-bearing buffers.
The original agent's onLeave reads the entire allocated output capacity and
does not retain IO_STATUS_BLOCK final status/Information or later completion.
Therefore candidates can be stale/repeated memory. Byte equality and observed
layout remain evidence, but fresh device response/chronology is NOT established.
V25_COMPLETION_AUDIT_20261009.json reproduces this metadata audit with matching
file hashes. Do not describe the decoder as a validated independent state read.

The current WPD reader is a different path: it completes the WPD transfer and
checks PTP response 2001 before returning data. That implementation alone is
not physical evidence. Next safe branches: locate completed higher-level reads
in other retained captures, or map EDSDK's completed-event decoding statically.
If new physical capture is required, retain final transferred length and status
at completion, not the allocated buffer at asynchronous call return.
py_compile passed for the new audit. No camera access or DLL modification.

Broader metadata inventory: eight retained events.jsonl captures in the two
selected archive trees contain matching transport event types. Neither of the
two IOCTL-bearing captures records final transferred-length/completion keys;
their 39+20 output entries all report STATUS_PENDING. Successful NtReadFile
entries are not a substitute: V25 attributes 10 to PF2/PF3 files and eight to
local executables, while the second recorder attributes all eight to PF3 files.
Other reads have unattributed handles and cannot be called camera responses.
TRANSPORT_COMPLETION_INVENTORY_20261009.json records counts without raw device
paths. Scope excludes differently named logs and nonselected archive trees.
py_compile passed. Next useful independent branch: static EDSDK event decoding
and property mapping, rather than replaying unproven return-time buffers.

Static EDSDK revision gated by SHA256
e1ed7ef265e2b351b0a2661bce0d7a2ded1ec45254edcc1015f60914671955d5.
Immediate candidate scan locates C189/114/115/01000203 instruction candidates,
but no 32-bit D163/D170 immediates in executable sections. Those values occur
in data: D170 at ed79c/f8328/1171f0; D163 at ed878/f8380/117248.
This redirects the next analysis toward data-table references, not an assumed
hardcoded instruction mapping. Tables' schemas still unproven. Private
EDSDK_REGISTRATION_ID_CANDIDATES_20261009.json includes bounded contexts and
hash. py_compile passed; DLL never loaded or modified. An inefficient optional
raw-occurrence command was interrupted and replaced with a completed bounded
regex search; no live process remains from it.

Static D163 attribution: table entry ed878 contains D163, handler 3c5f0,
internal ID 2000d163, type-like 21 and zero flag. Decoder table f8380 pairs
D163 with 70120. The latter allocates 40 bytes and calls 398c0 eleven times,
discarding the first word, storing the remaining ten. 398c0 directly reads
one x86 little-endian word and advances the supplied cursor by four bytes.
Handler 3c5f0 retains the decoded first word at receiver+400, publishes the
second word as four-byte property114, and copies the following eight words
in order to a 32-byte stack buffer published as property115.

This independently corroborates the observed length/marker/selector/control
split. It does not assign meanings to the eight control words or prove event
freshness. Private EDSDK_D163_STATIC_PATH_20261009.json records hash-gated
aligned windows and assertions. DLL not executed/modified; py_compile and
403 tests pass. Next: D170 decoder/envelope handling and table dispatch.

D170 static edge: decoder table f8328 pairs D170 with 701d0; handler table
ed79c pairs D170 with 3c680 and internal01000203 (type-like21, flag1).
Decoder has two allocation-size paths selected by comparing declared length
to the next 16-bit value; do not collapse these into a single assumed format.
Handler consumes a normalized validity word and dataSize at decoded+4. If
valid, allocates dataSize+40; otherwise allocates40. It zeroes the envelope,
copies validity/size, and copies the tail from decoded+8 to envelope+40.
It then publishes01000203 through one of two cache paths selected by a virtual
capability101 check. The allocated caption region is zero at this construction
point, so do not claim a camera-name round-trip or identical outgoing carrier.
The shared D170/D171/D172 handler is a lead for multi-slot generalization,
not proof of slot routing without caller arguments.

Hash-gated aligned windows/assertions persisted in EDSDK_D163_STATIC_PATH;
py_compile passed. No native execution or production modifications. Next:
resolve the decoder's two framing variants and shared-handler parameter flow.

Three-entry static assertions: D170/171/172 share decoder701d0, handler3c680
and internal01000203; their fourth table words are21/22/23. D163/164/165
share decoder70120 and handler3c5f0, with internal2000d163/164/165 and the
same varying fourth words. Exact dispatch meaning of those words remains open.

Added bounded pure decode_701d0 reference: declared uint32 size is compared
against first payload uint16. Equality allocates declared+8, otherwise declared.
Nonzero validity copies allocated-8 payload bytes and writes that size into
normalized+4; zero validity leaves zero-filled output. Strict length/bounds
are our safety guards, not claimed native validation. Four synthetic tests
cover both branches, invalid state and truncation. py_compile/407 tests pass.
Reference is not connected to transport; native equivalence remains to test in
an owned hidden lab process before using it to replace Canon decoding.

Decoder dispatch closed statically: 72db0 reads input property ID, scans341
eight-byte pairs startingf8120, selects the first matching key and calls its
function pointer with the original data and output-size arguments. Unknown ID
returns null. Assertions over the complete table verify D163/164/165 resolve
to70120 and D170/171/172 to701d0. This dispatch itself has no camera-model
argument or slot-specific decoder branch. That is a reusable protocol-layer
finding, not proof that all cameras expose these properties. Table hash and
aligned instructions persisted. py_compile passed; no DLL execution.
Fourth handler-table field still requires attribution in the separate handler
dispatcher; do not rename it as a confirmed slot parameter yet.

Handler dispatcher attribution: executable relocation references identify table
ed4e0..eef20,336 entries of20 bytes. Event path40d1e scans first words against
event property ID, loads handler at+4, then pushes table+0xc, table+8 and event
data before calling. Thus fourth word21/22/23 is the handler's third argument,
not a type enum inferred from appearance. Internal path41841 scans third words
and likewise supplies table+0xc to the handler. Both static paths are retained
with aligned windows/assertions; table SHA256 stored.
Consequently D170/171/172 share internal01000203 but carry distinct handler
parameters21/22/23. The handlers pass those parameters onwards to cache calls.
Mapping to displayed User Def.1/2/3 still requires downstream attribution;
do not conflate these parameter values with literal slot numbers or state IDs.
py_compile passed; no native DLL execution or camera operation.

Property-update propagation: 5a9e0 receives property/data/size/parameter, sign
extends parameter to64 bits and forwards all to receiver virtual+24. The
original parameter also reaches callbacks when update/callback conditions hold.
No slot-index subtraction or remapping occurs in this wrapper. Concrete virtual
implementation still needs attribution; 21/22/23 must not yet be converted to
User Def. numbers by a new transport implementation. Aligned bounded window
and assertions added; py_compile passed, no DLL execution.

Prioritized next steps: native synthetic equivalence of the standalone D163/
D170 decoders in a hash-gated owned host, then resolve actual property storage
implementation and independent state request/confirmation sequence. This is
necessary before enabling writes; current Windows registration remains intact.

Native decoder equivalence: owned hidden x86 PowerShell host loaded only the
hash-gated EDSDK and invoked standalone70120/701d0 with synthetic data. No
EdsInitializeSDK, camera enumeration/session or transport calls. Four D163
selectors0/65/66/67 and six D170 cases (validity0/1/2 times both size branches)
matched independent Python output byte-for-byte. Reported sizes matched,
input+guards remained unchanged and output-size guards intact. Native allocated
outputs freed, script unloaded/session detached/owned host killed in finally.
Private NATIVE_REGISTRATION_DECODER_PROOF_20261009.json retains hashes/results,
no Canon camera-state fixtures. py_compile and407 tests passed.

Important distinction: D163 reports original44 despite returning40 normalized
bytes; D170 reports declared size even when allocation is declared+8. Therefore
native reportedSize is not automatically safe normalized-output length.
This proof is ten synthetic cases, not full registration, unknown layouts or
fresh live state. Next: resolve storage/slot parameter and outbound encoding.

Public-property routing found independently: rdata e2f88 maps01000203 to
thunks1dd8/1de0, jumping through receiver virtual slots2f4/2f8. e2fa0 maps115
to1df8/1e00 -> virtual304/308. These are routes, not yet established read/write
directions or concrete serializers. Native property metadata e5d7c contains
01000203,e,1; not sufficient to infer wire layout.
Data strings identify D170 as DS_PROP_PICTURE_STYLE_USER_PARAMETER1 and D163
as DS_PROP_PICTURE_STYLE_EX_USER_SETTING1; names corroborate intended user
parameter/state roles but do not prove slot-number conversion alone.
Hash-gated table/thunk assertions persisted; py_compile passed. Next locate
concrete vtable implementations for2f4/2f8/304/308 and attribute direction.

Static continuation: constructor store4315b establishes f0154 as an object
vtable (base construction calls28a0). Its property01000203 setter is58330;
115 setter56650. Unlike unrelated stream vtables, these implementations use
the actual property IDs and transport paths. Scanner retains candidate origins
separately; f04c4 is only a raw immediate occurrence, not constructor evidence.

58330 bounds parameter21..23, strips the36-byte caption/envelope region by
copying carrier+40 into an intermediate header+8, then calls serializer72ba0.
Capability branches prefer operations9192 or918a using parameter-20 (1..3).
Fallback derives property parameter+d14f (D170..D172) and calls transport
virtual84 with value2. This establishes arithmetic but not complete transport
semantics. The serializer outputs length=dataSize+8, validity, then payload.

56650 bounds control data at least32 bytes and for parameters21..23 reads114
with that parameter. receiver+400 selects a legacy32-byte serializer72ce0,
property parameter+d13f (D160..D162), versus extended44-byte serializer72d40,
property parameter+d142 (D163..D165). Both flow to transport virtual84.
Extended input consists of marker, selector, eight control words. Initial
reading incorrectly inferred a final-word swap from instruction order. Native
synthetic verification below corrects this: input+24 to output+28 and input+20
to output+24 are both normal offsets after prepending the four-byte length.
Do not change working registration or enable standalone writes based only on
these isolated serializers; freshness and complete framing remain unproven.

Hash-gated static evidence: EDSDK_REGISTRATION_VTABLE_CANDIDATES_20261009.json,
reproducer scan_edsdk_registration_vtables.py; py_compile passed. No DLL
execution/camera access. Next independently model and synthetically validate
these serializers, then attribute framing and completion of transport virtual84.

Serializer verification completed: independent registration_encode_reference.py
matches native72ba0/72ce0/72d40 in18 synthetic cases (legacy/extended distinct
word sequences and validity0/1/2/ffffffff with payload lengths0/4/64). Initial
swap hypothesis failed immediately; corrected offset interpretation preserves
every normalized state word. All18 outputs and reported sizes exact; inputs
and guards unchanged. Owned hidden x86 host cleaned in finally, no SDK init,
camera enumeration or session. Private NATIVE_REGISTRATION_ENCODER_PROOF_20261009.json.
Production send path untouched. This is serializer equivalence, not live-state
freshness, full carrier generation, transaction completion or camera acceptance.

Transport candidate6a450: three constructor-referenced lower-layer tables
f17dc/f4034/f8c38 contain6a450 at virtual84. Aligned body builds operation9110;
buffer fields are serializedLength+8, propertyCode, then serialized bytes.
Computes another command field via429c0 and calls virtual2fc with original
first argument and command structure. That first argument must not yet be
named a transaction/session ID. Still need prove manager receiver+20 resolves
this lower-layer class on the relevant call path and trace virtual2fc completion.
72ef0 is only a pointer selector using object+30c; not a transport factory.

Independent frame_property reference added with length bounds and tests:
extended normalized state ->44-byte serialization ->52-byte D163 buffer equals
the previous capture-derived property builder, with no assumed raw state or
camera access. Style framing also checked. 414 tests and py_compile passed.
This distinguishes property data framing from USB PTP containers and complete
registration transactions; production transport remains untouched.

Lower transport continuation: f4034 virtual2fc ->6f7c0, f8c38 virtual2fc
->739a0. First argument is used as an object pointer (vtable94 in6f7c0,
function pointer+38 via73560 in739a0), NOT a numeric session/transaction ID.
6f7c0 uses timeout30000, maps response through7bbb0 and retries resultA106
at most10 times with200ms delay. 739a0 explicitly checks response2001 before
copying five response parameters; responseA106 loops after200ms without a
local counter visible in the bounded body. Do not label A106's meaning until
mapping/source evidence establishes it or reproduce unbounded retries.

429c0 is unsigned min(length, capacity), not a checksum. 6a450 uses it for
command transfer length; potential truncation/capacity semantics must be handled
explicitly in an independent backend. Operation9110 and buffer layout asserted
against aligned instruction addresses. 73560 dispatches first-object+38 with
constant100 and original transfer arguments; adapter implementation unresolved.
Base constructor28a0 stores caller-supplied first argument in receiver+20;
thus previous scanner candidates alone do not prove its manager's concrete
class. de50/91b0 candidates excluded as direct transport-return proof.
Static report refreshed; hash gate/assertions/py_compile passed. No native
execution, camera operation or changes to production registration.
Next: resolve caller-owned manager/adapters and read completion semantics,
then pair bounded transaction logic with independently generated carriers.

RTTI attribution closes class names: COL/type-descriptor chains independently
identify f0154 CPtpCamera, f4034 CMobilePtpInterface, f8c38 CWinPtpInterface,
f17dc CPtpInterface. Not stream classes as previously cautioned/inferred.
This is internal class identification, NOT implemented Android/iOS support.
Short helper/manager tables recovered via RTTI, avoiding minimum-length scan:
CIOManager ec458; CWinIOManager f8fac; CPtpHelper f179c;
CWinPtpHelper f8bd0. Their constructor references retained separately.

CWinIOManager virtual0c ->75cd0: argument4 lazily creates a24-byte object via
6f100 (CMobilePtpInterface constructor), caches receiver+3c, calls virtual4
initialization and deletes/nulls on failure. Other arguments call390f0, which
returns receiver+4. Constructor74970 initializes that default pointer to0;
actual subsequent assignment still needs attribution. CPtpHelper virtual0c
returns0 and CWinPtpHelper virtual0c returns1; neither is the sought interface
resolver. This removes two misleading candidate paths without live execution.
Full RTTI and aligned windows saved in static evidence; py_compile passed.
Next resolve default manager+4 initialization and external callback+38 owner.

Default manager path closed: CWinIOManager virtual4 is39670, calls virtual50
->76df0. After COM initialization/object creation,76df0 constructs via73230
(CWinPtpInterface), stores returned object at manager+4, initializes virtual4,
and aborts on failure. Thus75cd0's non4 path returns this Windows interface.
Camera factory74cd0 supplies its manager pointer explicitly to43120 CPtpCamera
constructor; legacy paths instead call3b410. Parameter-source model semantics
still unassigned. No initializer was executed.

Offset38 immediate callback scan yielded one executable-pointer candidate:
store7673a ->770d0. Callback770d0 branches on first object+30: kind3 calls796f0
through global119d7c, kind2 acquires a COM interface using GUID faf84 then
calls73e30. Other kind handling and error remapping retained in the bounded
body. This supplies concrete adapter subpaths to inspect rather than guessing
a universal USB implementation. Names of the two Windows API interfaces not
yet established; don't label them WPD/WIA solely from appearance.
Manager creation and adapter call instructions asserted; static reproducer and
py_compile pass. All calls remain static, no SDK initialization or camera I/O.
Next: anchor enclosing store7673a function, attribute73e30/796f0 buffer and
completion contracts, then implement only proven portable protocol behavior.

Kind2 adapter positively identified as WPD: faf84 IID equals project's
IPortableDevice IID625e2df8-6392-4cf0-9ad1-3cfa5f17775c;742c0 uses MTP
category4d545058-1a2e-4106-a357-771e0819fc56 command14, operation1001,
parameters1002, length1007, context1006, common error1003.74820 performs
the data phase and73d60 completion. These identities now hash-gated/asserted
and retained as decoded property keys. No COM instances created.
Kind3 path796f0 is queued: selects object,78c80 copies command into worker
queue78190, waits up to60000ms for event, then returns worker result and actual
length fields. Queue/worker completion and API identity still unresolved.

Added platform-neutral mtp_write_reference controller with injected adapter
only: exact per-chunk acknowledgements, bounded size/chunk count, PTP2001
required, no write retries, one completion/cleanup attempt preserving original
error. These are deliberate safety policies, not a claim of exact replication
of Canon's single-call write helper. Simulated tests cover short/overlong/zero/
boolean counts, exceptions, failed completion, bounds and cleanup failure.
No live adapter, discovery/session or UI binding; cannot register a camera on
its own. 420 tests and py_compile pass. Current production send is unchanged.
Next resolve WPD write helper acknowledgement semantics and worker completion,
then create a tested adapter without enabling camera writes prematurely.

WPD field attribution:74820 uses command16 (fd464), context1006, requested
write count1010 (fb510), data1012 (fb000), returns written count1011 (fa044).
73d60 uses completion command17 (fde2c) and validates common HRESULT1003.
These keys are decoded in the hash-gated static report. Canon's callers of
74820 do not visibly compare returned write count before completion; the
independent controller deliberately requires exact acknowledgement instead.

Added wpd_data_phase_reference.PropertyMapAdapter: injected mapping sender
translates begin14/write16/complete17 with distinct category keys. Common
HRESULT and MTP response1003 cannot be conflated. Missing context/count/error
or invalid types fail. Integration tests use simulated sender only; no COM,
camera discovery/session, live binding or registration UI path exists here.
Strict controller input bounds now reject booleans/floats, oversized buffers
and integer payload allocation before any adapter operation. 424 tests and
py_compile pass. This is tested adapter schema, not device registration.
Remaining: real OS marshaling/access options, live state acquisition/freshness,
registration sequence/confirmation, independent full carrier generation and
physical acceptance. Continue worker and session/state paths offline.

Command helper74640 closed: creates IPortableDeviceValues (CLSIDfa56c,
IIDfbb78 matching existing Windows WPD implementation). Sets COMMON1002
command as PROPVARIANT VT_UI4=19, COMMON1001 category as VT_CLSID=72.
Complete bounded body contains no per-command access-option property; do not
invent a FILE_WRITE_ACCESS setting as part of this helper's native schema.
Device-open access permissions are a separate unresolved layer. This confirms
PropertyMapAdapter's common command/category mapping against native code;
real marshalling must preserve GUID type, not send its string literally.
Decoded common property keys and instruction assertions added to static report.
No COM instantiation or camera calls. py_compile and static assertions pass.

Response extractor74530: reads MTP response code via UI4 accessor, copies
low16 bits to response structure, then retrieves response parameter collection,
reads count and copies VT_UI4 entries at response+0xa. No local maximum count
check is visible in the complete bounded body. Independent decoding must bound
this collection to PTP's five parameters and reject non-UI4 values rather than
silently leaving holes. Response and collection property keys retained from
fc810/fda68; native helper's successful HRESULT alone is not camera acceptance.
This reinforces separate API/transport/protocol/application confirmation gates.
No code execution or live I/O; existing production path remains unchanged.

Independent completion decoder implemented: immutable Completion(code, params),
requires explicit MTP1004 collection (empty allowed), maxfive uint32 parameters,
rejects bool/float/string/negative/overflow and missing collection. Parameters
copied to immutable tuple. Adapter retains only last successfully decoded
completion, clears on new begin or failed completion so stale response cannot
masquerade as the latest result. Common HRESULT is still checked independently.
Simulated tests cover validfive parameters, mutation isolation, all malformed
collections, and failed-result clearing. 427 tests and py_compile passed.
No real OS sender/camera operation or production send changes. This does not
establish installed-style acknowledgement; post-registration readback remains.

Request/readback distinction closed statically: CPtpInterface virtual88 ->68f70
constructs9127 with exactly one property-code parameter and routes through
virtual2f8 (command/no-data). Confirms the existing WPD research reader's
request opcode, but successful request alone does not prove fresh event state.
Separate01000203 getter4ad40 requires supported9189; subtracts20 from caller
parameter then invokes virtual2d4 ->65f00.65f00 uses9189 and virtual300
device-to-host, copies returned data into owned output with reported length.
Thus a direct post-registration style readback capability exists separately
from property event D170. No fallback for absent9189 established in this getter;
do not claim every camera supports it. Returned style is decoded/wrapped and
cached, not trivially equal to original PF3 bytes or proof of a rendered LUT.
Aligned opcode/dispatch assertions saved and py_compile passes. No live reads.
Next inspect supported-operation initialization, registration-state request
caller/cache invalidation and compare readback to independent carrier layout.

Reference framing boundary fixed: earlier accepted1MiB serialized data plus8
header bytes, exceeding the controller's1MiB total packet bound. Limit now
includes the header; boundary test proves exactly1MiB accepted and one more
byte rejected. Optional explicit capacity rejects any would-truncate packet
instead of imitating native min(length,capacity). This is a deliberate safety
policy, not a claim of Canon's maximum supported transfer size. Bytes remain
identical for existing validated small vectors.
Encoder snapshots bytearray/memoryview input to immutable bytes after checking
actual byte count; rejects numeric/string payloads, boolean/float property IDs
and nonboolean state-layout flag. Synthetic tests cover capacity boundaries,
type misuse and mutation isolation. 430 tests and py_compile passed.
No production registration changes, DLL execution, camera access or release.

Capability initialization now attributed statically: camera480c0 clears the
operations vector at+48c/+490, passes DeviceInfo destination+464 to interface
virtual0c (6df10). That function issues1001 through device-to-host virtual300,
decodes uint32 operation count then uint16 codes, stored as uint32 entries.
Thus the supported-operation decisions in style send/readback originate in
DeviceInfo, not a model-name table. Aligned instruction assertions retained.
Added independent ptp_device_info_reference decoder: immutable dataset,
bounded arrays/total bytes, strict terminated UTF16 strings, rejects truncation
and trailing data. Serial number omitted from repr. Synthetic tests exercise
all truncation boundaries, non-ASCII strings and oversized arrays. 434 tests
and py_compile passed. No live DeviceInfo reads or native decoder equivalence;
this is a transport prerequisite, not independent registration completion.

Style capability branches closed one layer deeper: interface2cc ->6b650 sends
9192; interface2d0 ->6b540 sends918a. Both set exactly two command parameters:
caller slot index and serialized byte count. Both copy the72ba0 serialized
style into interface data buffer, then use virtual2fc host-to-device transport.
Caller58330 subtracts20 from selectors21..23 (slot indices1..3), preferring
9192 then918a then property route. Existing36-byte caption is excluded from
these data buffers by caller normalization. This is not raw PF3 transmission.
Instruction assertions and route evidence retained. Full434 tests pass.
No session/state sequence or physical acceptance inferred from these opcodes;
no application send behavior changed and no camera or native execution.

Cache/freshness path separated: CPtpCamera virtual18 ->49bf0 special-cases115;
parameter0 invokes virtual28 before generic4e20. Virtual28 ->13350 removes
matching property/parameter entries and frees their storage: invalidation only,
NOT a remote read. Generic12f50 returns a matching cached value directly;
only absent entry calls virtual80 ->49df0. Cache lookup142e0 matches property
and full64-bit parameter (unless wildcard enabled). Therefore a successful
EdsGetPropertyData alone cannot establish fresh transaction state.
49df0 first calls property-specific5000. Generic fallback only for flagged
handler entries issues interface88 (9127), waits100 timer units, calls59e80
then checks cache. 59e80 matches C189 and requested property before4d100
dispatch, retaining other events where appropriate. D163 table flag is0,
so do not assume generic fallback acquires115; resolve its specific handler.
Static assertions/report updated. No camera sessions or DLL execution.

Specific115 dispatch confirmed via e2fa0 ->1df8 ->virtual304 ->49a70:
only parameter0 resolves114 then reads115 at that selector and caches alias0;
nonzero parameter returns50 in this acquisition helper.114 acquisition thunk
1dc8 ->virtual2ec ->4d10 returns7 without transport. Thus the state-specific
getter relies on selector/slot state already provisioned through events rather
than itself requesting D163. Next resolve initial event population and how its
completion establishes a current state; do not label these getters fresh reads.

Event reference hardened without adding I/O: rejects nonbuffers before bytes
conversion, checks actual memoryview byte count before allocation, total16MiB
safety bound, strict integer property/limits and immutable snapshots. Tests
cover invalid types, all record truncation boundaries and source mutation.
437 tests and py_compile pass. This is safe parsing, not freshness proof.

Initial event population route now closed statically:4c740 configures remote
via interface90=6bc50 (9114), event mode via interfaceb4=6a5b0 (9115), then
camera b8c=48850.48850 invokes interfaceb8=637b0 (9116, device-to-host300),
loops on returned continuation state, or consumes retained camera+418 batch.
It processes C189/D116 first with caller flag1, then dispatches every event
through eff10..f00b0. C189 table entryeff98 points40cf0, reaching existing
property dispatch. So getters114/115 depend on this event population sequence.
Setup values are NOT always1: remote base1, transport+330==2 ->5, timer
predicate may OR10, transport==4 ->41. Event mode1 when helper+37c virtual0c
returns true, else2. Helpers/transport identities are not yet fully assigned.
448b0 cleanup and4c740 failure cleanup send event0 then remote0. Retry81
and other loops retained as evidence, not implemented as unbounded retries.
Aligned assertions and report retain the route/mode branches. No live setup,
camera reads, sessions or DLL execution. Fresh event generation and complete
independent registration remain unproven; retained batches matter to freshness.

Continuation semantics closed in5ea80: stop on length0/code0/codeffffffff;
optional output flag set1 exactly when final codeffffffff.637b0 passes this
flag to48850, which repeats9116 until it clears. Independent EventBatch now
exposes continuation separately from immutable C189 property values, hides
values in repr, rejects nonzero tail and unsupported terminal geometries.
Eight-byte terminal records are an explicit stricter research policy, not a
claim that native code validates their size. Existing extraction API retains
its selected-property-only value limit. Synthetic empty/normal/continuation,
malformed-tail/layout and selected-limit tests pass.440 tests and py_compile
pass. Native instruction assertions saved; no DLL execution or live I/O.

Re-ran original read-only V25 candidate audit using refactored extractor:
39 archived WPD output buffers still yield66 syntactically valid state-event
candidates. This preserves archival parser compatibility, NOT completion or
freshness: those native captures were STATUS_PENDING, as documented earlier.

Independent receive controller added (injected test adapter only): validates
opcode/parameters, declared total, actual buffer length, bounded chunks/bytes;
returns payload only after PTP2001 completion. Known length must match exactly;
unknown length requires a short read, never treats hitting a bound as EOF.
Completes once during failure cleanup without promoting failure to success.
No transport implementation, discovery/session or camera access. Six synthetic
tests cover empty/known/unknown/padded reads, inconsistent counts, read failure,
completion failure, bounds and preflight rejection.446 tests/py_compile pass.

Independent WPD receive property-map adapter now bridges the receive controller
to injected command13/15/17 maps. No COM sender/device discovery/session is
provided or invoked. Begin reads context1006 and UI8 total1007; command15 sends
context1006, requested1008 and a bounded1012 request buffer. Returned1012 bytes
are copied immutably and their actual length is used; the zero-filled supplied
capacity is never accepted as returned data. Completion still requires final
PTP2001, independently of WPD HRESULT. Invalid begin-size closes an established
context once; read failure/final PTP failure never returns a successful payload.

Chunk size is a configured stricter controller policy, not a claim that native
74050 queries optimal-size1005. extract_wpd_read_keys.py independently verifies
eight GUID/PID constants in hash-known EDSDK; WPD_READ_KEYS_20261009.json records
them without DLL execution. Synthetic integration tests cover exact command
maps/chunk lengths, invalid UI8 size, missing/oversized actual data, immutable
copy, allocation guards, HRESULT failure and unsuccessful final response with
one cleanup.483 total tests and py_compile pass. The remaining real sender,
fresh event-state acquisition and independent camera registration are unproven.

WPD receive correction: the first injected adapter used GetBuffer length as
actual bytes. That was insufficient for padded buffers. Microsoft's documented
READ_DATA contract requires TRANSFER_NUM_BYTES_READ (1009), distinct from
TRANSFER_DATA capacity (1012). The adapter now requires a bounded integer1009
and preserves only that prefix through the receive controller. Missing/bool/
negative/excess counts fail. Begin handles documented unknown totalffffffff
with short-read EOF, and optional driver optimal1013 bounded by configured
policy. Earlier discussion of optimal1005 was not an attribution: actual WPD
optimal key is1013. Native EDSDK74050 itself does not query it in the observed
window, whereas the existing experimental windows_wpd_probe does.

Sources:
https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/wpd-command-mtp-ext-read-data
https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/wpd-command-mtp-ext-execute-command-with-data-to-read

`canon_event_receive_reference.drain` now joins completed injected WPD receives
with existing Canon event parsing and bounded ffffffff continuation handling.
It returns immutable ordered events only after every data phase completes;
failure/malformed later batch never returns partial success. Aggregate byte and
batch bounds fail rather than declaring EOF. Synthetic integration covers two
batches, failed second completion, malformed data, bounds and hidden event values.
489 tests and py_compile pass. No real adapter/session/device was invoked.

Important limitation: completed9116 batches can still be retained camera events.
The drain does not claim freshness, manufacture115, or authorize registration.
Existing windows_wpd_probe already contains experimental COM discovery/read
helpers; the missing part is a verified reusable adapter/state-machine path,
not the literal absence of all OS-facing code. It remains unexecuted here.

Native WPD read mapped statically:74050 command13 sets opcode/parameter
collection, reads total1007/context1006, calls746e0 command15 with context,
requested1008 and supplied1012 buffer. GetBuffer1012 returns owned data and
reported buffer length. Then command17 via73d60 and final PTP extraction74530.
Thus successful begin/read alone is insufficient. Independent controller's
chunk and exact-count rules are intentional stricter policy, not a claim native
code implements those same loops. Keys/assertions retained; no DLL execution.

### Portable offline style-send plan —20261010

Added pure `style_send_plan_reference.plan_style_send`: explicit handler21..23,
bounded carrier with matching dataSize, immutable supported-operation list.
Removes the envelope caption region via normalized validity/size + carrier40:,
then existing72ba0 reference serialization. Selects9192 before918a with
parameters(slot=selector-20, serializedBytes); otherwise frames D170/171/172
for9110. No I/O/state acquisition/session/permission to write is provided.
`extract_style_send_selection.py` verifies16 instructions in hash-known EDSDK.
Important:58330 branches straight to cleanup on nonzero9192/918a result; its
fallback is capability absence, not retry after a failed write. Do not implement
automatic retries across protocols on the strength of this planner.
Three fixture-free tests cover precedence, slots/property framing, immutable
copies, hidden payload repr and invalid/truncated inputs.517 tests/py_compile
pass. Complete independent registration remains unproven; no camera accessed.

### Explicit slot-state packet reference —20261010

`state_send_plan_reference` implements only56650's explicit21..23 branches.
It requires observed marker/selector and an opaque32-byte control, with no
parameter0 alias/getter. Nonzero marker chooses extended normalized
marker+selector+eight control words, serializer72d40, propertiesD163..D165.
Zero marker chooses selector+first six words, serializer72ce0, D160..D162;
this matches native wire construction, not a mutation/resizing of the original
control or a claim that its last two words are dispensable in other contexts.
No transport/session/freshness/registration authorization is implemented.
Three new synthetic tests pass; total520 tests pluspy_compile pass.
`verify_state_plan_archived_values.py` compares66 archived slot1 candidate
values after strict decoding and reserialization: all exact. This is layout
roundtrip only, not independent authority: the original WPD observations were
STATUS_PENDING and cannot prove completed/fresh device events. No values sent.

### Readback conversion and parser allocation bounds —20261011

Added pure `style_readback_reference.decode_9189`, following4ad40's two
cursor-word reads (declared/validity), payload length declared-8 and normalized
validity/dataSize/body. This is the explicit header-included path, not701d0's
dual-size heuristic. Empty payload and invalid/zeroed cases have tests; strict
length/allocation checks are our safety policy. Static verifier now asserts
nine readback instructions in addition to16 send-selection instructions.
No live read was made; even byte equality would require independent freshness
and transaction attribution before claiming installation confirmation.
Hardened existing701d0 reference: reject nonbuffers and oversized buffers before
bytes conversion; numeric input previously could cause arbitrary allocation.
New truncation/type/snapshot tests preserve accepted numerical behavior.
524 tests andpy_compile pass. Production registration remains unchanged.

### Injected completed9189 receive —20261011

`receive_9189` now joins explicit advertised9189 capability and handler21..23
to the bounded independent receive controller, with slot parameters1..3.
Only after complete returns PTP2001 is the body decoded. There is no OS adapter,
discovery/session or cache fallback. Missing capability/invalid slot fails before
calling an adapter. Failed completion/malformed body never returns success.
Three new synthetic tests verify all slots, chunked reception, one completion
and preflight rejection. An initial fake returned padding beyond requested
capacity and correctly failed the controller; corrected the fake, not the guard.
527 tests andpy_compile pass. This proves injected integration only, not device
availability, fresh post-registration contents or complete registration.

### Compiler-input events —20261011

New static linkage: handler tableed8b4 mapsD17F ->3ba40 ->01000210,
parameter0/flag1. Decoder tablef83b0 selects70c80, which copies declared bytes
including length; handler publishes bytes after the four-byte length. This
supplies a protocol-side source for the raw descriptor, not a decoded store.
Handler tableed5e4 mapsD116 ->3b6c0 ->01000001, parameter0/flag0;
decoder6fbe0 reads one uint32. Handler aliases ONLY80000227 to40000227.
Do not generalize the alias to other IDs or assume rawID equals compiler ID.
Getter thunks1e08/1b48 select slots30c/1a8 atCPtpCamera vtablef0154;
targets4d30/4a30 return7 without transport. Thus getters depend on prior
event/cache provisioning; descriptor flag1 is compatible with the previously
mapped generic9127 fallback, but a fresh successful response remains unproven.
`extract_compiler_input_events.py` gates DLL hash, verifies four table pairs/
entries and19 aligned instructions. Pure `compiler_input_events_reference`
extracts bounded immutable descriptor bytes and the specific ID mapping.
Three synthetic tests cover alias specificity, descriptor geometries, invalid
types/lengths/truncation and snapshot isolation.530 tests andpy_compile pass.
No SDK execution, camera access or production behavior changes.

### Archived compiler-input candidate audit —20261011

`audit_compiler_input_events.py` scans59 retained WPD output buffers from the
two IOCTL-bearing captures in the existing completion inventory (39V25+20).
Regex locates bounded C189/D17F orC189/D116 headers; strict pure decoders would
compare to five captured compiler descriptor/ID inputs fromV25. Result: zero
syntactic candidates of either property, no rejected bounded candidates.
Report retains hashes/lengths for all59 buffers, no raw payloads. First39 hashes
are checked against earlier audit; added20 are hash-inventoried by this run.
This does NOT prove those events never occurred: scope is retained output
buffers only, with WPD framing and STATUS_PENDING limitations. It excludes
using these captures as empirical descriptor-event provenance. Next useful
branch is initial event population/static request flow, not fabricating events
around saved descriptors and presenting that as physical evidence.
Audit andpy_compile pass. No camera access, source modifications or native code.

### Initial ID prepass is not deduplication —20261011

Aligned48850 control flow confirms caller initial flag!=0 scans for FIRST
C189/D116 only, dispatches it, then enters the normal loop from event index0.
No removal or skip is performed: firstID can be published/callbacked twice.
AdditionalID events remain in their original positions. Do not count that as
two device transactions, replace it with moving allID events to the front, or
infer the reason beyond earlyID publication from this control flow alone.
`initial_property_dispatch_order` is a pure property-event-only projection;
nonproperty native events/handlers and full session setup are outside scope.
Static compiler-input verifier now29 assertions. Two synthetic order/typing
tests added;532 total tests andpy_compile pass. No native/device execution.

### WPD no-data command reference —20261011

Closed a missing transport piece statically: interface table f8c38 slot2f8
targets737a0, which prepares transfer mode5 and calls73560. The mode dispatcher
73e30 selects73e90 for mode5. That helper constructs MTP command12 from the
PROPERTYKEY atfd42c, sets opcode1001 and parameter collection1002 (VT_UI4=19),
calls the injected WPD sender and checks common HRESULT1003 before extracting
final PTP completion through74530. The offset38 callback binding is a distinct
ownership/linkage question; no complete OS/session call chain is claimed here.

`extract_wpd_no_data.py` verifies20 aligned instructions, the interface slot
and four GUID/property keys in the hash-known SDK without executing it.
`CommandPropertyMapAdapter.execute` reproduces the property map with an
explicit injected sender, requires bounded immutable uint32 parameters and
PTP2001 completion. It never retries, unlike native upper-layer busy handling;
that is intentional policy rather than a claim of full native equivalence.
Failure resets stale completion state; a valid non-OK completion remains
available as diagnostic data but is never returned as success.

Three fixture-free tests cover exact command12 maps, final response parameters,
preflight rejection before sender invocation, HRESULT failures, missing final
fields and no retry onA106. This supplies command-only framing alongside the
existing read13/15/17 and write14/16/17 references. It does not implement session
creation, fresh115 acquisition or registration authorization. Production
camera-install paths remain untouched; no Canon code or device was executed.

### WPD callback construction and COM ownership —20261011

Anchored the previously isolated7673a callback store inside762b0 using its
aligned function body. CWinIOManager tablef8fac slot74 points to762b0. That
routine creates the Windows PortableDeviceManager (CLSID0af10cec..., IIDa1567595...),
calls its device enumeration twice and builds outer records with stride314.
Each includes an inner3c-byte adapter at+c, kind2 at inner+30 and callback770d0
at inner+38. This is Windows adapter construction, not camera payload metadata.

The adapter's inner+34 is now attributable to a COM Global Interface Table
cookie rather than camera state. Manager initializer76df0 creates
CLSID00000323/IID00000146 into global119d78. Kind2 callback770d0 passes the
inner+34 value and IPortableDevice IID625e2df8... to that global's slot14,
then invokes73e30 and releases the acquired interface. This matches
IGlobalInterfaceTable::GetInterfaceFromGlobal; the registration and revocation
of that cookie still need their complete call paths attributed.

Microsoft documents the cookie as an apartment-access identifier, and the
returned pointer requires Release. It is not portable across process/machine
boundaries and must not be recorded/replayed as a camera transaction ID:
https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-iglobalinterfacetable-getinterfacefromglobal
https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-iglobalinterfacetable

Private `extract_wpd_callback_owner.py` now gates31 aligned instructions,
five GUIDs, three imported Windows functions and the manager slot. Report
`WPD_CALLBACK_OWNER_STATIC_20261011.json` contains no device data. This closes
the construction/lookup provenance for the Windows command callback, not
session opening, fresh115 acquisition or physical registration. No device
enumeration, COM creation or Canon code was executed; py_compile passes.

### WPD open and cookie registration linkage —20261011

The missing registration side is now anchored: thunk74e40 checks adapter kind2,
replaces its second argument with inner+34, and tail-jumps74e80. That routine
creates IPortableDeviceValues, supplies client properties2..5 in category
204d9f0c... (native labelEDSDK, numeric1/0/0), enumerates candidate WPD IDs and
compares the saved identifying strings before creating IPortableDevice.
Call75355 invokes its Open slot0c with the selected WPD ID and client values.
Only the success branch reaches7539f, GlobalInterfaceTable slot0c
RegisterInterfaceInGlobal, using the caller's inner+34 address as cookie output.
The subsequently mapped770d0 GetInterfaceFromGlobal therefore consumes the
same registered cookie, rather than arbitrary camera-provided bytes.

This native label/version metadata is evidence, not a requirement to impersonate
EDSDK in an independent application. Existing read-only Windows probe uses its
own client access policy and was NOT executed or changed. WPD object opening,
COM cookie registration, Canon remote/event configuration and actual style
registration are separate operations; proving the first two does not prove
the latter two or live state freshness. Cookie revocation/Close and all failure
cleanup paths remain to be traced fully.

The callback-owner verifier now checks55 aligned instructions, eight GUIDs,
four client PROPERTYKEYs and the native client string, plus prior import/slot
checks. Static replay andpy_compile pass. No SDK or COM method was executed,
no sessions opened and no production behavior changed.

### WPD close/revoke lifecycle —20261011

Anchored773f0 kind2 cleanup. If global GIT119d78 exists, it acquires the
IPortableDevice through cookie inner+34. A successful acquisition calls
IPortableDevice slot20 (Close); failed acquisition skips Close but still
reaches GIT slot10 (RevokeInterfaceFromGlobal). The cookie is zeroed, and any
acquired interface is released. If the global GIT is absent, the native branch
returns without revocation. Close/Revoke HRESULTs are not checked on this path;
therefore successful traversal cannot prove successful device cleanup.

The static verifier now gates71 instructions. Added isolated
`wpd_lifecycle_reference.close_registered_device` with injected table/device
objects only. It follows get/Close/Revoke/Release order but deliberately reports
cleanup failures after attempting the remaining stages. It rejects zero and
invalid cookies before invoking the injected object and never replays a saved
cookie as camera state. No real COM sender or production call site was added.

Three synthetic tests cover normal order, all four failure stages and preflight
rejection. This closes a lifecycle reference, not the full session state machine
or proof of live-state freshness. No devices enumerated, sessions opened, Canon
code executed or installed files modified.

### Remote/event mode predicates and retry limits —20261011

`event_mode_plan_reference.plan_event_modes` reproduces the mode-selection
arithmetic at4c740 from explicit observed internal transport kind and two
predicate results. Remote base is5 for kind2, otherwise1; a nonzero timer
predicate adds bit10; kind4 then overrides the whole result with41. Event mode
is1 for a nonzero helper predicate, otherwise2. No model-to-transport inference
or assumption that all WPD devices use the same modes was added.

33 hash-gated static assertions link those predicates to interface90/9114 and
b4/9115, each carrying exactly one uint32 mode parameter via no-data2f8.
The reference returns an immutable command plan only; it executes no setup.
Two fixture-free tests cover24 mode combinations and invalid/inferred inputs.

Additional control-flow evidence: remote return81 jumps back before the
ordinary retry counter increment, so the visible ten-attempt bound does NOT
bound that case. After initial GetEvent processing, model getter return7 also
loops back to event reception without a local bound visible in this region.
An independent backend must not reproduce these as unbounded waits or infer
successful/fresh state merely from looping. Predicate meaning, total session
setup and empirical state freshness remain unresolved. Production unchanged.

### Correction: remote option is registry-backed, not a timer —20261011

Followed7c960 rather than inferring its meaning from the adjacent timer object.
It calls RegOpenKeyExA on HKLM\\Software\\Canon\\EDSDK and RegQueryValueExA
for `remoterel`, with a four-byte destination initialized to0. Successful query
copies the result; failed open/query returns0, and an opened key is closed.
The type destination is initialized to REG_DWORD but the returned type is not
checked in this native body. Do not overclaim strict native type validation.
The earlier "timer predicate" descriptions above are superseded by this evidence.

The pure planner input has been renamed `registry_option_enabled`; it remains
an explicit boolean, with no host registry reads/writes or inferred default
configuration. The arithmetic and tests are unchanged. This option's presence
does not establish its intended camera semantics or universal applicability.

Separately7cc20 is exactly Sleep(200), so the remote setup retry delay is now
attributed in milliseconds, unlike previously unresolved timer-unit waits in
other getters. The static verifier now gates45 instructions, four Windows
imports and both registry strings, without executing Canon code or reading the
system registry. Independent code must still bound the rc81 retry path.

### Event helper construction linked —20261011

Constructor43120 allocates a12-byte helper, invokes72df0 and saves it at
camera+37c. The destination link is verified beyond disconnected instruction
matches: EAX=address(camera+37c) at43236 remains unmodified through432db, where
that address is saved for the constructor's later output store4356b.
72df0 invokes the base helper constructor and installs vtablef8bd0. Slot0c
points to73000, exactly `mov eax,1; ret`. Base helper tablef179c instead points
to5edc0, exactly `xor eax,eax; ret`.

Thus the successful observed Windows CPtpCamera construction path selects
event mode1 in4c740. This does not justify declaring mode1 universal for other
platforms, alternate constructors, replaced helpers or allocation failures.
The pure planner retains its explicit helper predicate for those distinctions;
no production session or discovery code changed.

The mode static verifier now gates60 instructions, both virtual slots and the
destination-pointer dataflow check, in addition to registry/import evidence.
No helper constructor, DLL entry point, registry operation or device API ran.

### Transport-kind provenance from discovery record —20261011

43120 forwards its manager-record argument to base constructor28a0. At2911
the destination is camera+24;2914 selects the source record;2917/2921 copy
c5 dwords, exactly314 bytes. Therefore source field30c becomes camera field330
used by the remote-mode selector. The Windows WPD enumerator762b0 writes1 to
outer-record30c at76698. This is not the camera model ID, nor the inner adapter
kind2 at outer+c+30; confusing those distinct fields would select remote mode5
incorrectly for the observed WPD discovery path.

Added `plan_observed_windows_record`: consumes only the transport-kind word
from an exact314-byte immutable snapshot, then uses the proven successful
Windows helper predicate. It never dereferences the record's pointers/cookies
or treats captured records as valid live handles. The default observed WPD
kind1 plus false registry option yields remote1/event1; this is still a packet
plan, not permission to execute it or evidence of fresh registration state.

Two synthetic tests cover kind1/2/4 selection independent of unrelated record
bytes and reject other sizes/types. The static verifier now68 assertions
including the base copy and enum source. Source offsets for other discovery
kinds remain to be attributed; no universal transport-name mapping claimed.
