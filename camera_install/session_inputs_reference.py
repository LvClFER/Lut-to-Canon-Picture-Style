"""Completed GetEvent -> compiler inputs and opaque slot observations.

No camera/cache access, state replay or freshness inference. A completed event
may be retained; these observations never authorize a registration operation.
"""
from dataclasses import dataclass, field
import struct
from .canon_event_receive_reference import CompletedEvents
from .canon_events import PropertyEvent
from .compiler_input_events_reference import camera_id_from_d116, descriptor_from_d17f


@dataclass(frozen=True)
class SlotObservation:
    handler_selector: int
    marker: int
    selector: int
    control: bytes = field(repr=False)


@dataclass(frozen=True)
class SessionInputs:
    camera_id: int | None
    raw_descriptor: bytes | None = field(repr=False)
    slots: tuple[SlotObservation, ...]


def collect_inputs(completed):
    """Reject contradictions, do not silently select stale/latest state.

    D163..165 share the known-revision extended decoder. Their44-byte event
    geometry is decoded structurally, without declaring support for a model.
    Missing inputs remain explicit; parsing does not manufacture defaults.
    """
    if (not isinstance(completed, CompletedEvents)
            or type(completed.properties) is not tuple or len(completed.properties) > 65536
            or type(completed.batch_count) is not int or not 1 <= completed.batch_count <= 256
            or type(completed.received_bytes) is not int or not 0 <= completed.received_bytes <= 16*1048576):
        raise ValueError('Require bounded completed event batches')
    values = {}
    for event in completed.properties:
        if (not isinstance(event, PropertyEvent) or type(event.property_code) is not int
                or type(event.value) is not bytes):
            raise ValueError('Require immutable typed property observations')
        code = event.property_code
        if code == 0xd116:
            value = camera_id_from_d116(event.value)
        elif code == 0xd17f:
            value = descriptor_from_d17f(event.value)
        elif code in (0xd163, 0xd164, 0xd165):
            if len(event.value) != 44:
                raise ValueError('Unestablished slot-state event geometry')
            size, marker, selector = struct.unpack_from('<III', event.value)
            if size != 44:
                raise ValueError('Slot-state event length differs')
            value = SlotObservation(code-0xd142, marker, selector, event.value[12:])
        else:
            continue
        if code in values and values[code] != value:
            raise ValueError('Contradictory session input observations')
        values[code] = value
    return SessionInputs(values.get(0xd116), values.get(0xd17f),
                         tuple(values[code] for code in (0xd163, 0xd164, 0xd165) if code in values))
