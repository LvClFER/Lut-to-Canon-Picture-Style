"""Independent observed global-saturation arithmetic, without native lookup data."""
from .grading import round_divide

def saturation_factor(value):
    if not isinstance(value,int) or not -100<=value<=100:
        raise ValueError('Global saturation outside verified -100..100 range')
    return 1024+round_divide(value*(1536 if value>=0 else 1024),100)

def saturation_matrix(value,strength,base):
    if not isinstance(strength,int) or not 0<=strength<=65535 or len(base)!=9:
        raise ValueError('Expected unsigned16 strength and nine matrix coefficients')
    factor=round_divide((saturation_factor(value)-1024)*strength+262144,256)
    chroma=[(round_divide(coefficient*factor,1024)+32768)%65536-32768 for coefficient in base[3:]]
    return list(base[:3])+chroma

def highlights_shadows_curve(highlights,shadows,basis):
    if any(not isinstance(v,int) or not -120<=v<=120 for v in (highlights,shadows)):
        raise ValueError('Expected prepared global highlights/shadows in -120..120')
    if len(basis['highlights'])!=1028 or len(basis['shadows'])!=1028:
        raise ValueError('Expected complete 257-sample tonal bases')
    hi=2 if highlights<0 else 3
    si=2 if shadows<0 else 3
    return [(min(4095,index*16)+round_divide(basis['highlights'][index*4+hi]*abs(highlights),120)+
        round_divide(basis['shadows'][index*4+si]*abs(shadows),120)+32768)%65536-32768
        for index in range(257)]


def white_black_curve(white,black,parameters):
    if any(not isinstance(v,int) or not -100<=v<=100 for v in (white,black)):
        raise ValueError('Expected white/black controls in -100..100')
    if len(parameters)!=6 or any(not isinstance(v,int) or not 0<=v<=65535 for v in parameters):
        raise ValueError('Expected six unsigned16 white/black parameters')
    wn,wp,bn,bp,high_knee,low_knee=parameters
    if not 0<high_knee<256 or not 0<low_knee<256:
        raise ValueError('Invalid white/black knees')
    w=round_divide(white*(wn if white<0 else wp),100)
    b=round_divide(black*(bn if black<0 else bp),100)
    slope=round_divide(262144+(w-b)*64,256)
    offset=b*64
    high_a=high_b=high_c=0
    if w<0:
        width=256-high_knee
        high_a=round_divide(262144-high_knee*slope-offset,width*width)-round_divide(slope,width)
        high_b=slope-2*high_knee*high_a
        high_c=262144-high_a*65536-high_b*256
    else:
        high_knee=256
    low_a=low_b=0
    if b>0:
        low_a=round_divide(slope,low_knee)+round_divide(-(low_knee*slope+offset),low_knee*low_knee)
        low_b=slope-2*low_knee*low_a
    else:
        low_knee=0
    def truncate64(value):
        return (abs(value)//64)*(-1 if value<0 else 1)
    return [truncate64(low_a*i*i+low_b*i if i<low_knee else
                       high_a*i*i+high_b*i+high_c if i>high_knee else slope*i+offset)
            for i in range(257)]


def contrast_expand(first,second,weight_first,weight_second):
    if any(len(curve)!=257 or any(not isinstance(v,int) or not 0<=v<=65535 for v in curve)
           for curve in (first,second)):
        raise ValueError('Expected two 257-sample unsigned16 contrast curves')
    if any(not isinstance(v,int) or not 0<=v<=256 for v in (weight_first,weight_second)):
        raise ValueError('Expected contrast weights in 0..256')
    residual=(256-weight_first-weight_second)*256
    output=[]
    for i in range(4096):
        index,fraction=divmod(i,16)
        a=first[index]+round_divide((first[index+1]-first[index])*fraction,16)
        b=second[index]+round_divide((second[index+1]-second[index])*fraction,16)
        output.append(a*weight_first+b*weight_second+residual)
    return output


def contrast_select(contrast,brightness,first,second,brightness_first,brightness_second):
    if not isinstance(contrast,int) or not -256<=contrast<=256 or not isinstance(brightness,int) or not 0<=brightness<=12:
        raise ValueError('Contrast/brightness outside observed native ranges')
    for values,length in ((first,771),(second,771),(brightness_first,514),(brightness_second,514)):
        if len(values)!=length or any(not isinstance(v,int) or not 0<=v<=65535 for v in values):
            raise ValueError('Invalid contrast calibration table')
    selected=2 if contrast>0 else 1
    side=int(brightness>6)
    amount=abs(brightness-6)
    curves=[]
    for base,adjustments in ((first,brightness_first),(second,brightness_second)):
        for column in (0,selected):
            values=[]
            for i in range(257):
                delta=(adjustments[i*2+side]-4096)*amount
                delta=(abs(delta)//6)*(-1 if delta<0 else 1)
                values.append((base[i*3+column]+delta)%65536)
            curves.append(values)
    return curves,(256-abs(contrast),abs(contrast))
