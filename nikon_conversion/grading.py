"""Independent arithmetic only; callers supply the unimplemented hue basis."""

def round_divide(numerator,divisor):
    if not isinstance(numerator,int) or not isinstance(divisor,int) or divisor<=0:
        raise ValueError('Expected integer numerator and positive divisor')
    if abs(numerator)+divisor//2>2147483647:
        raise ValueError('Signed32 adjusted numerator overflow')
    return ((abs(numerator)+divisor//2)//divisor)*(-1 if numerator<0 else 1)

def grading_vector(hue,saturation,lightness,basis,lightness_scale):
    if not 0<=hue<len(basis) or len(basis[hue])!=3:
        raise ValueError('Hue outside supplied basis')
    return (round_divide(lightness*lightness_scale,100),
        *(round_divide(value*saturation,100) for value in basis[hue]))

def grading_ramps(vectors,balance,shift,parameters):
    if len(vectors)!=3 or any(len(v)!=4 for v in vectors) or len(parameters)!=7:
        raise ValueError('Expected three four-component vectors and seven ramp parameters')
    shift_scale,base_width,width_scale,*knots=parameters
    offset=round_divide(shift*shift_scale,100)
    width=base_width+round_divide(balance*width_scale,100)
    if width<=0:
        raise ValueError('Nonpositive blending width is outside the verified arithmetic')
    a,b,c,d=(v-offset for v in knots)
    def boundary(value):
        truncated=abs(value)//16*(-1 if value<0 else 1)
        return max(0,min(65,truncated+1))
    result=[[0]*4 for _ in range(65)]
    def add(group,start,end,origin=None,fall=False):
        for index in range(boundary(start) if start is not None else 0,
                           boundary(end) if end is not None else 65):
            weight=256 if origin is None else round_divide((index*16-origin)*256,width)
            if fall:weight=256-weight
            for channel,amplitude in enumerate(vectors[group]):
                value=result[index][channel]+round_divide(amplitude*weight,256)
                result[index][channel]=(value+32768)%65536-32768
    add(0,None,a)
    add(0,a,a+width,a,True)
    add(1,b-width,b,b-width)
    add(1,b,c)
    add(1,c,c+width,c,True)
    add(2,d-width,d,d-width)
    add(2,d,None)
    return [row[0] for row in result],[v for row in result for v in row[1:]]

def grading_curves(lightness,color,gain):
    if len(lightness)!=65 or len(color)!=195 or len(gain)!=65:
        raise ValueError('Expected 65 samples per grading curve')
    def signed16(value):
        return (value+32768)%65536-32768
    return [[max(0,min(4095,index*64+
        signed16(round_divide(lightness[index],16))+
        signed16(round_divide(color[index*3+channel]*gain[index],1024))))
        for index in range(65)] for channel in range(3)]

def expand_curve65(curve):
    if len(curve)!=65 or any(not isinstance(v,int) or not 0<=v<=65535 for v in curve):
        raise ValueError('Expected 65 unsigned16 curve samples')
    result=[]
    for position in range(4096):
        lower,fraction=divmod(position,64)
        value=curve[lower]+round_divide((curve[lower+1]-curve[lower])*fraction,64)
        result.append(value%65536)
    return result
