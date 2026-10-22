# Known Basic control update candidate

This local candidate adds an explicit `--update-known-basic-controls` option to
experimental independent registration. The option requires registration scope;
the Windows layout candidate keeps it disabled in the editor, as requested by
the user. The published RC7 and this editor require matching controls. There is
no physical validation of the optional diagnostic update path yet; it is not
included in the normal camera workflow.

The candidate copies the observed selected-slot control block and replaces only
the documented Contrast, Strength, Saturation, Color Tone, Fineness and Threshold
words represented by that layout. Source values must have the exact known name,
offset, signedness and range. Unknown bytes, marker and selector are preserved.
Mixed observation/wire layouts cannot be updated. Legacy layouts retain their
four represented controls; no missing words are fabricated.

The exclusive baseline style backup must succeed before either write. After
style and state transfer and interface unlock, confirmation requires both exact
requested style content and an exact event for the intended changed control block.
Old-state echoes before that event are tolerated; subsequent reversions, unknown
word changes and contradictory observations fail. Event drains are bounded and
there are no directed D160–D165 requests, retries or automatic restoration.
The event proves content correspondence, not universal state freshness.

The existing identical-style guard remains: this does not enable state-only
updates or repeated identical-style transfers. The backup is not a complete
restoration transaction. Physical validation needs a new specific authorization
because it changes control words that the released path only preserves.

Local tests cover framing, word ranges, opaque-byte preservation, default refusal,
late/missing events, reversion, contradictory content, backup before writing,
exactly two transfers, cleanup on failure and supervisor confirmation checks.
Injected devices establish software behavior, not real-camera acceptance.

The follow-up `test_known_control_updates_reach_each_family_with_both_state_layouts`
uses actual independently compiled jobs for one identifier in every serializer
family, then runs the shared registration controller for both 24-byte and 32-byte
observations: 20 simulated combinations. Each checks every represented Basic
word, exact preservation of all other words, exclusive baseline backup before
both transfers, one unlock, the exact before/after confirmation arguments and
absence of opaque data in the report. Modern-only words are not invented in
legacy states. The run passed; log `KNOWN_BASIC_TEN_FAMILIES_20261018.log` remains
private. Runtime code was unchanged, so this adds evidence for the existing local
integrated candidate without generating another build or release.
