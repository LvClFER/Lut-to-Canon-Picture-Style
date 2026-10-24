"""Independent reconstructed prefix of Nikon's colour-grid point generator."""
from math import floor,isfinite,cos,sin,pi
from .grading import round_divide


def grid_rotation_tables():
    tables=[]
    for function in (cos,sin):
        values=[1024*function((i-16)*pi/90) for i in range(33)]
        knots=[int(v+0.5) if v>=0 else -int(-v+0.5) for v in values]
        tables.append([knots[i//16]+round_divide((knots[i//16+1]-knots[i//16])*(i%16),16)
                       for i in range(512)])
    return tables


def grid_input(coordinates,size,curves):
    if not isinstance(size,int) or size<2 or len(coordinates)!=3:
        raise ValueError('Expected a three-dimensional grid with at least two points per axis')
    if any(not isinstance(v,int) or not 0<=v<size for v in coordinates):
        raise ValueError('Grid coordinate outside axis bounds')
    if len(curves)!=3 or any(len(curve)!=4096 for curve in curves):
        raise ValueError('Expected three 4096-entry channel curves')
    positions=[min(4095,floor(v*(1/(size-1))*4095+0.5)) for v in coordinates]
    values=[curve[position] for curve,position in zip(curves,positions)]
    if any(not isinstance(v,int) or not 0<=v<=65535 for v in values):
        raise ValueError('Channel lookup value is not unsigned16')
    return values


def grid_matrix(values,matrix,margin):
    if len(values)!=3 or any(not isinstance(v,int) or not 0<=v<=65535 for v in values):
        raise ValueError('Expected three unsigned16 lookup values')
    if len(matrix)!=9 or any(not isinstance(v,int) or not -32768<=v<=32767 for v in matrix):
        raise ValueError('Expected nine signed16 coefficients')
    if not isinstance(margin,int) or not 0<=margin<=32767:
        raise ValueError('Margin outside reconstructed nonnegative signed16 range')
    clipped=[4095 if v>4095 else max(v,-margin) for v in values]
    output=[]
    for row in range(3):
        products=[round_divide(v*c,64) for v,c in zip(clipped,matrix[row*3:row*3+3])]
        value=round_divide(sum(products),8)
        output.append(min(4095,max(0 if row==0 else -4096,value)))
    return output


def grid_hue_position(first,second):
    if any(not isinstance(v,int) or not -4096<=v<=4095 for v in (first,second)):
        raise ValueError('Expected clamped signed chroma values')
    a,b=min(4095,abs(first)),min(4095,abs(second))
    magnitude=a+b
    position=min(511,round_divide(b*512,magnitude)) if magnitude else 0
    segment,fraction=divmod(position,64)
    quadrant=(3 if first>=0 else 2) if second>0 else (1 if first>0 else 0)
    lower=quadrant*8+segment
    upper=lower+1
    if quadrant==0 and segment==7:upper=16
    elif quadrant==2 and segment==0:lower=0
    elif quadrant==3:
        if segment==0:lower=8
        if segment==7:upper=24
    return [magnitude,lower,upper,fraction]


def grid_colour_coefficients(lower,upper,fraction,tables):
    if any(not isinstance(v,int) or not 0<=v<32 for v in (lower,upper)) or not isinstance(fraction,int) or not 0<=fraction<64:
        raise ValueError('Invalid hue segment position')
    if len(tables)!=6 or any(len(row)!=32 or any(not isinstance(v,int) or not -32768<=v<=32767 for v in row) for row in tables):
        raise ValueError('Expected six signed16 colour coefficient rows')
    return [min(2047,max(-2048,4*row[lower]+round_divide((row[upper]-row[lower])*fraction,16)))
            for row in tables]


def grid_base_coefficients(lower,upper,fraction,tables):
    if any(not isinstance(v,int) or not 0<=v<32 for v in (lower,upper)) or not isinstance(fraction,int) or not 0<=fraction<64:
        raise ValueError('Invalid hue segment position')
    if len(tables)!=10 or any(len(row)!=32 or any(not isinstance(v,int) or not -32768<=v<=32767 for v in row) for row in tables):
        raise ValueError('Expected ten signed16 base coefficient rows')
    return [min(511,max(-512,row[lower]+round_divide((row[upper]-row[lower])*fraction,64)))
            for row in tables]


def grid_intensity_indices(luma,chroma,coefficients):
    if not isinstance(luma,int) or not 0<=luma<=4095 or len(chroma)!=2 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in chroma):
        raise ValueError('Invalid clamped luma/chroma input')
    if len(coefficients)!=12 or any(not isinstance(v,int) or not -2147483648<=v<=2147483647 for v in coefficients):
        raise ValueError('Expected twelve signed32 intensity coefficients')
    a,b=(min(4095,abs(v)) for v in chroma)
    magnitude=min(32767,max(0,round_divide(2*(a+b)+abs(a-b),4)))
    inputs=[magnitude]*5+[luma,luma]+[magnitude]*3+[4095-luma,magnitude]
    products=[(v*c+2147483648)%4294967296-2147483648 for v,c in zip(inputs,coefficients)]
    return [min(4095,max(0,v)) for v in products]


