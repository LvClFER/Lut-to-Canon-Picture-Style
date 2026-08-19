# Research status

## Considered validated in the tested contexts

- Dense PF3 `0x40001070/71` layout: 33³, 12-bit, 3-channel.
- Arbitrary dense LUT transport on EOS 1300D.
- Exact controlled `.cube → legacy compiled block` pipeline in the EOS Utility compiler context.
- EOS RP payload shape: 368-byte prefix + two 8192-byte blocks.
- RP Block1 carries the essential visible LUT transform in the validated carrier test.
- Manual EOS Utility registration + `0x01000203` payload replacement works on EOS RP.
- `0x00000115` must remain untouched by the loader.

## Still not claimed solved

- A stock standalone arbitrary-LUT PF3 that can simply be copied/registered on EOS RP without the helper.
- A direct no-EOS-Utility-transaction write path for the protected RP payload.
- Exact semantic equivalence between the experimental Chrome-style transforms and Fujifilm Color Chrome / Color Chrome FX Blue.
- General compatibility with other Canon generations.

## Reliability workaround

Restart EOS Utility between preset registrations. The exact retained process/transaction state causing occasional missed subsequent interceptions is not yet fully mapped.
