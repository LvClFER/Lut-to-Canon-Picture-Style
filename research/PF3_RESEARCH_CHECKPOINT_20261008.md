# Research checkpoint — 2026-10-08

Purpose: distinguish useful verified results from unfinished internal analysis.
This is not a release checklist or a claim of universal camera support.

## Evidence available

- Current automated suite: 390 tests passed in the preceding recorded run.
- Mode-two synthetic polynomial/curve chains have independent CLUT comparisons;
  tested matrices, selectors and curve cases are enumerated in the detailed log.
- ICC lookup controls retain equivalence after tag-directory reordering and
  payload relocation; shared intent tags are structurally validated.
- PF2/PF3 checksum, record-bank and getter error handling have bounded tests.
- The 17-node packer requires an object receiver. Its normal caller constructs
  a wrapper around an owner's record collection; initialization alone is invalid.

## Not established

- Numeric boundary equivalence for the new standalone 17-node probe: the first
  invocation failed because it lacked the required receiver. Do not reuse it as
  a successful result or run it unchanged.
- Universal acceptance across Canon cameras, independent replacement of Canon
  runtime libraries, or complete understanding of all PF3 fields.
- Physical validation of these new mathematical and static findings.

## Remaining research questions

1. Attribute the record-container owner and obtain the normal packer receiver
   from an owned offline compiler invocation before retrying boundary tests.
2. Locate the origin of content state 1; current store scans are not proof that
   the state is unreachable.
3. Obtain a genuine legacy 0x1007 fixture if a relevant old-route failure needs
   investigation; synthetic zero/FF records are not substitutes.

## Practical relevance gate

Before further deep investigation, state the concrete compatibility failure or
production defect the experiment can resolve. Preserve functional production
paths. A passing mathematical reference alone does not justify a new build.
User has questioned the value of continuing deep analysis; a proposed pause is
awaiting an explicit decision. This checkpoint does not pause or complete the
persistent goal and does not authorize a change of scope.

Detailed evidence: PF3_DESCRIPTOR_CAPABILITY_WORDS_20261007.md and private
PF3_FIELD_EXPERIMENTS_20261004 outputs. No Canon fixtures included here.
