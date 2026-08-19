# Technical notes

## Dense Canon PF3 LUT

The dense LUT properties used in the research are:

- `0x40001070`
- `0x40001071`

Each property is **215,628 bytes**:

```text
6-byte header + 33 × 33 × 33 × 3 × 2 bytes
```

Header:

```text
0C 00 03 00 21 00
```

Observed interpretation:

- 12-bit values
- 3 channels
- 33 nodes per dimension

Dense indexing is `((R*33 + G)*33 + B)` with B fastest. Standard `.cube` row ordering uses R fastest, so conversion must account for the ordering difference.

## EOS 1300D legacy payload research

Historical EOS 1300D captures used a **16,744-byte** compiled payload:

```text
360-byte prefix
+ 8192-byte Block1
+ 8192-byte Block2
```

In the controlled encoder dataset, the two 8192-byte blocks were identical. The exact EOS Utility compiler path reproduced the known test blocks byte-for-byte for the controlled 12-probe dataset.

These 16,744-byte captures are 1300D data, not EOS RP captures.

## EOS RP compiled payload

The EOS RP compiled registration payload observed in the validated workflow is **16,752 bytes**:

```text
368-byte prefix
+ 8192-byte Block1
+ 8192-byte Block2
```

A controlled three-slot RP test showed:

- target legacy block in RP **Block1** + native RP carrier Block2 → visible target transform;
- native RP Block1 + target legacy block only in Block2 → insufficient;
- target block in both blocks → visible target transform.

Practical conclusion: **Block1 is essential in the tested carrier context**. This does not establish that Block2 is globally irrelevant.

## Current practical path

```text
.cube / Hald TIFF / PF3
→ dense Canon PF3
→ exact compiler path
→ legacy 8192-byte Block1
→ RP 16752-byte carrier
→ normal EOS Utility registration
→ intercept outgoing 0x01000203
→ replace payload
```

This is loader-assisted registration, not a claim that arbitrary dense-LUT PF3 files execute stock on EOS RP.

## `0x00000115`

This property is a 32-byte binary state/control blob in the observed registration sequence. It is not a text name property and must not be overwritten with ASCII names.

## Direct EDSDK experiments

Direct third-party writes to the protected RP `0x01000203` property were rejected in testing, including attempts that reproduced observed UI lock and `0x114 → 0x203 → 0x115` call ordering. Calling the same low-level setter from an injected EOS Utility process also did not reproduce the complete successful registration state.

For this reason, the supported experimental path keeps Canon's normal EOS Utility registration transaction and replaces only the outgoing payload at the validated point.
