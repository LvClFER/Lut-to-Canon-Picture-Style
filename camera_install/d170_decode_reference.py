"""Bounded reference for observed EDSDK 701d0 input conversion, not a sender."""
import struct


def decode_701d0(value: bytes) -> bytes:
    """Model two declared-size branches; reject inconsistent/truncated input.

    Static x86 attribution only. Does not prove camera-family acceptance.
    """
    if not isinstance(value,(bytes,bytearray,memoryview)):
        raise ValueError('D170 data must be a byte buffer')
    length=value.nbytes if isinstance(value,memoryview) else len(value)
    # Bound before copying: bytes(integer) and oversized views must never
    # allocate attacker-selected capacity in the independent decoder.
    if not 10<=length<=1024*1024+8:
        raise ValueError('D170 input outside bounded decoder domain')
    value = bytes(value)
    if len(value) < 10:
        raise ValueError("Missing D170 decoder fields")
    declared, valid = struct.unpack_from("<II", value)
    if not 8 <= declared <= 1024 * 1024:
        raise ValueError("Unbounded D170 declared size")
    # Native compares the first payload uint16 against the original uint32 size.
    payload_word = struct.unpack_from("<H", value, 8)[0]
    allocated = declared + 8 if payload_word == declared else declared
    if len(value) != allocated:
        raise ValueError("D170 input does not match the selected size branch")
    output = bytearray(allocated)
    struct.pack_into("<I", output, 0, valid)
    if valid:
        struct.pack_into("<I", output, 4, allocated - 8)
        output[8:] = value[8:]
    return bytes(output)
