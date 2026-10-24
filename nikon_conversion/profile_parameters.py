"""Reconstruct observed fixed fields directly from a decoded coefficient profile."""
import struct
from .grading import expand_curve65,round_divide
from .tone import expand_tone_curve
from .curves import expand_curve33,expand_signed_curve65

# Observed output mode0, selected by the grid caller after coefficient preparation.
SRGB_D50_XYZ=(0.436071339,0.385066415,0.143057225,
    0.222502613,0.716880769,0.06061491,0.013922978,0.097068147,0.713984047)


def profile_gamut_parameters(profile,style_index):
    if not isinstance(profile,bytes) or len(profile)<0x63d80 or not isinstance(style_index,int) or not 0<=style_index<=255:
        raise ValueError('Invalid profile or style index')
    offset=(style_index+0x9fbb)*10
    if offset+10>len(profile):raise ValueError('Profile style record is truncated')
    low,high=struct.unpack_from('<2H',profile,offset)
    shift=profile[offset+4]
    high_weight,low_weight=struct.unpack_from('<2H',profile,offset+6)
    return dict(toneMatrix=list(struct.unpack_from('<9h',profile,0x63c32)),
        toneOffsets=list(struct.unpack_from('<3h',profile,0x63c44)),
        mappedLuma=expand_tone_curve([min(4095,i*16) for i in range(257)]),
        gamutControls=[low,high,shift,high_weight,low_weight],
        gamutHigh=expand_curve65(struct.unpack_from('<65H',profile,0x63c4a)),
        gamutLow=expand_curve65(struct.unpack_from('<65H',profile,0x63ccc)))


def flexible_colour_bases(profile):
    if not isinstance(profile,bytes) or len(profile)<0x682a8:
        raise ValueError('Truncated flexible-colour profile')
    def read(kind,offset,count=1):return list(struct.unpack_from('<'+str(count)+kind,profile,offset))
    style=14  # Observed NP3 base 0x0020 maps to this internal style.
    hue=read('h',0x67a2c,1080)
    return dict(gradingHue=dict(values=[hue[i:i+3] for i in range(0,1080,3)],lightnessScale=read('H',0x21c22)[0]),
        gradingRamps=dict(gain=read('H',0x679aa,65),values=[read('H',o)[0] for o in
            (0x21c1c,0x21c1e,0x21c20,0x679a2,0x679a4,0x679a6,0x679a8)]),
        mixer=dict(quarter=read('H',0x2d6b2)[0],hue=read('h',0x66520,512),
            saturation=read('h',0x675a2,512),luminosity=read('h',0x66920,1024),slopes=read('h',0x67522,64)),
        mixerNeutral=[read('h',0x22460+style*0x180+i*64,32) for i in range(6)],
        tone=dict(highlights=read('h',0x62c22,1028),shadows=read('h',0x6342a,1028)),
        whiteBlack=read('H',0x6829c,6),
        globalSaturation=dict(strength=256,base=[read('h',0x6535c+i*6)[0] for i in range(9)]),
        globalContrast=dict(baseFirst=read('H',0x3bdb6+style*0x606,771),
            baseSecond=read('H',0x4a29a+style*0x606,771),
            brightnessFirst=read('H',0x5877e+style*0x404,514),
            brightnessSecond=read('H',0x5cfc6+style*0x404,514)))


def profile_chroma_parameters(profile,style_index):
    if not isinstance(profile,bytes) or not isinstance(style_index,int) or not 0<=style_index<=255:
        raise ValueError('Invalid profile or style index')
    hue_offset=0x30af8+style_index*64
    gain_offset=0x30f78+style_index*0x82
    if len(profile)<max(0x21c1c,hue_offset+64,gain_offset+130):
        raise ValueError('Truncated chroma profile fields')
    knots=[min(2047,v) for v in struct.unpack_from('<65H',profile,gain_offset)]
    return dict(margin=struct.unpack_from('<H',profile,0x21c1a)[0],
        hueCurve=list(struct.unpack_from('<32H',profile,hue_offset)),chromaGain=expand_curve65(knots))