def grid_response_gains(coefficients,lookup):
    if len(coefficients)!=6 or any(not isinstance(v,int) or not -512<=v<=511 for v in coefficients):
        raise ValueError('Expected six interpolated base coefficients')
    if len(lookup)!=7 or any(not isinstance(v,int) or not 0<=v<=65535 for v in lookup):
        raise ValueError('Expected seven unsigned16 intensity lookup values')
    def clip(value):return min(2047,max(0,value))
    def response(coefficient,value):
        return clip(256-coefficient+round_divide(coefficient*value,256))
    a=response(coefficients[0],lookup[0])
    b=response(coefficients[1],lookup[1])
    product=(a*b*lookup[2]+2147483648)%4294967296-2147483648
    gains=[clip(round_divide(product,65536))]
    for index,slot in ((2,3),(4,5)):
        a=response(coefficients[index],lookup[slot])
        b=response(coefficients[index+1],lookup[slot+1])
        gains.append(clip(round_divide(a*b,256)))
    return gains


def grid_apply_colour(luma,chroma,coefficients,luma_gain,luma_offset,colour_gains):
    if not isinstance(luma,int) or not 0<=luma<=4095 or len(chroma)!=2 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in chroma):
        raise ValueError('Invalid clamped luma/chroma input')
    if len(coefficients)!=6 or any(not isinstance(v,int) or not -2048<=v<=2047 for v in coefficients):
        raise ValueError('Expected six creative coefficients')
    if not isinstance(luma_gain,int) or not 0<=luma_gain<=2047 or not isinstance(luma_offset,int) or not -65535<=luma_offset<=65535:
        raise ValueError('Invalid luma gain/offset')
    if len(colour_gains)!=3 or any(not isinstance(v,int) or not 0<=v<=2047 for v in colour_gains):
        raise ValueError('Expected three colour response gains')
    def signed32(v):return (v+2147483648)%4294967296-2147483648
    def clip(v,low,high):return min(high,max(low,v))
    x,y=chroma
    value=signed32(coefficients[4]*x+coefficients[5]*y)
    value=(abs(value)//4)*(-1 if value<0 else 1)
    value=signed32(value+signed32(luma_gain*luma)+signed32(luma_offset*256))
    output=[clip(round_divide(value,256),0,4095)]
    scale=clip(signed32(colour_gains[0]*colour_gains[1]*colour_gains[2])>>16,0,4095)
    for row in (0,2):
        value=signed32(coefficients[row]*x+coefficients[row+1]*y)>>8
        output.append(clip(round_divide(signed32(value*scale),1024),-4096,4095))
    return output


def grid_rotation_matrix(chroma,rotation,mapped_luma,mix,target,matrix,offsets):
    for values,length,low,high in ((chroma,2,-4096,4095),(rotation,2,-32768,32767),
                                  (target,2,-32768,32767),(matrix,9,-32768,32767),(offsets,3,-32768,32767)):
        if len(values)!=length or any(not isinstance(v,int) or not low<=v<=high for v in values):
            raise ValueError('Invalid rotation/matrix input')
    if not isinstance(mapped_luma,int) or not 0<=mapped_luma<=65535 or not isinstance(mix,int) or not -2147483648<=mix<=2147483647:
        raise ValueError('Invalid mapped luma or mixture')
    def s32(v):return (v+2147483648)%4294967296-2147483648
    def trunc(v,d):return (abs(v)//d)*(-1 if v<0 else 1)
    def clip(v,low):return min(4095,max(low,v))
    x,y=chroma;c,s=rotation
    rotated=[clip(round_divide(s32(c*x-s*y),1024),-4096),
             clip(round_divide(s32(s*x+c*y),1024),-4096)]
    mixed=[clip(s32(v+trunc(s32((t-v)*mix),1024)),-4096) for v,t in zip(rotated,target)]
    values=[mapped_luma]+mixed
    output=[]
    for row in range(3):
        products=[trunc(s32(v*c),128) for v,c in zip(values,matrix[row*3:row*3+3])]
        value=s32(trunc(s32(sum(products)),8)+offsets[row])
        output.append(clip(value,0 if row==0 else -4096))
    return output


def grid_post_colour(luma,chroma,gain,hue_curve):
    if not isinstance(luma,int) or not 0<=luma<=4095 or len(chroma)!=2 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in chroma):
        raise ValueError('Invalid luma/chroma input')
    if not isinstance(gain,int) or not 0<=gain<=65535 or len(hue_curve)!=32 or any(not isinstance(v,int) or not 0<=v<=65535 for v in hue_curve):
        raise ValueError('Invalid gain or hue curve')
    x,y=chroma
    magnitude=abs(x)+abs(y)
    position=min(127,round_divide(abs(y)*128,magnitude)) if magnitude else 0
    segment,fraction=divmod(position,16)
    quadrant=(3 if x>=0 else 2) if y>0 else (1 if x>0 else 0)
    lower=quadrant*8+segment;upper=lower+1
    if quadrant==0 and segment==7:upper=16
    elif quadrant==2 and segment==0:lower=0
    elif quadrant==3:
        if segment==0:lower=8
        if segment==7:upper=24
    coefficient=min(4095,max(0,round_divide(hue_curve[lower]*16+(hue_curve[upper]-hue_curve[lower])*fraction,16)))
    scaled=[min(4095,max(-4096,(v*gain)>>10)) for v in chroma]
    a,b=(min(4095,abs(v)) for v in scaled)
    intensity=min(4095,round_divide(abs(a-b)+min(4095,a+b)+a+b,4))
    index=min(4095,max(0,(intensity*coefficient+luma*1024)>>10))
    return [index]+scaled


def grid_contrast(values,factors):
    if len(values)!=3 or not isinstance(values[0],int) or not 0<=values[0]<=4095 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in values[1:]):
        raise ValueError('Invalid luma/chroma values')
    if len(factors)!=2 or any(not isinstance(v,int) or not -2147483648<=v<=2147483647 for v in factors):
        raise ValueError('Expected two signed32 contrast factors')
    return [min(4095,max(0 if i==0 else -4096,(v*factors[0 if i==0 else 1])>>20))
            for i,v in enumerate(values)]


