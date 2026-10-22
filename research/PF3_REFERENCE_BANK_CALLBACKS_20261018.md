# PF3 3000 reference banks and compact families 5/6

The previous family dispatcher blocked every source containing a high reference bank. This was broader than the verified PF3 format requires.

## Context and callback evidence

The native PF3 3000 constructor selects one format-context vtable. Its reference callbacks return zero without writing memory. Both compact-family-5 calls and the family-6 call use that callback entry. Static extraction verified the constructor assignment, the callback table entries, the return-only instructions and the two vtable immediate references in the executable code. Reference-bank contents cannot select a different callback through these records.

A private read-only-source experiment opened an existing 40-record PF3 containing 14 high reference records. It compared the original, reference-only edits and a private copy without the reference bank. Offline selectors covered EOS M3, EOS 1300D, EOS 7D Mark II and EOS 5DS, using borrowed genuine compact/modern descriptors. All twelve compilations kept the same context and produced the same carrier for each selector. Both observed callback buffers stayed unchanged; no high-bank field was read during the observed input/compile stages. The final lookup observers cover the verified record accessors and show active-field reads as positive controls; the earlier non-accessor probe is not used as absence-of-read evidence. Installed files and the original PF3 remained unchanged. Only owned hidden numerical host processes were used and closed; no camera API or camera session was involved.

## Independent integration

The pure dispatcher now accepts those records after strict PF3 3000 envelope, typed-record and checksum validation. It passes the original immutable field mapping to the existing builders, which consume active records. It neither deletes the reference bank nor copies its controls into active fields. Saved PF3/project files retain the reference records.

A separate replay forbade native-library calls and recovered equivalent cipher keys from a caller-owned self-contained PF3. It reproduced nine complete native carriers for the M3/1300D/7D-II coefficient routes. All twelve headers and second pairs matched. The three 5DS first-pair results keep the existing application dense-table policy, which intentionally differs from the unmodified native first-pair route; complete native parity is not claimed for those three results.

The synthetic regression checks high-bank invariance for every catalogued family-5/6 identifier and confirms other PF3 envelopes are still rejected. Existing old-style edit/project tests preserve reference values and ordering.

## Limits

This proof covers the strict version-3000 PF3 context. It does not establish a general PF2/subclass rule, arbitrary format conversion, physical installation on those bodies, firmware compatibility or clean-Windows deployment. Native execution was used only as a private development oracle; the shipped compiler does not load Canon code or contain its vtable addresses, keys, descriptors or captured data.

Private evidence: `CLASS56_PF3_CALLBACK_STATIC_20261018.json`, `CLASS56_HIGH_BANK_CALLBACK_V2_20261018/RESULTS.json`, and `INTEGRATED_HIGH_BANK_PROOF_V2_20261018.json`.

## Related class-6 Fine Detail correction

The family number alone does not determine Fine Detail rejection. The existing reconstructed `rejects_fine_detail_branch` policy uses the coefficient-policy identifier set. EOS 5DS and 5DS R are outside that set and use the 255-scale modern-reader class-6 path; 7D Mark II is inside it.

Three additional private native-oracle runs opened an application-generated Fine Detail PF3. The 5DS/5DS R selectors accepted it and emitted the 16752-byte layout with the Fine Detail selector; 7D-II rejected the model input for that source. The live family dispatcher now uses the existing rejection policy rather than rejecting all of class 6. Pure tests cover the two positive selectors, the negative selector and unsupported envelopes. This adds no physical-camera claim.

Private evidence: `CLASS6_FINE_DETAIL_POLICY_20261018/RESULTS.json`.