def profile_base_rows(profile,style_index):
    if not isinstance(profile,bytes) or not isinstance(style_index,int) or not 0<=style_index<=255:
        raise ValueError('Invalid profile or style index')
    offset=0x25d60+style_index*9*64
    if len(profile)<max(offset+9*64,0x65af0):
        raise ValueError('Truncated base coefficient rows')
    rows=[list(struct.unpack_from('<32h',profile,offset+i*64)) for i in range(9)]
    gain=struct.unpack_from('<H',profile,0x65a5e+12*12)[0]
    # shortcut: neutral basic saturation only; derive its gain selection before supporting other settings.
    if gain!=0:raise ValueError('Nonneutral basic saturation gain is not reconstructed')
    return dict(baseRows=rows[:8]+[[0]*32,rows[8]])


def profile_intensity_parameters(profile,tone_index):
    if not isinstance(profile,bytes) or len(profile)<0x65a5e or not isinstance(tone_index,int) or not 0<=tone_index<=2:
        raise ValueError('Invalid intensity profile or tone selector')
    coefficients=[1<<min(profile[0x2243c+tone_index+i*3],3) for i in range(12)]
    curves=[]
    for offset in (0x658d2,0x65998):
        knots=[struct.unpack_from('<H',profile,offset+tone_index*2+i*6)[0] for i in range(33)]
        curves.append(expand_curve33(knots))
    return dict(intensityCoefficients=coefficients,toneIntensityCurves=curves)


def flexible_intensity_curves(profile):
    # shortcut: observed flexible mode 12/style 14; verify other modes before extending selection.
    offset=0x28664+14*0x252-0x84
    if not isinstance(profile,bytes) or len(profile)<offset+9*66:
        raise ValueError('Truncated flexible intensity profile')
    return {slot:expand_curve33(struct.unpack_from('<33H',profile,offset+i*66))
        for i,slot in enumerate((0,1,3,4,5,6,7,8,11))}


def flexible_special_intensity_curve(profile,adjustment):
    # shortcut: observed mode12/style14/bank0; caller must supply independently selected basic adjustment.
    if not isinstance(profile,bytes) or len(profile)<0x6650a or not isinstance(adjustment,int) or not -12<=adjustment<=12:
        raise ValueError('Truncated special intensity profile')
    def read(offset):return struct.unpack_from('<H',profile,offset)[0]
    knots=[]
    for i in range(33):
        delta=round_divide((read(0x2b8c8+14*132+(66 if adjustment>0 else 0)+i*2)-256)*abs(adjustment),12)
        base=read(0x2cc60+14*66+i*2)
        knots.append(round_divide((base+delta)*read(0x66208+i*24),256))
    return expand_curve33(knots)


def profile_luma_curve(profile,style_index):
    if not isinstance(profile,bytes) or not isinstance(style_index,int) or not 0<=style_index<=255:
        raise ValueError('Invalid luma profile or style selector')
    offset=0x2afa4+style_index*0x82
    if len(profile)<offset+130:
        raise ValueError('Truncated luma profile')
    return expand_signed_curve65(struct.unpack_from('<65h',profile,offset))


def profile_target_parameters(profile):
    if not isinstance(profile,bytes) or len(profile)<0x3080a:
        raise ValueError('Truncated target profile')
    first,second,target_y,target_x,shift,multiplier,minimum,ceiling=struct.unpack_from('<4h2B2H',profile,0x307fc)
    first=max(-4096,min(4095,first));second=max(-4096,min(4095,second))
    magnitude=min(4095,abs(second-first)+abs(second+first)+abs(second)+abs(first))
    mix=max(minimum,max(0,min(4095,ceiling-((magnitude*multiplier)>>(shift&31)))))
    return dict(target=[target_x,target_y],mix=max(0,min(1023,mix)))


def flexible_neutral_rotation(profile):
    # shortcut: mode12 with hue sentinel255; other hue controls require indexed selection.
    if not isinstance(profile,bytes) or len(profile)<0x30896:
        raise ValueError('Truncated rotation profile')
    offsets=(0x3080a,0x3080c,0x3080e,0x30810,0x3088e,0x30890,0x30816,0x30892,0x30894)
    return dict(rotationMatrix=[struct.unpack_from('<h',profile,offset)[0] for offset in offsets],
        rotationOffsets=[0,0,0])
