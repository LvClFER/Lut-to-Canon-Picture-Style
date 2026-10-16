"""Preceding six-axis transition arithmetic, verified default geometry only."""
import argparse
import json
import math
import struct
from pathlib import Path
from .default_axis_reference import cone_hue,adjustments
from .axis_composition_reference import compose


def sector_weights(hue,softness=20):
    sample=hue%6;centre=math.floor(sample+.5)%6
    if isinstance(softness,(list,tuple)):
        if len(softness)!=6 or not all(math.isfinite(v) and v>=0 for v in softness):
            raise ValueError('Require six bounded transition widths')
        softness=softness[centre]
    if not math.isfinite(softness) or softness<0:raise ValueError('Require bounded transition width')
    width=min(softness/60,.5)
    # The wrap sector is evaluated around zero, not around six. Subtracting
    # six before the boundary comparison changes exact transition endpoints.
    if centre==0 and sample>=5.5:sample-=6
    low,high=centre-.5,centre+.5
    result=[0.]*6
    if not width:result[centre]=1.;return result
    if sample<low+width:
        t=(sample-low+width)/(2*width);neighbor=(centre-1)%6
    elif sample>high-width:
        t=(high-sample+width)/(2*width);neighbor=(centre+1)%6
    else:
        result[centre%6]=1.;return result
    weight=t+(1/(1+math.exp(-12*(t-.5)))-t)/6
    result[centre%6]=weight;result[neighbor]=1-weight
    return result


def decode_block(raw):
    if len(raw)!=512 or raw[:8]!=bytes.fromhex('0200000006000000'):
        raise ValueError('Require six-group kind2 block')
    words=list(struct.unpack('<128i',raw));widths=[words[20+21*i] for i in range(6)]
    if any(v<0 for v in widths):raise ValueError('Negative transition width')
    # Validate the same canonical geometry while retaining each native width.
    for i in range(6):words[20+21*i]=20
    checked=struct.pack('<128i',*words)
    values=adjustments([checked[8+i*84:8+(i+1)*84] for i in range(6)],20)
    return values,widths


def transform(rgb,values,softness=20):
    if len(values)!=6:raise ValueError('Require six initialized triplets')
    h=cone_hue(rgb);weights=sector_weights(h,softness)
    hi,lo=max(rgb),min(rgb);light=(hi+lo)*.5
    saturation=(hi-lo)/((hi+lo) if light>=.5 else (2-hi)-lo)
    h+=sum(w*v[0]/60 for w,v in zip(weights,values))
    ds=sum(w*v[1]/100 for w,v in zip(weights,values))
    dl=sum(w*v[2]/100 for w,v in zip(weights,values))*saturation
    return compose(rgb,h,ds*(saturation if ds>0 else 1),dl)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();data=json.loads(args.probe.read_text(encoding='utf-8'))
    values={}
    for case in data['cases']:
        raw=bytes.fromhex(case['parametersHex'])
        values[case['name']]=decode_block(raw)
    passed=0;maximum=0.;failures=[]
    for row in data['rows']:
        v,softness=values[row['name']]
        expected=transform(row['rgb'],v,softness)
        error=max(abs(a-b) for a,b in zip(expected,row['output']));maximum=max(maximum,error)
        passed+=error<=1e-14
        if error>1e-14 and len(failures)<20:failures.append({**row,'expected':expected,'error':error})
    result={'cameraAccess':False,'scope':'preceding default six-axis geometry',
            'softnessValues':sorted({width for v in values.values() for width in v[1]}),
            'cases':len(data['rows']),'passed':passed,'maxError':maximum,'firstMismatches':failures}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not data['rows'] or passed!=len(data['rows']):raise SystemExit(1)


if __name__=='__main__':main()
