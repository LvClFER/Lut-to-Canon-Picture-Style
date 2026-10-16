"""Experimental independent f730 polynomial gamut correction, offline only."""
import argparse
import json
import math
from pathlib import Path
from .polynomial_color_reference import transform


def correct(rgb,coefficients):
    if len(rgb)!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in rgb):
        raise ValueError('Require bounded finite source RGB')
    output=transform(rgb,coefficients)
    if all(0<=v<=1 for v in output):return output
    centre=(max(rgb)+min(rgb)-1)*.25+.5
    direction=[centre-v for v in rgb]
    distance=math.sqrt(direction[1]*direction[1]+direction[0]*direction[0]+direction[2]*direction[2])
    if distance==0:raise ValueError('Degenerate gamut direction not mapped')
    direction=[v/distance for v in direction]
    position=list(rgb);clipped=[min(1,max(0,v)) for v in output]
    step=32.;previous_valid=True
    for _ in range(256):
        position=[v+d/step for v,d in zip(position,direction)]
        output=transform(position,coefficients)
        valid=min(output)>=0 and max(output)<=1
        if valid==previous_valid:
            step*=-2;previous_valid=not previous_valid
        elif step!=32:step+=step
        if abs(step)>=513:break
    else:raise ValueError('Gamut iteration bound exceeded')
    fade=(max(0,min(.4,centre))/.4 if centre<.4 else
          max(0,min(.4,1-centre))/.4 if centre>.6 else 1.)
    return [v*fade+old*(1-fade) for v,old in zip(output,clipped)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();data=json.loads(args.probe.read_text(encoding='utf-8'))
    passed=0;maximum=0.;failures=[]
    for row in data['rows']:
        actual=correct(row['rgb'],row['coefficients'])
        error=max(abs(a-b) for a,b in zip(actual,row['output']));maximum=max(maximum,error)
        passed+=error<=1e-14
        if error>1e-14 and len(failures)<20:failures.append({**row,'reference':actual,'error':error})
    result={'cameraAccess':False,'experimental':True,'cases':len(data['rows']),
            'passed':passed,'maxError':maximum,'firstMismatches':failures}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not result['cases'] or passed!=result['cases']:raise SystemExit(1)


if __name__=='__main__':main()
