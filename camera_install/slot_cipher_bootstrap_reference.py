"""RP stream recovery from observed style bytes and owned mathematical blocks.

No file discovery, native loading, persisted keys, device access or permission
to write. Unsupported source parameters fail rather than guessing a stream.
"""
import hashlib
from .cipher_known_plaintext_reference import recover_equivalent_tables
from .cipher_stream_reference import decode
from .compact_carrier_reference import compact_upstream_grid,pack_compact_pixel_grid
from .compact_header_reference import inspect_compact16752_style
from .descriptor_import_reference import normalize_observed_raw
from .rp_preflight_reference import RP_DESCRIPTOR_SHA256


NORMALIZED_RP_SHA256='e1af5fd5f6f3e2c257966e77b7966105e39c4d2f68df61ee282d5bb0a62f0031'


def owned_parameterless_blocks():
    """Build both complete known blocks from application-owned fields/math."""
    import canon_engine as engine
    data={identifier:value for identifier,(_kind,value) in engine._generated_pf3_fields('Neutral').items()}
    return tuple(pack_compact_pixel_grid(data,compact_upstream_grid(bytes(14796),0x84,index),
        mode=index%2+1,style=0x84,pixel_scale=256) for index in (2,3))


def recover_rp_slot_calibration(style,descriptor):
    """Recover only when full owned blocks and the normalized descriptor agree.

    The two descriptor digests identify validated data, not embedded key tables
    or plaintext resources. They prevent a guessed pixel shape becoming a key.
    """
    if type(style) is not bytes or len(style)!=16720:
        raise ValueError('Require complete normalized compact RP style')
    if (type(descriptor) is not bytes or len(descriptor)!=15076
            or hashlib.sha256(descriptor).hexdigest()!=RP_DESCRIPTOR_SHA256):
        raise ValueError('Unverified RP descriptor profile')
    first,second=owned_parameterless_blocks()
    keys=recover_equivalent_tables(first,style[8528:12624],seed=0xb8ed)
    if (decode(style[8528:12624],keys,0xb8ed)!=first
            or decode(style[12624:16720],keys,0x33137)!=second):
        raise ValueError('Slot does not contain both complete owned mathematical blocks')
    normalized,_=normalize_observed_raw(descriptor,keys)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_RP_SHA256:
        raise ValueError('Recovered stream does not verify the full RP descriptor')
    inspect_compact16752_style(style,keys)
    return keys
