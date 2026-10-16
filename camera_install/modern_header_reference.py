"""Offline 17-node prefix reference with opt-in static missing-field defaults.

Not a whole carrier builder. Missing controls are rejected by default; opt-in
defaults are statically attributed but not natively verified. Encoded control bytes must be generated separately from records,
not taken from the outgoing carrier used for comparison.
"""
import struct

from .typed_record_reference import output_record


def build_modern17_prefix(records, encoded_control, total_size, *, allow_missing_controls=False):
    if type(allow_missing_controls) is not bool:
        raise ValueError('Explicit boolean missing-control policy required')
    if type(total_size) is not int or total_size not in (78980, 83076):
        raise ValueError('Unattributed modern layout')
    if type(encoded_control) is not bytes or len(encoded_control) != 252:
        raise ValueError('Require complete encoded control section')
    if encoded_control[:8] != struct.pack('<HHI', 0x2fff, 65535, 0):
        raise ValueError('Unexpected control section marker')
    result = bytearray(372)
    struct.pack_into('<II', result, 0, 1, total_size - 40)
    struct.pack_into('<I', result, 40, total_size - 40)

    def put(identifier, offset, capacity, optional=False):
        if identifier not in records:
            if optional:
                return False
            raise ValueError(f'Missing record {identifier:x}; fallback not implemented')
        kind, data = records[identifier]
        if type(kind) is not int or type(data) is not bytes or not data or len(data) > capacity:
            raise ValueError('Invalid or oversized record')
        value = output_record(data, kind, bytes(capacity), 0x4949)
        if value is None:
            raise ValueError('Record read would fail')
        result[offset:offset + capacity] = value
        return True

    for identifier, offset, capacity in (
            (0x1002, 8, 32), (0x1009, 44, 2), (0x1002, 46, 32),
            (0x100c, 368, 2)):
        put(identifier, offset, capacity)
    style = int.from_bytes(result[44:46], 'little')
    group_ok = [put(identifier, offset, 4, allow_missing_controls)
                for identifier, offset in ((0x1031, 80), (0x1030, 84),
                                          (0x1032, 88), (0x1033, 92))]
    if not all(group_ok):
        struct.pack_into('<IIII', result, 80, 0, 0 if style == 0x84 else 3, 0, 0)
    detail_ok = [put(identifier, offset, 4, allow_missing_controls)
                 for identifier, offset in ((0x1034, 104), (0x1035, 108))]
    # Native shift/or sequence reconstructs the original uint32, not bswap.
    for offset, lower, upper in ((84, 0, 7), (104, 1, 5), (108, 1, 5)):
        numeric = int.from_bytes(result[offset:offset + 4], 'little')
        if numeric < lower or numeric > upper:
            struct.pack_into('<I', result, offset, min(upper, max(lower, numeric)))
    if not all(detail_ok):
        fineness, threshold = {0x82: (2, 4), 0x84: (2, 2),
                               0x85: (2, 2), 0x88: (1, 1)}.get(style, (2, 3))
        struct.pack_into('<II', result, 104, fineness, threshold)
    struct.pack_into('<II', result, 96, 0xdeadbeef, 0xdeadbeef)
    struct.pack_into('<HH', result, 112, 0x4c, 252)
    result[116:368] = encoded_control
    return bytes(result)


def build_full33_prefix(records, encoded_control):
    """Observed56586 full33 layout; require complete controls, no defaults.

    The record/control envelope matches the normal modern17 prefix; only
    the duplicated data-size words change. No device support is inferred.
    """
    result = bytearray(build_modern17_prefix(records, encoded_control, 78980))
    struct.pack_into('<I', result, 4, 431616 - 40)
    struct.pack_into('<I', result, 40, 431616 - 40)
    return bytes(result)
