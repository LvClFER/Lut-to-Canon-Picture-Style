"""Offline reference for CnvUsersetData's copy stage, not a camera builder.

Header bytes must come from evidence. This module neither creates Canon
metadata nor interprets registration property 0x115. It does not marshal a
managed structure: it reproduces only the observed 40-byte header/data copy.
"""
import struct


def split_userset_buffer(buffer: bytes) -> tuple[bytes, bytes]:
    """Validate native x86 dataSize and split, preserving the opaque header."""
    if not isinstance(buffer, bytes):
        raise TypeError('Require immutable byte evidence')
    if len(buffer) < 40:
        raise ValueError('Truncated userset header')
    size = struct.unpack_from('<I', buffer, 4)[0]
    if size != len(buffer) - 40:
        raise ValueError('Declared userset size does not match evidence')
    return buffer[:40], buffer[40:]


def copy_userset_buffer(header: bytes, data: bytes, data_size: int) -> bytes:
    if not isinstance(header, bytes) or not isinstance(data, bytes):
        raise TypeError('Require immutable byte evidence')
    if len(header) != 40:
        raise ValueError('Observed userset header is exactly 40 bytes')
    if type(data_size) is not int or not 0 <= data_size <= len(data):
        raise ValueError('Data size must fit the supplied evidence')
    return header + data[:data_size]
