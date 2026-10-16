"""Four-point kind-1 selective color, bounded captured adjustments only."""
import argparse
import json
import math
import struct
from pathlib import Path
from .default_axis_reference import cone_hue


def decode_group(raw):
    if len(raw) not in (76,92):raise ValueError('Require bounded four/five-point group')
    words=struct.unpack('<'+str(len(raw)//4)+'i',raw)
    count=(len(raw)-12)//16
    if words[:3]!=(1,1,count): raise ValueError('Require one kind-1 group')
    points={words[3+i*4]:words[4+i*4:7+i*4] for i in range(count)}
    if set(points)!=set(range(count)): raise ValueError('Unknown point tags')
    result={tag:(values[0]/60,values[1]/100,values[2]/100) for tag,values in points.items()}
    centre,low,high=result[0],result[1],result[2]
    lower_h=low[0]-6 if low[0]>high[0] else low[0]
    # Deltas are bounded by each selector's extent, not global +/-0.5.
    # The broad synthetic S/L centre .5 and bounds 0..1 merely yield .5.
    lower=(lower_h,low[1],low[2])
    result[3]=tuple(min(hi-c,max(-(c-lo),d))
                    for c,lo,hi,d in zip(centre,lower,high,result[3]))
    return result


def target_selector(rgb,points,nodes):
    if 4 not in points or points[4][2]<0 or nodes not in (9,10,17,33):return points
    centre=points[0];centre_rgb=inverse_cone(*centre)
    step={9:40,10:32,17:16,33:8}[nodes]
    quantized=[]
    for value,sample in zip(centre_rgb,rgb):
        scaled=value*256
        if math.trunc(scaled)%step:
            if sample>value: value=(math.floor(scaled/step)+1)*step/256
            elif value>sample:value=math.floor(scaled/step)*step/256
        quantized.append(value)
    changed=cone(quantized)
    lower_h=points[1][0]-6 if points[1][0]>points[2][0] else points[1][0]
    lower=(lower_h,*points[1][1:])
    return {0:changed,
            1:tuple(q-(c-lo) for q,c,lo in zip(changed,centre,lower)),
            2:tuple(q+(hi-c) for q,c,hi in zip(changed,centre,points[2])),
            3:tuple(target-c for target,c in zip(points[4],centre))}


def cone(rgb):
    maximum,minimum=max(rgb),min(rgb)
    light=(maximum+minimum)*.5
    sat=(maximum-minimum)/((maximum+minimum) if light>=.5 else (2-maximum)-minimum)
    return cone_hue(rgb),sat,light


def inverse_cone(h,s,l):
    high=l+(1+abs(2*l-1))*s*.5;low=2*l-high
    h%=6;sector=int(h);fraction=h-sector
    up=high-(high-low)*(1-fraction);down=high-(high-low)*fraction
    return ((high,up,low),(down,high,low),(low,high,up),
            (low,down,high),(up,low,high),(high,low,down))[sector]


def weights(hsl,points):
    centre,low,high=points[0],points[1],points[2]
    lower_h=low[0]-6 if low[0]>high[0] else low[0]
    left=centre[0]-lower_h;right=high[0]-centre[0]
    hue=(hsl[0]-centre[0])%6
    wh=1-hue/right if right>hue else (1-(6-hue)/left if left>6-hue else 0.)
    if (left==0 and right==0) or hue==0: wh=1.
    def triangular(value,c,lo,hi):
        a,b=c-lo,hi-c;distance=value-c
        if (a==0 and b==0) or distance==0: return 1.
        if -a<=distance<=0: return distance/a+1
        if 0<=distance<=b: return 1-distance/b
        return 0.
    ws=triangular(hsl[1],centre[1],low[1],high[1])
    if centre[1]==0 and centre[1]-low[1]==0: ws=-ws
    wl=triangular(hsl[2],centre[2],low[2],high[2])
    return wh,ws,wl


def compose(hsl,deltas,weighted,*,allow_strong_gamut=False):
    wh,ws,wl=weighted
    amount=1-(1-wh*abs(ws)*wl)  # power=1 in captured four-point groups
    ds=deltas[1] if ws>=0 else 0.
    h,s,l=hsl
    result=[(h+amount*deltas[0])%6,s+amount*ds,l+amount*deltas[2]]
    # The native helper additionally constrains stronger out-of-gamut
    # adjustments. Do not silently substitute clipping for that branch.
    if not 0<=result[2]<=1 or result[1]<0 or result[1]>2*min(result[2],1-result[2]):
        if not allow_strong_gamut:
            raise ValueError('Native composition gamut branch requires explicit research opt-in')
        if result[1]>2*(.5-abs(.5-result[2])):
            dl=deltas[2]
            if ds==0:
                if dl!=0:
                    amount=((1-s*.5-l) if result[2]>=.5 else (s*.5-l))/dl
            else:
                slope=dl/ds
                intercept=l-s*slope
                lower=intercept/(.5-slope) if slope!=.5 else 2.
                upper=(1-intercept)/(slope+.5) if slope!=-.5 else 2.
                amount=(result[1]-s)/ds
                for candidate in (lower,upper):
                    if 0<=candidate<=1:
                        boundary_amount=(candidate-s)/ds
                        if boundary_amount>0: amount=boundary_amount
        result=[(h+amount*deltas[0])%6,min(1,max(0,s+amount*ds)),
                min(1,max(0,l+amount*deltas[2]))]
    return result


def transform(rgb,points,*,allow_inplace_gamut=False,allow_strong_gamut=False,nodes=33,inplace_margin=.05):
    # In-place groups preserve harmless floating reconstruction overshoot;
    # clipping it before the next selector changes the native arithmetic.
    if not math.isfinite(inplace_margin) or not 0<=inplace_margin<=.25:
        raise ValueError('Invalid bounded in-place research margin')
    margin=inplace_margin if allow_inplace_gamut else 1e-12
    if len(rgb)!=3 or not all(math.isfinite(v) and -margin<=v<=1+margin for v in rgb):
        raise ValueError('Require bounded finite RGB')
    points=target_selector(rgb,points,nodes)
    hsl=cone(rgb);w=weights(hsl,points)
    if any(v==0 for v in w): return tuple(rgb)
    return inverse_cone(*compose(hsl,points[3],w,allow_strong_gamut=allow_strong_gamut))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--strong-gamut',action='store_true',help='Validate the translated native linear boundary branch')
    args=p.parse_args();data=json.loads(args.probe.read_text(encoding='utf-8'))
    groups={c['name']:decode_group(bytes.fromhex(c['parametersHex'])) for c in data['cases']}
    checks=[];affected=0;failures=[];max_error=0.
    for row in data['rows']:
        active=max(abs(a-b) for a,b in zip(row['rgb'],row['output']))>1e-14
        affected+=active
        try:
            expected=transform(row['rgb'],groups[row['name']],allow_strong_gamut=args.strong_gamut,nodes=row.get('nodes',33))
            error=max(abs(a-b) for a,b in zip(expected,row['output']));max_error=max(max_error,error)
            passed=error<=1e-14
            if not passed and len(failures)<20: failures.append({**row,'expected':expected,'error':error})
        except ValueError as e:
            passed=False
            if len(failures)<20: failures.append({**row,'unsupported':str(e)})
        checks.append(passed)
    result={'cameraAccess':False,'scope':'four/five-point kind-1 groups, power1, '+('native boundary intersections' if args.strong_gamut else 'safe composition gamut'),
            'cases':len(checks),'passed':sum(checks),'nativeAffectedCases':affected,'maxError':max_error,'firstMismatches':failures}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not checks or not all(checks): raise SystemExit(1)


if __name__=='__main__': main()
