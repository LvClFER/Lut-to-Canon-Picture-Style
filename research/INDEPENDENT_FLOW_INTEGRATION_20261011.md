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
