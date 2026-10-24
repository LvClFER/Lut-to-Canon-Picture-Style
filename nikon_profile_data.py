"""Read user-supplied Nikon coefficient data; no DLL or profile data bundled."""
import hashlib
from pathlib import Path
import struct
import zlib

MAX_CONTAINER_BYTES=64*1024*1024
SUPPORTED_MODEL=1072
SUPPORTED_PROFILE_SHA256='6fe805ed9ffb2e4ca0fdd1b8bcd051a96bb1d9aa6626e66d1d2c77c2bc72d5e0'


def load_conversion_profile(path):
    with Path(path).open('rb') as stream:
        data=stream.read(MAX_CONTAINER_BYTES+1)
    profile=decode_profile(data,SUPPORTED_MODEL)
    if hashlib.sha256(profile).hexdigest()!=SUPPORTED_PROFILE_SHA256:
        raise ValueError('This Nikon profile version has not been validated for NP3 conversion')
    return profile


def decode_profile(data,model):
    if not isinstance(data,bytes) or not 32<=len(data)<=MAX_CONTAINER_BYTES or data[:8]!=b'NKON\x00\x00\x01\x01':
        raise ValueError('Unsupported coefficient container')
    if not isinstance(model,int) or not 0<=model<=0xffffffff:
        raise ValueError('Invalid profile identifier')
    records={};cursor=32
    while cursor<len(data):
        if len(data)-cursor<32 or len(records)>=4096:
            raise ValueError('Truncated or excessive coefficient records')
        kind,identifier,alias,flags,size,length,_,_=struct.unpack_from('<8I',data,cursor)
        cursor+=32;key=(kind,identifier)
        if key in records or size>8*1024*1024 or length>16*1024*1024 or size>len(data)-cursor:
            raise ValueError('Invalid coefficient record')
        records[key]=(alias,flags,length,data[cursor:cursor+size]);cursor+=size
    seen=set()
    while model not in seen:
        seen.add(model)
        record=records.get((0x1002,model))
        if record is None:raise ValueError('Required profile not found')
        alias,flags,length,packed=record
        if alias:
            model=alias;continue
        if flags!=3 or not packed:raise ValueError('Unsupported profile encoding')
        state=0x10dcd;decoded=bytearray(len(packed))
        for i,value in enumerate(packed):
            state=(state*0x6c078965+1)&0xffffffff
            decoded[i]=value^((state>>13)&255)
        decoder=zlib.decompressobj()
        try:result=decoder.decompress(decoded,length+1)
        except zlib.error as error:raise ValueError('Invalid compressed profile') from error
        if len(result)!=length or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('Profile decompression length mismatch')
        return result
    raise ValueError('Profile alias cycle')