def grid_tone_matrix(values,tone,matrix,offsets):
    if len(values)!=3 or not isinstance(values[0],int) or not 0<=values[0]<=4095 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in values[1:]):
        raise ValueError('Invalid luma/chroma values')
    for data,length,low,high in ((tone,4096,0,65535),(matrix,9,-32768,32767),(offsets,3,-32768,32767)):
        if len(data)!=length or any(not isinstance(v,int) or not low<=v<=high for v in data):
            raise ValueError('Invalid tonal table/matrix')
    mapped=[tone[values[0]]]+list(values[1:])
    return [min(8191,max(-8192,sum((v*c)>>10 for v,c in zip(mapped,matrix[row*3:row*3+3]))+offsets[row]))
            for row in range(3)]


def grid_gamut(range_values,colour,controls,high_curve,low_curve):
    if len(range_values)!=3 or any(not isinstance(v,int) or not -8192<=v<=8191 for v in range_values):
        raise ValueError('Invalid gamut range values')
    if len(colour)!=3 or not isinstance(colour[0],int) or not 0<=colour[0]<=65535 or any(not isinstance(v,int) or not -4096<=v<=4095 for v in colour[1:]):
        raise ValueError('Invalid gamut colour')
    for data,length in ((controls,5),(high_curve,4096),(low_curve,4096)):
        if len(data)!=length or any(not isinstance(v,int) or not 0<=v<=65535 for v in data):
            raise ValueError('Invalid gamut controls/curves')
    def s32(v):return (v+2147483648)%4294967296-2147483648
    def trunc(v,d):return (abs(v)//d)*(-1 if v<0 else 1)
    def clip(v,low,high):return min(high,max(low,v))
    low_threshold,high_threshold,shift,high_weight,low_weight=controls
    shift &= 31
    maximum=clip(max(range_values),0,8191)
    hi=high_curve[clip(s32((maximum-high_threshold)<<shift),0,4095)]
    lo=low_curve[clip(s32((low_threshold-min(range_values))<<shift),0,4095)]
    luma=colour[0]
    low_delta=trunc(s32((2048-lo)*(4095-luma)),1024)
    high_delta=trunc(s32((hi-2048)*luma),1024)
    delta=clip(s32(low_delta*low_weight+high_delta*high_weight)>>8,-4096,4095)
    scale=s32(hi*lo)>>11
    return [clip(luma+delta,0,4095)]+[clip(s32(scale*v)>>11,-2048,2047) for v in colour[1:]]


def grid_encode(values,flags,mode,matrix):
    if len(values)!=3 or not isinstance(values[0],int) or not 0<=values[0]<=4095 or any(not isinstance(v,int) or not -2048<=v<=2047 for v in values[1:]):
        raise ValueError('Invalid final grid colour')
    if not isinstance(flags,int) or mode not in (0,1,3) or len(matrix)!=9 or any(not isinstance(v,(int,float)) or not isfinite(v) for v in matrix):
        raise ValueError('Unsupported encoding mode or invalid XYZ matrix')
    def clip(v,low,high):return min(high,max(low,v))
    luma,first,second=(v*16 for v in values)
    y=luma*(1/65535)
    rgb=[clip(y+second*(1.4021/65535),0,1),
         clip(y-first*(0.3455/65535)-second*(0.7146/65535),0,1),
         clip(y+first*(1.7712/65535),0,1)]
    if flags&1:return [floor(v*65280+0.5) for v in rgb]
    if mode in (0,3):
        linear=[(v*0.9478672985781991+0.05213270142180095)**2.4 if v>0.04045
                else v*0.07739938080495357 for v in rgb]
    else:
        linear=[max(v**2.19921875,v*0.03125) for v in rgb]
    r,g,b=linear
    xyz=[g*matrix[i+1]+r*matrix[i]+b*matrix[i+2] for i in (0,3,6)]
    xyz=[clip(v,0,maximum) for v,maximum in zip(xyz,(0.9642,1.0,0.8249))]
    xyz[0]*=1.0371292263015972
    xyz[2]*=1.212268153715602
    fx,fy,fz=[v**(1/3) if v>0.008856 else v*7.787+0.13793103448275862 for v in xyz]
    lab=[clip(fy*116-16,0,100),clip((fx-fy)*500,-128,127),clip((fy-fz)*200,-128,127)]
    return [floor(lab[0]*652.8000000000001+0.5),floor(lab[1]*256+32768.5),floor(lab[2]*256+32768.5)]


def grid_remaining_response(coefficients,lookup,luma_value,rotation_tables):
    if len(coefficients)!=4 or any(not isinstance(v,int) or not -512<=v<=511 for v in coefficients):
        raise ValueError('Expected four base response coefficients')
    if len(lookup)!=5 or any(not isinstance(v,int) or not 0<=v<=65535 for v in lookup) or not isinstance(luma_value,int) or not -32768<=luma_value<=32767:
        raise ValueError('Invalid response lookup values')
    if len(rotation_tables)!=2 or any(len(row)!=512 or any(not isinstance(v,int) or not -32768<=v<=32767 for v in row) for row in rotation_tables):
        raise ValueError('Expected two signed16 rotation tables')
    def clip(v,low,high):return min(high,max(low,v))
    a=clip(round_divide(coefficients[0]*lookup[0],256),-512,511)
    b=clip(round_divide(coefficients[1]*lookup[1],256),-512,511)
    index=clip(((a+b)>>1)+256,0,511)
    product=(lookup[2]*lookup[3]+2147483648)%4294967296-2147483648
    inverse=clip(256-clip(round_divide(product,256),0,1023),0,1023)
    gain=clip(256-coefficients[2]+round_divide(inverse*coefficients[2],256),0,1023)
    offset=clip(round_divide(luma_value*coefficients[3],256),-lookup[4],lookup[4])
    return [rotation_tables[0][index],rotation_tables[1][index],gain,offset]
