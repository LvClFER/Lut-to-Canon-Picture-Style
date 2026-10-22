"""Observed explicit-slot order and opt-in execution over injected adapters.

No session/state acquisition or live authorization. State control
must be supplied from independently validated live acquisition, never captures.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from .style_send_plan_reference import StyleSendPlan, plan_style_send
from .state_send_plan_reference import StateSendPlan, plan_slot_state
from .mtp_write_reference import transfer
from .style_readback_reference import decode_9189
from .registration_encode_reference import frame_property


@dataclass(frozen=True)
class RegistrationSequence:
    selector_cache_value: int
    style: StyleSendPlan
    state: StateSendPlan

    @property
    def wire_steps(self):
        # Explicit114 updates cache only.115 later serializes that selector.
        return ((self.style.opcode, self.style.parameters, self.style.data),
                (0x9110, (), self.state.data))


def plan_registration(carrier, control, handler_selector, supported_operations,
                      *, observed_marker, selected_cache_value):
    """Project114 ->203 ->115 for explicit21..23, preserving opaque control.

    selected_cache_value is the explicit uint32 supplied to114, not an inferred
    camera slot or string/name. Parameter0 is deliberately unsupported.
    """
    style = plan_style_send(carrier, handler_selector, supported_operations)
    state = plan_slot_state(control, handler_selector, observed_marker=observed_marker,
                            observed_selector=selected_cache_value)
    return RegistrationSequence(selected_cache_value, style, state)


@contextmanager
def ui_lock(commands):
    """Observed RP lock argument; one release attempt even after ambiguous failure."""
    try:
        commands.execute(0x911b, (1,))
        yield
    except BaseException as error:
        try:
            commands.execute(0x911c, ())
        except Exception:
            error.add_note('UI unlock also failed')
        raise
    commands.execute(0x911c, ())


def execute_and_compare(sequence, writer, commands, read_style, *, allow_write=False):
    """Observed UI lock -> style/state -> unlock -> content request, no retries.

    Caller owns the active session, live control provenance, advertised command
    support and authorization. This revised policy has no physical validation.
    read_style(handler) must return a transport-completed normalized style;
    equality alone does not prove freshness, visual output or family support.
    """
    if type(allow_write) is not bool or not allow_write:
        raise ValueError('Registration writes are disabled')
    if (not isinstance(sequence, RegistrationSequence) or not callable(read_style)
            or not callable(getattr(commands, 'execute', None))):
        raise ValueError('Require an explicit plan, command adapter and read callback')
    expected = validate_sequence(sequence)
    with ui_lock(commands):
        for stage, (opcode, parameters, payload) in zip(('style', 'state'), sequence.wire_steps):
            try:
                transfer(writer, opcode, parameters, payload)
            except Exception as error:
                error.add_note(f'Registration {stage} transfer failed; camera content is unconfirmed')
                raise
    observed = read_style(sequence.style.slot + 0x20)
    if type(observed) is not bytes or observed != expected:
        raise ValueError('Requested style content differs from registration plan')
    return True


def validate_sequence(sequence):
    """Pure framing/coherence check shared with preflight; proves no freshness."""
    if not isinstance(sequence, RegistrationSequence):
        raise ValueError('Require an explicit registration plan')
    style, state = sequence.style, sequence.state
    if (not isinstance(style, StyleSendPlan) or not isinstance(state, StateSendPlan)
            or type(style.slot) is not int or style.slot not in (1, 2, 3)
            or type(style.opcode) is not int or style.opcode not in (0x9110, 0x918a, 0x9192)
            or type(style.parameters) is not tuple or any(type(value) is not int for value in style.parameters)
            or type(style.data) is not bytes or type(state.property_code) is not int
            or type(state.handler_selector) is not int or state.handler_selector != style.slot + 0x20
            or type(state.extended) is not bool or type(state.data) is not bytes
            or type(sequence.selector_cache_value) is not int
            or not 0 <= sequence.selector_cache_value <= 0xffffffff):
        raise ValueError('Inconsistent registration plan types or slot')
    expected_property = state.handler_selector + (0xd142 if state.extended else 0xd13f)
    selector_offset = 16 if state.extended else 12
    if (state.property_code != expected_property
            or len(state.data) != (52 if state.extended else 40)
            or frame_property(expected_property, state.data[8:]) != state.data
            or int.from_bytes(state.data[selector_offset:selector_offset+4], 'little') != sequence.selector_cache_value
            or (state.extended and not any(state.data[12:16]))):
        raise ValueError('Inconsistent registration state framing or selector')
    serialized = sequence.style.data[8:] if sequence.style.opcode == 0x9110 else sequence.style.data
    if style.opcode == 0x9110:
        if style.parameters or frame_property(style.slot + 0xd16f, serialized) != style.data:
            raise ValueError('Inconsistent style property framing')
    elif style.parameters != (style.slot, len(serialized)):
        raise ValueError('Inconsistent direct style command parameters')
    expected = decode_9189(serialized)
    if not any(expected[:4]):
        raise ValueError('Disabled style cannot confirm registration')
    return expected
