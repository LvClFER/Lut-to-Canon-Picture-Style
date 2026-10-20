"""Observed16752 compact header; offline only, complete controls required."""
import struct
from .modern_header_reference import build_modern17_prefix
from .cipher_stream_reference import decode
from .packed10_reference import packed_index


def inspect_compact16752_style(normalized, keys):
    """Validate the observed normalized style grammar, not model/route support.

    All four encrypted tables must obey the packed10 bit/padding geometry.
    Matching format does not establish which pixel/cache compiler path to use.
    """
    if type(normalized) is not bytes or len(normalized) != 16720:
        raise ValueError('Require exact normalized compact style bytes')
    validity, size = struct.unpack_from('<II', normalized)
    if validity != 1 or size != 16712 or struct.unpack_from('<H', normalized, 8)[0] != size:
        raise ValueError('Compact style envelope differs')
    style = struct.unpack_from('<H', normalized, 10)[0]
    if style not in (0x81, 0x82, 0x83, 0x84, 0x85, 0x88):
        raise ValueError('Unobserved compact base style')
    if (struct.unpack_from('<II', normalized, 60) != (0xdeadbeef, 0xdeadbeef)
            or struct.unpack_from('<HH', normalized, 76) != (0x48, 252)
            or struct.unpack_from('<HHI', normalized, 80) != (0x2fff, 0xffff, 0)):
        raise ValueError('Compact style markers differ')
    used = {packed_index(r, g, b) for r in range(10) for g in range(10) for b in range(10)}
    for index in range(4):
        start = 336 + index * 4096
        table = decode(normalized[start:start+4096], keys, 0xb8ed if index % 2 == 0 else 0x33137)
        words = struct.unpack('<1024I', table)
        if any(word & 0xc0000000 or (slot not in used and word) for slot, word in enumerate(words)):
            raise ValueError('Compact packed table geometry differs')
    return dict(styleSelector=style, blockCount=4, gridNodes=10, compilerRouteEstablished=False)


def build_compact16752_prefix(fields, encoded_control):
    # 556fe branch: uint16 data size40, style42, name44; Basic76,
    # markers92/96, detail100/104, envelope108/112,100c364.
    modern=bytearray(build_modern17_prefix(fields,encoded_control,78980))
    struct.pack_into('<I',modern,4,16752-40)
    struct.pack_into('<I',modern,40,16752-40)
    result=bytearray(modern[:42]+modern[44:78]+modern[80:])
    struct.pack_into('<H',result,108,0x48)
    return bytes(result)


def build_older_compact_prefix(fields,encoded_control,total_size):
    """Observed class3/4/5 prefix geometry; not a family selector.

    Conservatively requires all controls accepted by the shared constructor,
    even when omitted from the output. Missing-field defaults are unproven.
    """
    if type(total_size) is not int or total_size not in (8528,16720,16744):
        raise ValueError('Unvalidated older compact layout')
    compact=build_compact16752_prefix(fields,encoded_control)
    if total_size==16744:
        result=bytearray(compact[:100]+compact[108:]);offset=100;marker=0x40
    else:
        result=bytearray(compact[:76]+compact[108:]);offset=76;marker=0x28
    struct.pack_into('<I',result,4,total_size-40)
    struct.pack_into('<H',result,40,total_size-40)
    struct.pack_into('<H',result,offset,marker)
    return bytes(result)
