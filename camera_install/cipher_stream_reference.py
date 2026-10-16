"""Portable symmetric stream transform; no key discovery or Canon constants.

Supplying keys remains a separate dependency. This module does not eliminate
that dependency by embedding proprietary tables or importing native tooling.
"""


def decode(data: bytes, keys: tuple[bytes, bytes], seed=0xB8ED) -> bytes:
    first, second = keys
    if len(first) != 512 or len(second) != 513:
        raise ValueError('Invalid research cipher tables')
    return bytes(value ^ first[(seed + i) % 512] ^ second[(seed + i) % 513] ^ 0x37
                 for i, value in enumerate(data))
