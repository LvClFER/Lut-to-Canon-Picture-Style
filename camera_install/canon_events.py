"""Pure Canon GetEvent data parsing; no transport, device access or state replay."""
import struct
from dataclasses import dataclass, field


def _snapshot(data, maximum):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("Canon event data must be a byte buffer")
    size = data.nbytes if isinstance(data, memoryview) else len(data)
    if size > maximum:
        raise ValueError("Canon event data exceeds the safety limit")
    return bytes(data)


@dataclass(frozen=True)
class ObservedRegistrationState:
    selector: int
    control: bytes = field(repr=False)


@dataclass(frozen=True)
class PropertyEvent:
    property_code: int
    value: bytes = field(repr=False)


@dataclass(frozen=True)
class EventBatch:
    properties: tuple[PropertyEvent, ...]
    continuation: bool


def decode_observed_rp_d163(value: bytes) -> ObservedRegistrationState:
    """Decode observed RP event layout only; no freshness or write authorization.

    The event includes an extra length word compared with the captured write
    value. Preserve control bytes exactly. Other bodies/layouts are unproven.
    """
    value = _snapshot(value, 44)
    if len(value) != 44:
        raise ValueError("Unvalidated D163 event layout")
    size, marker, selector = struct.unpack_from("<III", value)
    if size != 44 or marker != 1:
        raise ValueError("Unexpected D163 event prefix")
    return ObservedRegistrationState(selector, value[12:])


def decode_event_batch(data: bytes, max_value_bytes: int = 1024 * 1024) -> EventBatch:
    """Bounded C189 decoding and native 5ea80 continuation-marker semantics.

    Accept only eight-byte terminal records; native parsing is less strict.
    A completed batch is not evidence of state freshness or write permission.
    """
    if type(max_value_bytes) is not int or not 0 < max_value_bytes <= 16 * 1024 * 1024:
        raise ValueError("max_value_bytes must be positive")
    data = _snapshot(data, 16 * 1024 * 1024)
    output = []
    continuation = False
    offset = 0
    while offset < len(data):
        if len(data) - offset < 8:
            raise ValueError("Truncated Canon event header")
        length, code = struct.unpack_from("<II", data, offset)
        if length == 0 and not any(data[offset:]):
            break
        if code in (0, 0xffffffff):
            if length != 8:
                raise ValueError("Unsupported Canon event terminator layout")
            if any(data[offset + 8:]):
                raise ValueError("Non-zero data follows the Canon event terminator")
            continuation = code == 0xffffffff
            break
        if length < 8 or length > len(data) - offset:
            raise ValueError("Invalid Canon event record length")
        if code == 0xC189:
            if length < 12:
                raise ValueError("Truncated Canon property event")
            event_property = struct.unpack_from("<I", data, offset + 8)[0]
            value = data[offset + 12:offset + length]
            if len(value) > max_value_bytes:
                raise ValueError("Canon property event exceeds the safety limit")
            output.append(PropertyEvent(event_property, value))
        offset += length
    return EventBatch(tuple(output), continuation)


def extract_property_values(data: bytes, property_code: int, max_value_bytes: int = 1024 * 1024) -> list[bytes]:
    """Extract one property without logging its state or implying freshness."""
    if type(property_code) is not int or not 0 <= property_code <= 0xffffffff:
        raise ValueError("property_code must be an unsigned 32-bit integer")
    if type(max_value_bytes) is not int or not 0 < max_value_bytes <= 16 * 1024 * 1024:
        raise ValueError("max_value_bytes must be positive")
    batch = decode_event_batch(data, 16 * 1024 * 1024)
    output = [event.value for event in batch.properties if event.property_code == property_code]
    if any(len(value) > max_value_bytes for value in output):
        raise ValueError("Canon property event exceeds the safety limit")
    return output
