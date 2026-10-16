"""Observed floating XYZ/Lab helpers, separate from fixed-point RGB/Lab."""
import argparse
import json
import math
from pathlib import Path


def white(mode):
    return (.9505,1.089) if mode==12 else (.9642,.8249)


def forward(xyz,mode):
    if len(xyz)!=3 or not all(math.isfinite(v) for v in xyz): raise ValueError('Require finite XYZ')
    wx,wz=white(mode); x,y,z=xyz
    def f(v): return v**(1/3) if v>.008856 else 7.787*v+16/116
    light=116*y**(1/3)-16 if y>.008856 else y*903.29
    return [light,500*(f(x/wx)-f(y)),200*(f(y)-f(z/wz))]


def inverse(lab,mode):
    if len(lab)!=3 or not all(math.isfinite(v) for v in lab): raise ValueError('Require finite Lab')
    wx,wz=white(mode); light,a,b=lab
    fy=(light+16)/116 if light>7.99953624 else light*7.787/903.29+16/116
    def f(v): return v**3 if v**3>.008856 else (v-16/116)/7.787
    return [f(fy+a/500)*wx,f(fy),f(fy-b/200)*wz]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); source=json.loads(args.probe.read_text(encoding='utf-8'))
    if not source.get('floatLab'): raise ValueError('Not a floating Lab probe')
    checks=[]
    for row in source['rows']:
        ef=max(abs(a-b) for a,b in zip(forward(row['input'],row['mode']),row['forward']))
        ei=max(abs(a-b) for a,b in zip(inverse(row['forward'],row['mode']),row['inverse']))
        checks.append({'mode':row['mode'],'input':row['input'],'forwardError':ef,'inverseError':ei,
                       'passed':ef<=1e-12 and ei<=1e-14 and row['rcForward']==0 and row['rcInverse']==0})
    result={'cameraAccess':False,'checks':checks,'passed':sum(r['passed'] for r in checks)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(checks),'passed':result['passed'],'maxForwardError':max(r['forwardError'] for r in checks),'maxInverseError':max(r['inverseError'] for r in checks)}))


if __name__=='__main__': main()
