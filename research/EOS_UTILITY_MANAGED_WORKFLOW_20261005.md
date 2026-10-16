# Reflection-only Canon compiler workflow evidence

The installed EOS Utility3 executable is x86 managed .NET, importing mscoree,
not directly EdsCFParse. Its managed EDSDKLib.EdsCFParse class declares the
native APIs. Therefore static IL metadata is a more direct source for the
application-level call order than scanning native x86 instructions here.

Executable SHA256:
`728bcb732431855c411bf742d5f4e9c810666f5676b364f3448a6938d171d09e`.
New `camera_install/managed_compiler_calls.ps1` hash-gates this revision and
uses only Windows PowerShell/.NET Framework ReflectionOnlyLoadFrom and metadata
inspection. It never invokes Canon methods, runs EOS Utility, creates a session,
modifies installed files or generates an outgoing payload. Outputs are private.

Final V4 report:22874 methods inspected,677 selected call contexts, zero IL
decode errors and zero unresolved method tokens. Constructor and generic-method
contexts are included. Selected edges cover EdsCfp APIs, CustomFileParser
wrappers and EdsGet/SetPropertyData. This is NOT a full semantic reconstruction
of every application branch or a runtime transaction trace.

The initial V1 report had2025 decode errors from an incorrect two-byte opcode
prefix (`ff00` instead of `fe00`). V2 corrected decoding but did not count failed
generic-token resolution; V3 explicitly identified93 such misses. V4 supplies
generic type/method contexts and resolves all93. Earlier reports remain private
debug evidence and must not be used as complete call maps.

## Observed source-validation sequence

`EOSUtility.View.CameraSetting.PSFileRegister::valid`:

|IL offset|Operation|
|---|---|
|0018|CustomFileParser.Create(path)|
|0049|SetProperty01000001 using get_ModelID|
|0067|If available, SetProperty01000210 using get_PictureStyleLutParam|
|0079|GetProperty01000203 into a local result structure|
|008f|GetProperty0200 (name)|
|00a5|GetProperty4000100a (additional string field)|
|00c5|GetProperty0115 on the PF3 reference; clamp strength to7 later|

The wrapper Create(path) calls EdsCfpCreateRef(path,2,0,out) atIL002e, exactly
matching the offline lab's creation arguments. It releases any previous
reference first. The overload Create(type,id) calls EdsCfpCreateEmptyRef.

`EOSUtility.CaptureView::setCameraPictureStyleFile` similarly opens a path,
sets model01000001, name0200 and4000100a strings, optionally sets the live
descriptor01000210, then requests01000203. No preceding01000203 carrier
import appears in these inspected compilation sequences.

## Separate carrier-inspection path

`EOSUtility.PictureStyleCaption::getPictureSytleCaption` creates an EMPTY
reference using type777012786 (`2e505332`) and modelID, sets01000203 using
the supplied structure, and reads0200. This matches the DLL's carrier-import
role but is a different object/path from file validation above.

This distinguishes two operations previously easy to conflate:

-Compile a selected PF3 file using its model and descriptor.
-Import an existing carrier into an empty reference to read its caption.

The hypothesis that ordinary source validation first imports a camera carrier
to supply1007 is not supported by these sequences. It is not disproved for
every old application version, wrapper, or other transaction path. Native1007
writers still only show carrier imports in the currently mapped code; its
semantic content remains unresolved, and no synthetic1007 is an install fix.

0115 above is a PF3-reference property, not the opaque EDSDK registration-state
blob. Neither was modified during this read-only analysis.

Private source: `../tmp/PF3_FIELD_EXPERIMENTS_20261004/EOS_UTILITY_MANAGED_CALLS_V4_20261005.json`.
Next: follow actual registration-command callers and descriptor acquisition
through managed fields, distinguish legacy supported routes from retained
read-only carrier helpers, and match each wrapper's property marshalling with
the native record schema. No camera execution is needed for that static work.

## Registration and descriptor follow-up (2026-10-06)

The reflection-only tool now retains full instructions for25 selected methods
and the writer of CameraModel.pictureStyleLutParam. It resolves field names as
well as method names. Calls are filtered by actual call/newobj/function-pointer
opcodes: an intermediate report counted45 matching FIELD accesses as calls;
that was corrected before using the registration evidence.

Signed short integers/branches and switch destinations are now decoded, and
every branch target is checked against an instruction boundary. The V3
registration report again parses22874 methods with zero decoding errors and
zero unresolved method targets. A separate Python extractor independently
identifies21 simple subtract-and-switch tables in the25 selected methods.
It rejects incomplete reflection reports or out-of-boundary destinations.

### Slot and apply operations

PSFileRegister.getPsUserParameter maps user slots1/2/3 to33/34/35 (21/22/23 hex).
PSFileRegister.Apply checks `modified`, obtains that slot value, and calls
CameraController.actionPerformed with these property events in source order:

1.0114 and the selected user Picture Style.
2.If userParamModified,01000203, the slot parameter, and pictureStyleUserParam.
  The event size comes from Marshal.SizeOf of that structure.
3.0115, the slot, and the default Picture Style description structure.

These are static event submissions, not proof of live transport ordering;
the controller/command dispatch still needs to be followed. No0115 was read,
modified, constructed or sent during this analysis. The previously observed
camera-registration buffer must remain untouched even where Canon's own
managed code names a description structure.

SetDevelopParamCommand.execute is another inspected command: for user-set
styles65/66/67 it submits01000203 with get_PictureStyleData().Length and the
original byte array. This distinguishes buffer length from slot selection.
It is not yet evidence that PSFileRegister.Apply dispatches this particular
command; the methods must not be conflated without the controller edge.

### Descriptor ownership

