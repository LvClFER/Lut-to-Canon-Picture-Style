"""Observed16752 compact header; offline only, complete controls required."""
import struct
from .modern_header_reference import build_modern17_prefix


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
