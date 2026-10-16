"""Observed explicit-slot call order projected to offline wire plans only.

No session/state acquisition, live authorization or execution. State control
must be supplied from independently validated live acquisition, never captures.
"""
from dataclasses import dataclass
from .style_send_plan_reference import StyleSendPlan, plan_style_send
from .state_send_plan_reference import StateSendPlan, plan_slot_state


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