CameraModel.setProperty has a simple switch subtracting01000210 atIL02e2;
its case0 branches toIL104e. That branch creates a new byte array using the
received length argument and copies the incoming pointer atIL1065. The result
is CameraModel.pictureStyleLutParam; the getter returns the stored field.
This confirms a length-driven descriptor cache in this application revision,
not a fixed7772/15076-byte universal descriptor. File compilation then passes
this array to Canon01000210 as already observed in valid/setCameraPictureStyleFile.

Private evidence: EOS_UTILITY_REGISTRATION_IL_V3_20261006.json and
EOS_UTILITY_MANAGED_SWITCHES_20261006.json. Python compilation and253 tests pass.
Remaining: resolve the controller's event-to-command edge and the descriptor
read command, while keeping file compilation, cached capabilities and camera
transport separate. These static findings do not add physical camera support.

### Registration command and transport (2026-10-06)

The transport reflection report resolves string literals as well as call targets.
Apply submits the literal `setproperty`; the controller constructs
SetPropertyCommand and submits it through StoreAsync. StoreAsync forwards the
command to Processor.set_Command. This is not SetDevelopParamCommand.

SetPropertyCommand retains the event and reads its PropertyID, Param, Size and
Data before CameraModel.UploadProperty (IL00bb). UploadProperty selects the
camera/flash handle, checks IsBulb, then calls EdsSetPropertyData at IL0036 with
its four original arguments. No compiler, table conversion or payload rewriting
appears inside this method. Event-data marshalling remains a separate edge to
verify; this statement does not assert that an arbitrary managed object is
already identical to its final native representation.

DownloadProperty calls EdsGetPropertySize (IL002d), allocates that returned
length, calls EdsGetPropertyData (IL0044), and passes pointer plus length to
setProperty (IL0053). The previously mapped descriptor cache therefore follows
a size-driven read path rather than an assumed fixed descriptor size.

Private evidence: EOS_UTILITY_COMMAND_DISPATCH_20261006.json and
EOS_UTILITY_TRANSPORT_IL_20261006.json; 22874 methods, 677 selected call contexts,
zero instruction decoding errors and zero unresolved method targets. Only
reflection-only metadata was inspected: no application, session or write ran.

The event report identifies a real intermediate conversion: Apply's01000203
event uses constructor token100683591, which calls EDSDK.CnvUsersetData at
IL0016, stores its returned byte array and uses that array's Length as Size.
Other constructor overloads directly retain their supplied data/size. Therefore
the transport method's pass-through behavior must not be generalized backwards
to the compiler structure: CnvUsersetData is the next required static edge.
Private evidence: EOS_UTILITY_EVENT_BUFFER_IL_20261006.json. The controller's
`setproperty` comparison atIL0460 branches toIL0a76, the already observed
SetPropertyCommand construction path.

### Userset copy and layout

CnvUsersetData uses a constant40-byte prefix, marshals EdsUsersetData into
scratch memory, copies the first40 bytes, then copies dataSize bytes from
the managed data array after that prefix. It returns40+dataSize bytes; there
is no LUT interpolation or quantization in this method. Allocation reserves
40+max(dataSize,IntPtr.Size), a scratch-memory detail rather than output length.

Reflection-only field metadata identifies sequential EdsUsersetData fields:
UInt32 Valid, UInt32 dataSize, szCaption string with MarshalAs23/SizeConst32,
and byte[] data with MarshalAs30/SizeConst1. The first two scalar fields plus
the inline32-character ANSI caption explain the40-byte prefix. This does not
authorize manufacturing registration state or transplanting camera carriers.
The parser's GetProperty overload100663362 still needs inspection to establish
how its native output is split into this structure.

Private evidence: EOS_UTILITY_USERSET_CONVERSION_IL_20261006.json and
EOS_UTILITY_USERSET_LAYOUT_IL_20261006.json, both complete without decoder or
method-resolution errors. userset_buffer_reference.py intentionally treats
the40-byte header as opaque supplied evidence, reproduces only bounded copying,
and is not connected to production camera installation. py_compile and255
unit tests pass; tests prove copying/validation, not physical registration.

### Parser-to-userset edge closed

GetProperty overload100663362 obtains the native property size, allocates that
size, calls EdsCfpGetPropertyData, and on success calls MarshalPtrToUsersetData
(IL0033). That helper reads the EdsUsersetData structure, allocates a data array
of dataSize, copies40+dataSize bytes from the native pointer, and copies the
tail at offset40 into the managed data array. The return conversion described
above then restores the same tail. Thus this managed edge does not explain
LUT normalization: that must be investigated earlier in native compilation.

split_userset_buffer validates the x86 little-endian size field at offset4,
retains the40-byte header without constructing it, and rejects inconsistent
lengths. Both existing full33 stock laboratory outputs (431616 bytes) split
to431576 bytes of data and reconstruct byte-for-byte. This is a bounded
opaque-header copy proof, not a test of ANSI caption marshalling or installation.
The private parser/unmarshal reports decode completely without unresolved calls.

The transport-signatures report independently confirms GetProperty100663362
returns EdsUsersetData by reference; MarshalPtrToUsersetData returns that
structure and CnvUsersetData returns byte[]. EdsSetPropertyData100663595 takes
IntPtr, UInt32 propertyID, Int32 parameter, Int32 size and System.Object data.
That last signature does not by itself prove CLR interop attributes or ANSI
caption round-trip fidelity. The reflector now records parameter and return
types, including selected declarations without IL bodies. The native compiler
result's Valid field is checked in PSFileRegister.valid atIL015a; a nonzero
value stores the complete structure atIL0163 and enables userParamModified.
No additional dense-grid acceptance test appears in this managed check.

Private evidence: EOS_UTILITY_TRANSPORT_SIGNATURES_20261006.json; 257 tests pass.
