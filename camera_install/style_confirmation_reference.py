"""Content verification only; no transport, freshness or visual-success claim."""
import struct
from .registration_encode_reference import MAX_TRANSFER_BYTES
from .style_readback_reference import decode_9189


def verify_readback_content(carrier, readback):
    """Compare a compiler carrier to a completed 9189 wire dataset.

    Exclude the carrier's 36-byte desktop caption, as the native send path
    does. Caller must independently establish session, slot and post-write
    freshness. Matching bytes cannot establish those facts or image appearance.
    Invalid/disabled styles are not accepted as successful confirmation.
    """
    if not isinstance(carrier, (bytes, bytearray, memoryview)):
        raise ValueError('Require compiler carrier bytes')
    size = carrier.nbytes if isinstance(carrier, memoryview) else len(carrier)
    if not 40 <= size <= MAX_TRANSFER_BYTES - 8:
        raise ValueError('Carrier outside bounded reference domain')
    carrier = bytes(carrier)
    validity, payload_size = struct.unpack_from('<II', carrier)
    if not validity or payload_size != len(carrier) - 40:
        raise ValueError('Require valid carrier with exact envelope length')
    observed = decode_9189(readback)
    expected = struct.pack('<II', validity, payload_size) + carrier[40:]
    if observed != expected:
        raise ValueError('Readback content differs from compiled style')
    return True
