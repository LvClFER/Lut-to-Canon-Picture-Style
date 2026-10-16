"""Unencrypted 512e0 control envelope reference, not a camera payload builder.

Static attribution only. Native cipher seed is 0x22e1 over bytes after the
first eight. No keys, Canon records or captured control blobs are supplied.
Oversized inputs are rejected instead of reproducing native partial output.
"""
import struct

from .typed_record_reference import output_record


def build_control_plain(records, size=252):
    """Build a little-endian synthetic envelope for records 100a then 100d.

records maps each optional ID to (kind, immutable bytes). This does not
interpret the contents or generate registration property 0x115.
"""
    if type(size) is not int or not 16 <= size <= 4096:
        raise ValueError('Control envelope must be bounded and contain both markers')
    if not isinstance(records, dict) or set(records) - {0x100a, 0x100d}:
        raise ValueError('Only statically selected control records are supported')
    result = bytearray(size)
    struct.pack_into('<HHI', result, 0, 0x2fff, 0xffff, 0)
    cursor = 8
    for identifier in (0x100a, 0x100d):
        if identifier not in records:
            continue
        entry = records[identifier]
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError('Expected kind/data tuple')
        kind, data = entry
        if type(kind) is not int or kind not in (1, 2, 3, 4, 65535):
            raise ValueError('Unsupported typed record')
        if type(data) is not bytes or not data:
            raise ValueError('Expected nonempty immutable record bytes')
        if cursor + len(data) + 16 > size:
            raise ValueError('Record and terminator do not fit; partial output forbidden')
        struct.pack_into('<HHI', result, cursor, identifier, kind, len(data))
        result[cursor + 8:cursor + 8 + len(data)] = output_record(
            data, kind, bytes(len(data)), 0x4949)
        cursor += 8 + len(data)
    struct.pack_into('<HHI', result, cursor, 0xffff, 0xffff, 0)
    return bytes(result)
