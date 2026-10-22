"""Experimental independent 10a00 helper with nondefault sector bounds."""
import argparse
import json
import math
import struct
from pathlib import Path
from .default_axis_reference import cone_hue
from .axis_composition_reference import compose


def decode(raw):
    words=struct.unpack('<21i',raw)
    if words[0]!=5 or words[1::4]!=(0,1,2,3,5):
        raise ValueError('Require verified five-tag axis layout')
    # RP descriptors also encode the red sector's lower bound as -10,
    # equivalent to 350 after the helper's circular interval normalization.
    if not (-360<=words[6]<=360 and 0<=words[10]<=360 and
            all(0<=words[i]<=100 for i in (7,8,11,12)) and 0<=words[18]<=360):
        raise ValueError('Nondefault bounds outside the bounded research domain')
    return {'low':[words[6]/60,words[7]/100,words[8]/100],
            'high':[words[10]/60,words[11]/100,words[12]/100],
            'delta':[words[14]/60,words[15]/100,words[16]/100],
            'width':words[18]/60}


def extent(group):
    low,high=group['low'][0],group['high'][0]
    while high>6:high-=6
    while low>high:low-=6
    return (high-low)*.5


def helper(rgb,current,previous,following,*,allow_fixed_point_overshoot=False):
    upper=1.001 if allow_fixed_point_overshoot else 1
    if len(rgb)!=3 or not all(math.isfinite(v) and 0<=v<=upper for v in rgb):
        raise ValueError('Require bounded finite RGB')
    hue=cone_hue(rgb);hi,lo=max(rgb),min(rgb);light=(hi+lo)*.5
    saturation=0. if hi==lo else (hi-lo)/((hi+lo) if light>=.5 else (2-hi)-lo)
    low,high=current['low'][0],current['high'][0]
    width=current['width']
    if low>=high:
        if low==high:width=0.
        low-=6
    if high>6:high-=6
    if low>=high:low-=6
    sample=hue-6 if hue>high else hue
    if not (sample>=low and sample<high
            and max(0,current['low'][1])<=saturation<=min(1,current['high'][1])
            and max(0,current['low'][2])<=light<=min(1,current['high'][2])):
        return [hue,hue,0.,0.]
    left=min((high-low)*.5,extent(previous),width)
    right=min((high-low)*.5,extent(following),width)
    dh,ds,dl=current['delta']
    def blend(t,values,neighbor):
        weight=t+(1/(1+math.exp(-12*(t-.5)))-t)/6
        return [weight*a+(1-weight)*b for a,b in zip(values,neighbor)]
    if sample<low+left:
        dh,ds,dl=blend((sample-low+left)/(left+left),(dh,ds,dl),previous['delta'])
    if sample>high-right:
        dh,ds,dl=blend((high-sample+right)/(right+right),(dh,ds,dl),following['delta'])
    adjusted=sample+dh
    if hue>high:adjusted+=6
    if adjusted>=6:adjusted-=6
    if adjusted<0:adjusted+=6
    if light==0 and saturation==0:return [adjusted,adjusted,0.,0.]
    return [adjusted,adjusted,ds*(saturation if ds>0 else 1),dl*saturation]


def transform(rgb,raw,*,allow_fixed_point_overshoot=False):
    if len(raw)<8:
        raise ValueError('Require bounded axis block header')
    kind,count=struct.unpack_from('<2i',raw)
    if kind!=2 or count not in (3,6,7,8) or len(raw)!=8+84*count:
        raise ValueError('Require observed three/six/seven/eight-group bounded axis block')
    groups=[decode(raw[8+i*84:8+(i+1)*84]) for i in range(count)]
    hue=cone_hue(rgb);h=ds=dl=0.
    for i,group in enumerate(groups):
        result=helper(rgb,group,groups[(i-1)%count],groups[(i+1)%count],allow_fixed_point_overshoot=allow_fixed_point_overshoot)
        h+=result[0]-hue;ds+=result[2];dl+=result[3]
    return compose(rgb,hue+h,ds,dl,allow_fixed_point_overshoot=allow_fixed_point_overshoot)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--final-rgb',action='store_true',help='Also verify composition against final RGB output')
    args=p.parse_args();data=json.loads(args.probe.read_text(encoding='utf-8'))
    passed=0;maximum=0.;failures=[]
    for row in data['legacyAxisCalls']:
        groups=[decode(bytes.fromhex(row[k])) for k in ('currentGroupHex','previousGroupHex','nextGroupHex')]
        expected=helper(row['inputRGB'],*groups)
        error=max(abs(a-b) for a,b in zip(expected,row['output']));maximum=max(maximum,error)
        passed+=error<=1e-14
        if error>1e-14 and len(failures)<20:failures.append({**row,'reference':expected,'error':error})
    result={'cameraAccess':False,'experimental':True,'cases':len(data['legacyAxisCalls']),
            'passed':passed,'maxError':maximum,'firstMismatches':failures}
    if args.final_rgb:
        blocks={case['name']:bytes.fromhex(case['parametersHex']) for case in data['cases']}
        rgb_passed=0;rgb_max=0.;rgb_failures=[]
        for row in data['rows']:
            expected=transform(row['rgb'],blocks[row['name']])
            error=max(abs(a-b) for a,b in zip(expected,row['output']));rgb_max=max(rgb_max,error)
            rgb_passed+=error<=1e-14
            if error>1e-14 and len(rgb_failures)<20:rgb_failures.append({**row,'reference':expected,'error':error})
        result['finalRGB']={'cases':len(data['rows']),'passed':rgb_passed,'maxError':rgb_max,'firstMismatches':rgb_failures}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    if not result['cases'] or passed!=result['cases']:raise SystemExit(1)
    if args.final_rgb and rgb_passed!=len(data['rows']):raise SystemExit(1)


if __name__=='__main__':main()
