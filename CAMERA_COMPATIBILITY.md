# Independent Canon camera compatibility

RC5 integrates the ten reconstructed serializer families into the existing editor. The 77 catalog entries identify known compiler dispatches; they are not 77 physically validated USB installations. Real operation capabilities, the live descriptor and the complete existing slot format are checked before writing.

Independent physical evidence: EOS RP, NC/Aerochrome in User Def. 3; the user also reported a successful RC4 User Def. 1 test. RC5 installed Aerochrome in User Def. 2 with an exact requested readback, saved baseline backup and completed session cleanup; the user confirmed the look and normal camera operation. Other bodies still need physical confirmation.

RC7 removes the overly broad class-5/6 reference-bank block for strict PF3 3000 and allows Fine Detail for the reconstructed 5DS/5DS R policy. These additions have offline compiler evidence only; they do not add physically validated bodies.

## Integrated families

| Family | Carrier bytes | Catalogued models |
| --- | ---: | --- |
| 1 | 8164 | EOS 5D; EOS-1D Mark II N |
| 2 | 8168 | EOS 30D; EOS Digital Rebel XTi / 400D / Kiss Digital X |
| 3 | 8528 | EOS-1D Mark III; EOS 40D; EOS-1Ds Mark III |
| 4 | 16720 | EOS Digital Rebel XSi / 450D / Kiss X2; EOS 5D Mark II; EOS Rebel XS / 1000D / Kiss F; EOS 50D |
| 5 | 16744 | EOS M3; EOS M10; EOS 7D; EOS Rebel T1i / 500D / Kiss X3; EOS-1D X; EOS Rebel T2i / 550D / Kiss X4; EOS-1D Mark IV; EOS 5D Mark III; EOS Rebel T3i / 600D / Kiss X5; EOS 60D; EOS Rebel T3 / 1100D / Kiss X50; EOS Rebel T4i / 650D / Kiss X6i; EOS 6D; EOS-1D C; EOS 70D; EOS Rebel T5i / 700D / Kiss X7i; EOS Rebel T5 / 1200D / Kiss X70 / Hi; EOS M; EOS Rebel SL1 / 100D / Kiss X7; EOS M2; EOS Rebel T6 / 1300D / Kiss X80; EOS Rebel T100 / 4000D / 3000D; EOS Rebel T7 / 2000D / 1500D / Kiss X90 |
| 6 | 16752 | EOS 7D Mark II; EOS Rebel T6s / 760D / 8000D; EOS Rebel T6i / 750D / Kiss X8i; EOS 5DS; EOS 5DS R |
| 7 | 16752 | EOS M50 / Kiss M; EOS M6 Mark II; EOS M200; EOS M5; EOS M100; EOS M6; EOS C300; EOS C200; EOS-1D X Mark II; EOS 5D Mark IV; EOS 80D; EOS Rebel T7i / 800D / Kiss X9i; EOS 6D Mark II; EOS 77D / 9000D; EOS Rebel SL2 / 200D / Kiss X9; EOS R / Ra; EOS RP; EOS Rebel T8i / 850D / Kiss X10i; EOS Rebel SL3 / 250D / 200D Mark II / Kiss X10; EOS 90D; EOS M50 Mark II / Kiss M2; EOS R100; EOS D2000C; EOS D6000C |
| 8 | 78980 | EOS-1D X Mark III |
| 9 | 83076 | EOS R5; EOS R3; EOS R6; EOS R7; EOS R10; EOS R50; EOS R6 Mark II; EOS R8; EOS R1; EOS R5 Mark II |
| 10 | 431616 | EOS C50; EOS R50 V; EOS R6 Mark III |

## Runtime requirements and limits

- The local candidate includes six authorized application-generated basic PF3 files for automatic initialization; opening an owned PF3 or project remains supported. No fixed cipher key arrays, Canon DLLs, ICCs, extracted metadata or captured payloads are distributed.
- The camera must advertise the reconstructed remote/event, property-request, UI-lock and state-write operations. The chosen style operation must be advertised by both WPD and DeviceInfo.
- Published RC7 requires existing slot Basic controls to match the serialized candidate. The local development candidate instead updates only the represented known words and requires a matching post-write event as well as exact style readback; this new path is not physically validated or approved for publication. Fineness/threshold are represented only where supported; all other words remain unchanged. See `research/KNOWN_BASIC_CONTROL_UPDATES_20261018.md`.
- Legacy families 1/2 require complete metadata read from that live slot, with the same base Picture Style already selected in camera. They do not request an unused D17F compiler descriptor. Metadata is base-specific and is never taken from a distributed Canon resource.
- Strict PF3 3000 reference-bank records (`0x9000..0x90ff`) are preserved in styles/projects. Families 5/6 compile the active records; the verified PF3 callback is a no-op, so reference-bank presence alone does not block installation. This is not a PF2 or unknown-format conversion rule. Fine Detail remains rejected for families 1–5 and coefficient-policy class-6 identifiers. The noncoefficient 5DS/5DS R class-6 path supports Fine Detail; this is compiler-policy evidence, not a physical test of those cameras.
- Unknown identifiers retain the reconstructed default class-7 dispatch and must pass full live grammar/descriptor checks. Non-default compact families use established dispatch facts; unambiguous live formats can supersede an older nominal mapping. Payload size alone never authorizes a write.
- Axis geometries outside the reconstructed mathematical domain are reported as unsupported. A catalog entry does not override this check.
- A style backup is saved before writing; it is not a complete restoration transaction. There is no automatic retry or restore. A stalled or failed driver session can require power/USB recovery.
- The pure compiler, PTP framing and injected-adapter sequence core are portable. Windows uses WPD. Mac development candidates include the ImageCaptureCore adapter, with GUI installation disabled pending native camera validation. An Android adapter is not shipped.
- Canon RAW rendering remains a separate optional Canon-dependent feature. Clean-Windows deployment is still unverified.
