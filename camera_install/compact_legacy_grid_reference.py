"""Offline48d10 compact-reader/MLIBcalcLuckyEx reference, not transport."""
import struct
from .descriptor_import_reference import validated_style_ordinal
from .legacy_grid_reference import prepare,flagged_point


def compact_legacy_arguments(normalized,style,index):
    """Return semantic math arguments plus the ORIGINAL native kind0 block.

    fa40's non-kind2 branch dispatches each kind0 four-point group toff60.
    Reusing the verified selective group math requires an internal kind1
    envelope; this is NOT a change to descriptor/PF3 bytes or Canon API input.
    """
    if type(normalized) is not bytes or len(normalized)!=7492:
        raise ValueError('Require normalized compact7492-byte store')
    ordinal=validated_style_ordinal(style)
    if ordinal>=5 or type(index) is not int or index not in (1,2):
        raise ValueError('Unvalidated compact style/index')
    base=ordinal*0x5d8
    offset=base+0x2d0+index*0x104
    kind,count=struct.unpack_from('<HH',normalized,offset)
    if kind!=0 or count>8:
        raise ValueError('Require bounded native kind0 four-point groups')
    words=[kind,count]
    for group in range(count):
        words.append(4)
        for position in range(16):
            words.append(struct.unpack_from('<H' if position%4==0 else '<h',
                normalized,offset+4+group*32+position*2)[0])
    native=struct.pack('<'+'I'*len(words),*(v&0xffffffff for v in words))
    semantic=struct.pack('<I',1)+native[4:]
    arguments=dict(oldParameterBlock=None,axisParameterBlock=None,
        additionalParameterBlock=dict(kind=1,count=count,points=4,initializedHex=semantic.hex()),
        matrix240Hex=normalized[base+0x104+index*0xf0:base+0x104+(index+1)*0xf0].hex(),
        preCurvesHex=None,postCurvesHex=None,thirdCurvesHex=None,numericArguments=[index,1])
    return arguments,native


def compact_legacy_grid(normalized,style,index):
    arguments,_=compact_legacy_arguments(normalized,style,index)
    coefficients,mode,curves,groups=prepare(arguments,experimental_geometry=True)
    rgb=[flagged_point((r,g,b),coefficients,mode,curves,groups,10,1)
         for r in range(10) for g in range(10) for b in range(10)]
    return [p[c] for c in range(3) for p in rgb]
