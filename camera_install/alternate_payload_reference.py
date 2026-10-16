"""Offline proof of observed 00FF0001 blocks; never camera transport."""
import hashlib
import struct

LAYOUT=((360,0xb8ed),(4456,0x33137),(8552,0xb8ed),(12648,0x33137))


def expanded_header(header):
    """Predict the observed alternate header expansion, not serialize a carrier."""
    if (len(header)!=344 or struct.unpack_from('<H',header,24)[0]!=0x4140
            or struct.unpack_from('<I',header,84)[0]!=0xfc0040):
        raise ValueError('Unknown alternate header structure')
    extension=struct.pack('<2I',1,1)
    result=bytearray(header[:24]+extension+header[24:84]+extension+header[84:])
    struct.pack_into('<H',result,32,0x4148)
    struct.pack_into('<I',result,100,0xfc0048)
    return bytes(result)


def verify_blocks(decoded, captures, gates, header_size=360):
    """Require complete, unambiguous observed block coverage and gate agreement."""
    if type(header_size) is not int or header_size not in (344,360):
        raise ValueError('Unverified alternate header geometry')
    layout=tuple((header_size+i*4096,seed) for i,(_,seed) in enumerate(LAYOUT))
    if set(decoded)!=set(layout) or any(len(v)!=4096 for v in decoded.values()):
        raise ValueError('Require four bounded alternate-property decoded blocks')
    if (len(gates)!=2 or {g['index'] for g in gates}!={1,2}
            or any(type(g['index']) is not int or type(g['enabled']) is not bool for g in gates)):
        raise ValueError('Require two distinct observed boolean descriptor gates')
    rows=[]
    for capture in captures:
        if capture.get('functionRva') not in ('0x4b760','0x49e00'):
            continue
        block=bytes.fromhex(capture['nativePackedHex'])
        if len(block)!=4096:
            raise ValueError('Unbounded or missing native packer output')
        locations=[{'offset':offset,'seed':seed} for (offset,seed),value in decoded.items() if value==block]
        if not locations:
            raise ValueError('Native packer output absent from alternate payload')
        rows.append({'functionRva':capture['functionRva'],
                     'hash':hashlib.sha256(block).hexdigest(),'locations':locations})
    covered={(p['offset'],p['seed']) for row in rows for p in row['locations']}
    if covered!=set(layout):
        raise ValueError('Alternate payload contains unexplained blocks')
    integer_offsets={p['offset'] for row in rows if row['functionRva']=='0x49e00' for p in row['locations']}
    enabled_offsets={header_size+(g['index']-1)*4096 for g in gates if g['enabled']}
    if integer_offsets!=enabled_offsets:
        raise ValueError('Integer block locations disagree with gates or are ambiguous')
    return rows
