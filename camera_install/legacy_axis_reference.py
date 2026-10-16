"""Verified preceding two-group global axis geometry, private math only."""
import argparse
import json
import math
import struct
from pathlib import Path
from .default_axis_reference import cone_hue
from .axis_composition_reference import compose


def adjustments(raw):
    if len(raw)!=176:raise ValueError('Require initialized two-group axis block')
    words=struct.unpack('<44i',raw)
    first=[5,0,0,0,0,1,0,0,0,2,0,0,0,3,0,0,0,5,0,0,0]
    second=[5,0,180,50,50,1,0,0,0,2,360,100,100,3,*words[37:40],5,5,5,5]
    if list(words)!=[2,2]+first+second:
        raise ValueError('Nondefault preceding global axis geometry not mapped')
    return words[37:40]


def transform(rgb,values,*,allow_fixed_point_overshoot=False):
    upper=1.001 if allow_fixed_point_overshoot else 1
    if len(rgb)!=3 or not all(math.isfinite(v) and 0<=v<=upper for v in rgb):
        raise ValueError('Require bounded finite RGB')
    if len(values)!=3 or not all(math.isfinite(v) for v in values):raise ValueError('Require three finite deltas')
    high,low=max(rgb),min(rgb);light=(high+low)*.5
    saturation=(high-low)/((high+low) if light>=.5 else (2-high)-low)
    dh,ds,dl=values
    return compose(rgb,cone_hue(rgb)+dh/60,ds/100*(saturation if ds>0 else 1),dl/100*saturation,
                   allow_fixed_point_overshoot=allow_fixed_point_overshoot)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();data=json.loads(args.probe.read_text(encoding='utf-8'))
    values={c['name']:adjustments(bytes.fromhex(c['parametersHex'])) for c in data['cases']}
    failures=[];maximum=0.;affected=0;passed=0
    for row in data['rows']:
        actual=transform(row['rgb'],values[row['name']])
        error=max(abs(a-b) for a,b in zip(actual,row['output']));maximum=max(maximum,error)
        affected+=max(abs(a-b) for a,b in zip(row['rgb'],row['output']))>1e-14
        passed+=error<=1e-14
        if error>1e-14 and len(failures)<20:failures.append({**row,'reference':actual,'error':error})
    result={'cameraAccess':False,'scope':'verified two-group global axis geometry only',
            'cases':len(data['rows']),'passed':passed,'affected':affected,'maxError':maximum,'firstMismatches':failures}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not data['rows'] or passed!=len(data['rows']):raise SystemExit(1)


if __name__=='__main__':main()
