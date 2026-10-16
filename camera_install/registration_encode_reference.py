"""Independent references for hash-known EDSDK serializers, not a send API.

Inputs are normalized structures, NOT raw event values or camera carriers.
These functions neither acquire live state nor establish its freshness.
"""
import struct

MAX_TRANSFER_BYTES = 1024 * 1024


def _buffer(value, minimum: int, maximum: int) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise ValueError('Expected a byte buffer')
    size = value.nbytes if isinstance(value, memoryview) else len(value)
    if not minimum <= size <= maximum:
        raise ValueError('Invalid byte buffer size')
    return bytes(value)


def frame_property(property_code: int, serialized: bytes, *, capacity: int | None = None) -> bytes:
    """Reference for 6a450's data buffer, not a complete PTP transaction.

    The serialized value already includes its own length word. 6a450 adds
    total length and the property code before copying that value unchanged.
    """
    if type(property_code) is not int or not 0 <= property_code <= 0xffffffff:
        raise ValueError('Property code is outside uint32')
    serialized = _buffer(serialized, 4, MAX_TRANSFER_BYTES - 8)
    if capacity is not None and (type(capacity) is not int or capacity < len(serialized)+8):
        raise ValueError('Transfer capacity would truncate the property packet')
    if struct.unpack_from('<I', serialized)[0] != len(serialized):
        raise ValueError('Serialized property length does not match buffer')
    return struct.pack('<II',len(serialized)+8,property_code)+serialized


def encode_style(normalized: bytes) -> bytes:
    """Reference for 72ba0: validity/dataSize/payload -> length/validity/payload."""
    normalized = _buffer(normalized, 8, MAX_TRANSFER_BYTES - 8)
    validity, size = struct.unpack_from('<II', normalized)
    if size != len(normalized) - 8:
        raise ValueError('Normalized style dataSize does not match payload')
    return struct.pack('<II', size + 8, validity) + normalized[8:]


def encode_state(normalized: bytes, *, extended: bool) -> bytes:
    """References for 72ce0/72d40: prepend length, preserve all input words."""
    if type(extended) is not bool:
        raise ValueError('State representation must be explicitly boolean')
    required = 40 if extended else 28
    normalized = _buffer(normalized, required, required)
    words = list(struct.unpack('<' + 'I' * (required // 4), normalized))
    return struct.pack('<I', required + 4) + struct.pack('<' + 'I' * len(words), *words)
