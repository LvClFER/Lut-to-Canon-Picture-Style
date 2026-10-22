"""Recover a stream from a mathematical identity or caller-owned PF3 records.

No file discovery, Canon runtime, embedded key tables, calibration asset or
camera access. Arbitrary styles are not assumed to contain either known shape.
"""
import struct

from .cipher_known_plaintext_reference import recover_equivalent_tables
from .pf3_source_reference import read_source_fields, write_source_fields
from .cipher_stream_reference import decode


def _rectangle(data):
    # Both stream tables cancel: p, p+512, p+513, p+1025 use each entry twice.
    view = memoryview(data)
    return bytes(a ^ b ^ c ^ d for a, b, c, d in
                 zip(view, view[512:], view[513:], view[1025:]))


def _recover_from_block(raw, plaintext, verify):
    if type(raw) is not bytes or not 32 <= len(raw) <= 16 * 1024 * 1024:
        raise ValueError('Require bounded immutable calibration PF3 bytes')
    if (raw[:8] != bytes.fromhex('0000300050535000')
            or int.from_bytes(raw[8:12], 'big') != len(raw) - 12):
        raise ValueError('Unsupported calibration PF3 envelope/length')
    fingerprint = _rectangle(plaintext[:1089])
    assert len(fingerprint) == 64
    searchable = _rectangle(raw)
    recovered = set()
    offset = 11
    candidates = 0
    while True:
        offset = searchable.find(fingerprint, offset + 1)
        if offset < 0:
            break
        candidates += 1
        if candidates > 32:
            raise ValueError('Too many calibration candidates')
        if offset + len(plaintext) > len(raw) - 20:
            continue
        try:
            keys = recover_equivalent_tables(plaintext[:2048], raw[offset:offset+2048], seed=offset)
            fields = read_source_fields(raw, keys)
        except ValueError:
            continue
        if verify(fields):
            recovered.add(keys)
    if len(recovered) != 1:
        raise ValueError('Calibration requires one unambiguous fully verified PF3')
    return recovered.pop()


def recover_identity_calibration(raw):
    """Recover from a full mathematical identity table, then verify file/checksum.

    No offset manifest or stored cipher tables; the complete typed identity must
    match, not just a known prefix. Arbitrary LUTs are not treated as identities.
    """
    axis = tuple((i * 4095 + 16) // 32 for i in range(33))
    identity = struct.pack('>3H', 12, 3, 33) + b''.join(
        struct.pack('>3H', r, g, b) for r in axis for g in axis for b in axis)
    host_identity = b''.join(identity[i:i+2][::-1] for i in range(0, len(identity), 2))
    return _recover_from_block(raw, identity,
        lambda fields: any(fields.get(i) == (3, host_identity) for i in (0x1070, 0x1071)))


def recover_known_fields_calibration(raw, known_fields):
    """Recover from caller-owned mathematical records, never guessed Canon fields.

    The caller supplies a contiguous ordered set produced by its own generator.
    Require all those complete records plus whole-file/checksum validation;
    encrypted LUT content may differ. This does not accept arbitrary PF3s.
    """
    zeros = (bytes(512), bytes(513))
    encoded = write_source_fields(known_fields, zeros)
    plaintext = decode(encoded[12:-20], zeros, 12)
    if not 2048 <= len(plaintext) <= 16384:
        raise ValueError('Require2048..16384 bytes of caller-owned contiguous records')
    return _recover_from_block(raw, plaintext,
        lambda fields: all(fields.get(i) == entry for i, entry in known_fields.items()))
