"""Mixer accumulation arithmetic; reference basis tables are caller-owned inputs."""
from .grading import round_divide
import math

COSINE=tuple(math.floor(1024*math.cos(i*math.pi/1024)+0.5) for i in range(513))

def mixer_accumulate(controls,basis):
    if len(controls)!=24 or any(len(basis[k])!=n for k,n in (
            ('hue',512),('saturation',512),('luminosity',1024),('slopes',64))):
        raise ValueError('Expected eight control triples and complete mixer basis arrays')
    hue=[0]*32;saturation=[0]*32;luminosity=[0]*64
    def signed16(v):
        return (v+32768)%65536-32768
    for group in range(8):
        h,s,l=controls[group*3:group*3+3]
        hi=group+(8 if h>=0 else 0)
        si=group+(8 if s>=0 else 0)
        li=group+(8 if l>=0 else 0)
        for index in range(32):
            hue[index]=signed16(hue[index]+round_divide(basis['hue'][index*16+hi]*abs(h),100))
            delta=round_divide(basis['saturation'][index*16+si]*abs(s),100)
            saturation[index]=signed16(saturation[index]+delta)
            for side in range(2):
                if s>0:
                    luminosity[index*2+side]+=round_divide(signed16(delta)*basis['slopes'][index*2+side],1024)
                luminosity[index*2+side]+=round_divide(basis['luminosity'][index*32+side*16+li]*abs(l),100)
    return hue,saturation,luminosity

def mixer_finalize(hue,saturation,luminosity,base,quarter):
    if quarter!=2048 or len(hue)!=32 or len(saturation)!=32 or len(luminosity)!=64 or len(base)!=6 or any(len(row)!=32 for row in base):
        raise ValueError('Expected observed 2048-unit quadrant and complete mixer arrays')
    def signed(value,bits):
        return (value+(1<<(bits-1)))%(1<<bits)-(1<<(bits-1))
    def rounded32(value,divisor):
        value=signed(value,32)
        adjusted=signed(value+(divisor//2 if value>=0 else -divisor//2),32)
        return (abs(adjusted)//divisor)*(-1 if adjusted<0 else 1)
    output=[[] for _ in range(6)]
    for index in range(32):
        angle=hue[index]
        if angle<0:angle=signed(angle+quarter*4,16)
        if not 0<=angle<=quarter*4:
            raise ValueError('Mixer angle would index outside the verified cosine domain')
        if angle<quarter:
            cosine=COSINE[angle//4];sine=COSINE[(quarter-angle)//4]
        elif angle<quarter*2:
            cosine=-COSINE[(quarter*2-angle)//4];sine=COSINE[(angle-quarter)//4]
        elif angle<quarter*3:
            cosine=-COSINE[(angle-quarter*2)//4];sine=-COSINE[(quarter*3-angle)//4]
        else:
            cosine=COSINE[(quarter*4-angle)//4];sine=-COSINE[(angle-quarter*3)//4]
        scale=max(0,signed(saturation[index]+1024,16))
        a,b,c,d=(row[index] for row in base[:4])
        transformed=((a*cosine-c*sine),(b*cosine-d*sine),
                     (c*cosine+a*sine),(d*cosine+b*sine))
        for row,value in zip(output[:4],transformed):
            row.append(max(-512,min(511,rounded32(signed(value,32)*scale,1048576))))
        for side in range(2):
            output[4+side].append(signed(base[4+side][index]+rounded32(luminosity[index*2+side],128),16))
    return [row+row for row in output]
