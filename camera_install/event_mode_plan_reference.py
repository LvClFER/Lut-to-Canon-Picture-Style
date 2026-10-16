"""Pure known-revision 4c740 mode selection; no device or session access.

Inputs are observed internal predicates, not inferred camera model names.
This plan supplies no freshness, authorization, or complete setup sequence.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class EventModePlan:
    remote_mode: int
    event_mode: int
    commands: tuple[tuple[int, tuple[int, ...]], ...]


def plan_event_modes(transport_kind, *, helper_predicate, registry_option_enabled):
    if type(transport_kind) is not int or not 0 <= transport_kind <= 0xffffffff:
        raise ValueError('Require observed uint32 transport kind')
    if type(helper_predicate) is not bool or type(registry_option_enabled) is not bool:
        raise ValueError('Require explicit observed predicate results')
    remote = 5 if transport_kind == 2 else 1
    if registry_option_enabled:
        remote |= 0x10
    # Native override occurs after registry option bit selection, not before it.
    if transport_kind == 4:
        remote = 0x41
    event = 1 if helper_predicate else 2
    return EventModePlan(remote,event,((0x9114,(remote,)),(0x9115,(event,))))


def plan_observed_windows_record(record, *, registry_option_enabled):
    """Observed 314-byte manager record -> successful Windows helper plan.

    This is an internal discovery record, NOT a descriptor/carrier or saved
    live camera state. Pointers/cookies in it are never dereferenced or reused.
    Only the source30c -> camera330 transport-kind field is consumed.
    """
    if not isinstance(record,(bytes,bytearray,memoryview)):
        raise ValueError('Require bounded manager-record bytes')
    size=record.nbytes if isinstance(record,memoryview) else len(record)
    if size!=0x314:
        raise ValueError('Require exact observed Windows record geometry')
    kind=struct.unpack_from('<I',bytes(record),0x30c)[0]
    return plan_event_modes(kind,helper_predicate=True,
                            registry_option_enabled=registry_option_enabled)
