"""Strict portable reader for observed PF3 version3000; explicit caller keys.

No DLL loading/discovery, key constants, model selection or camera access.
Unsupported envelopes are rejected rather than interpreted as this version.
"""
import struct
from types import MappingProxyType
from .cipher_stream_reference import decode


def read_source_fields(raw, keys):
    """Return immutable host-ordered records usable by carrier constructors.

    Validate the exact envelope, unique records, final additive checksum and
    terminator before exposing any fields. This is not native parser parity
    for all PF2/PF3 versions. Cipher keys remain an external dependency.
    """
    if type(raw) is not bytes or not 32 <= len(raw) <= 16 * 1024 * 1024:
        raise ValueError('Require bounded immutable PF3 file bytes')
    if raw[:8] != bytes.fromhex('0000300050535000'):
        raise ValueError('Unsupported PF3 envelope')
    if struct.unpack_from('>I', raw, 8)[0] != len(raw) - 12:
        raise ValueError('PF3 envelope length differs')
    plain = decode(raw[12:], keys, 12)
    fields = {}
    cursor = 0
    checked = False
    while cursor + 8 <= len(plain):
        start = cursor
        identifier, kind, size = struct.unpack_from('>HHI', plain, cursor)
        cursor += 8
        if size > len(plain) - cursor:
            raise ValueError('Truncated PF3 record')
        value = plain[cursor:cursor + size]
        cursor += size
        if identifier == 0xffff:
            if kind != 0xffff or size or cursor != len(plain) or not checked:
                raise ValueError('Invalid PF3 terminator/checksum order')
            return MappingProxyType(fields)
        if checked:
            raise ValueError('Record after PF3 checksum')
        if identifier == 0xfffe:
            if kind != 4 or size != 4 or int.from_bytes(value, 'big') != sum(plain[:start]) & 0xffffffff:
                raise ValueError('Invalid PF3 additive checksum')
            checked = True
            continue
        if not 0x1000 <= identifier <= 0x10ff or identifier in fields:
            raise ValueError('Unsupported or duplicate PF3 record')
        if kind not in (2, 3, 4, 0xffff):
            raise ValueError('Unsupported PF3 record type')
        width = {3: 2, 4: 4}.get(kind, 1)
        if size % width:
            raise ValueError('Misaligned PF3 typed record')
        host = b''.join(value[i:i+width][::-1] for i in range(0, size, width))
        fields[identifier] = (kind, host)
    raise ValueError('Missing PF3 terminator')
