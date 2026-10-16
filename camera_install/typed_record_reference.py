"""Offline typed-copy reference, not a carrier parser or camera builder."""


def copy_record(data: bytes, kind: int, mode: int = 0, expected_size: int = 0):
    """Return copied bytes or None for a known expected-size rejection."""
    if kind not in (1, 2, 3, 4, 65535):
        raise ValueError('Unsupported record type')
    if not isinstance(data, bytes) or not data:
        raise ValueError('Reference requires nonempty bounded bytes')
    if not isinstance(expected_size, int) or expected_size < 0:
        raise ValueError('Invalid expected size')
    if expected_size and len(data) != expected_size:
        if kind != 2 or len(data) > expected_size:
            return None
    result = bytearray(expected_size or len(data))
    width = {3: 2, 4: 4}.get(kind, 1)
    for offset in range(0, len(data) - width + 1, width):
        chunk = data[offset:offset + width]
        result[offset:offset + width] = chunk if mode in (0, 0x4949) or width == 1 else chunk[::-1]
    return bytes(result)


def output_record(data: bytes, kind: int, destination: bytes, mode: int = 0):
    """Model bounded output copies; None means a known size rejection."""
    if kind not in (1, 2, 3, 4, 65535):
        raise ValueError('Unsupported record type')
    if not isinstance(data, bytes) or not data or not isinstance(destination, bytes):
        raise ValueError('Reference requires nonempty bounded bytes')
    if not destination:
        raise ValueError('Empty output spans are not yet validated')
    if len(destination) > len(data) and kind != 2:
        return None
    result = bytearray(destination)
    width = {3: 2, 4: 4}.get(kind, 1)
    for offset in range(0, min(len(data), len(destination)) - width + 1, width):
        chunk = data[offset:offset + width]
        result[offset:offset + width] = chunk if mode in (0, 0x4949) or width == 1 else chunk[::-1]
    return bytes(result)
