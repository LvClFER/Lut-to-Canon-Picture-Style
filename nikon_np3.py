"""Independent NP3 0310 record reader; color rendering is not implemented here.

Record geometry was checked against Nikon's parser on user-provided files.
Keep encoded control pairs and color blocks intact until their semantics have
been validated; decoding a document does not establish a Canon conversion.
"""
from dataclasses import dataclass,field
import struct

MAX_BYTES=2*1024*1024
CONTROL_TAGS={'sharpness':0x600,'clarity':0x700,'contrast':0x800,
    'brightness':0x900,'saturation':0xa00,'hue':0xb00,'midrange_sharpness':0x1600}
RECORD_SIZES={0x100:4,0x200:20,0x1f00:28,0x2000:20,2:578,
    **{tag:2 for tag in range(0x300,0x1f00,0x100)}}


@dataclass(frozen=True)
class NP3Style:
    name:str
    records:tuple[tuple[int,bytes],...]=field(repr=False)

    def block(self,tag):
        return next((payload for code,payload in self.records if code==tag),None)

    @property
    def encoded_controls(self):
        return {name:self.block(tag) for name,tag in CONTROL_TAGS.items() if self.block(tag) is not None}

    @property
    def tone_curve_samples(self):
        """Native 15-bit table values; their rendering stage is not established."""
        block=self.block(2)
        if block is None:return None
        samples=struct.unpack('>257H',block[64:])
        if max(samples)>32767:raise ValueError('NP3 tone curve exceeds the 15-bit range')
        return samples

    @property
    def color_values(self):
        """41 numeric slots in native order, without claiming pixel equivalence.

        Slot groups are 6 global values, 8 triples, 3 triples and 2 final values.
        Visual meanings and rendering must be validated separately.
        """
        blender=self.block(0x1f00);grading=self.block(0x2000)
        if blender is None or grading is None:
            raise ValueError('NP3 color extension blocks are required')
        def divide(value,divisor):
            if not divisor:raise ValueError('Invalid NP3 zero divisor')
            return int(value/divisor)  # Native conversion truncates toward zero.
        def scalar(value,divisor,default=0):
            return default if value in (0,1,255) else divide(value-128,divisor)
        values=[]
        for tag in range(0x1900,0x1f00,0x100):
            pair=self.block(tag)
            values.append(scalar(*pair) if pair is not None else 0)
        values.extend(scalar(blender[index],blender[24+index%3]) for index in range(24))
        for offset in (0,4,8):
            value=int.from_bytes(grading[offset:offset+2],'big')
            values.append(0 if value==65535 else divide(value-32768,grading[12]))
            values.extend((scalar(grading[offset+2],grading[13]),scalar(grading[offset+3],grading[14])))
        values.extend((scalar(grading[16],grading[17],50),scalar(grading[18],grading[19])))
        return tuple(values)


def decode(data):
    if not isinstance(data,bytes) or not 52<=len(data)<=MAX_BYTES:
        raise ValueError('NP3 document is outside the supported size bounds')
    if data[:4]!=b'NCP\0' or data[-4:]!=bytes(4):
        raise ValueError('Invalid NP3 header or terminator')
    records=[];seen=set();cursor=4;end=len(data)-4
    while cursor<end:
        if end-cursor<8:raise ValueError('Truncated NP3 record header')
        tag,size=struct.unpack_from('>II',data,cursor);cursor+=8
        if tag in seen or size>end-cursor:raise ValueError('Duplicate or truncated NP3 record')
        if len(records)>=256:raise ValueError('NP3 record count exceeds the supported bound')
        fixed=RECORD_SIZES.get(tag)
        if fixed is not None:
            if size!=fixed:raise ValueError('Invalid NP3 record size')
        elif tag==0x10100:
            if size>2000:raise ValueError('NP3 comment exceeds its bound')
        elif tag==0x10200:
            if size>256:raise ValueError('NP3 text exceeds its bound')
        else:raise ValueError(f'Unsupported NP3 record 0x{tag:X}')
        records.append((tag,data[cursor:cursor+size]));seen.add(tag);cursor+=size
    blocks=dict(records)
    if blocks.get(0x100)!=b'0310':raise ValueError('Only NP3 version 0310 has been validated')
    if not {0x200,0x300}.issubset(blocks):raise ValueError('Missing NP3 name or base identifier')
    name_bytes=blocks[0x200];name,separator,padding=name_bytes.partition(b'\0')
    if separator and padding.strip(b'\0'):raise ValueError('Invalid NP3 name padding')
    try:name=name.decode('ascii')
    except UnicodeDecodeError as error:raise ValueError('Unsupported NP3 name encoding') from error
    if not name or any(ord(c)<32 for c in name):raise ValueError('Invalid NP3 name')
    return NP3Style(name,tuple(records))
