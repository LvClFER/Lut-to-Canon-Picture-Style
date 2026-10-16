"""Offline old-layout dense9 composition with caller-supplied genuine metadata.

No device/model dispatch, Canon discovery/execution or installation authority.
The opaque 1007 record and cipher tables are explicit external dependencies.
"""
import struct
from .cipher_stream_reference import decode
from .control_section_reference import build_control_plain
from .typed_record_reference import output_record
from .legacy_dense9_reference import dense9_flag0
from .packed9_reference import pack9_dense9


def build_legacy_dense9_carrier(fields, keys, metadata, *, total_size):
    if type(total_size) is not int or total_size not in (8164,8168):
        raise ValueError('Require explicitly observed old layout')
    if type(metadata) is not bytes or len(metadata)!=1460 or struct.unpack_from('<I',metadata)[0]!=1460:
        raise ValueError('Require complete externally supplied genuine-format1007 metadata')
    if type(fields) is not dict:
        raise ValueError('Require typed host-ordered source fields')

    def field(identifier, capacity, kind):
        entry=fields.get(identifier)
        if type(entry) is not tuple or len(entry)!=2 or entry[0]!=kind or type(entry[1]) is not bytes:
            raise ValueError(f'Missing or incorrectly typed source {identifier:x}')
        if not entry[1] or len(entry[1])>capacity:
            raise ValueError('Source field exceeds observed capacity')
        value=output_record(entry[1],kind,bytes(capacity),0x4949)
        if value is None:
            raise ValueError('Source field cannot fill the required geometry')
        return value

    name=field(0x1002,32,2)
    style_bytes=field(0x1009,2,3)
    style=int.from_bytes(style_bytes,'little')
    if style not in range(0x81,0x86):
        raise ValueError('Unvalidated old dense-source style')
    curve=field(0x1018,300,4)
    matrix=field(0x1029,240,4)
    control=build_control_plain({i:fields[i] for i in (0x100a,0x100d) if i in fields})
    control=control[:8]+decode(control[8:],keys,0x22e1)
    result=bytearray(total_size)
    struct.pack_into('<II',result,0,1,total_size-40)
    result[8:40]=name
    struct.pack_into('<H',result,40,total_size-40)
    result[42:44]=style_bytes
    result[44:76]=name
    if total_size==8164:
        metadata_offset,curve_offset,control_offset,flags_offset,grid_offset=76,1536,2076,2328,2332
    else:
        struct.pack_into('<I',result,76,0xfc0028)
        metadata_offset,curve_offset,control_offset,flags_offset,grid_offset=332,1792,80,2332,2336
    result[metadata_offset:metadata_offset+1460]=metadata
    result[curve_offset:curve_offset+300]=curve
    result[curve_offset+300:curve_offset+540]=decode(matrix,keys,0x3f194)
    result[control_offset:control_offset+252]=control
    struct.pack_into('<I',result,flags_offset,0x10000 if style in (0x81,0x84) else 0x10001)
    for index,(identifier,seed) in enumerate(((0x1070,0x252e4),(0x1071,0x2d456))):
        table=field(identifier,215628,3)
        grid=dense9_flag0(table)
        packed=pack9_dense9(grid.reshape(-1).tolist())
        offset=grid_offset+index*2916
        result[offset:offset+2916]=decode(packed,keys,seed)
    return bytes(result)
