"""Independent bounded fixed-point tetrahedral helper, offline research only."""
import argparse
import hashlib
import json
from pathlib import Path


def interpolate(values,coordinates):
    if len(values)!=3000 or len(coordinates)!=3 or any(type(v) is not int or not 0<=v<=9216 for v in coordinates):
        raise ValueError('Require planar 10-node table and safe fixed-point coordinates')
    scaled=[v>>4 for v in coordinates]
    cells=[v//64 for v in scaled]; fractions=[v%64 for v in scaled]
    order=sorted(range(3),key=lambda i:fractions[i],reverse=True)
    vertices=[cells.copy()]
    for axis in order:
        point=vertices[-1].copy(); point[axis]+=1; vertices.append(point)
    a,b,c=[fractions[i] for i in order]
    weights=[64-a,a-b,b-c,c]
    result=[]
    for channel in (0,2,1):
        total=0
        for point,weight in zip(vertices,weights):
            # Endpoint neighbor addresses have zero weight; never read padding.
            if weight == 0:
                continue
            index=(point[0]*10+point[1])*10+point[2]
            total+=weight*values[channel*1000+index]
        result.append(((total+2**31)%2**32)-2**31)
    return result


def profile_rgb16(values, coordinates):
    """Observed DppCore profile lattice; reuses the compiler's integer kernel."""
    if len(coordinates)!=3 or any(type(v) is not int or not 0<=v<=65535 for v in coordinates):
        raise ValueError('Require three unsigned RGB16 coordinates')
    if len(values)!=3000 or any(type(v) is not int or not -(2**31)<=v<2**31 for v in values):
        raise ValueError('Require 3000 signed 32-bit profile lattice values')
    totals=interpolate(values,[v>>3 for v in coordinates])
    # The profile wrapper restores RGB order and wraps its final 32-bit shift.
    shifted=[((totals[c]*4+2**31)%2**32)-2**31 for c in (0,2,1)]
    return [max(0,min(65535,v)) for v in shifted]


def table(pattern):
    result=[]
    for channel in range(3):
        for r in range(10):
            for g in range(10):
                for b in range(10):
                    if pattern=='identity': v=(r,g,b)[channel]*64
                    elif pattern=='modular': v=(r*19+g*37+b*13+channel*23)%1024
                    elif pattern=='signed': v=(r*17+g*71+b*53+channel*19)%1024-512
                    elif pattern=='impulse': v=(channel+1)*100 if (r,g,b)==(4,5,6) else 0
                    elif pattern=='overflow': v=(r*19+g*37+b*13+channel*23)*1000000
                    else: raise ValueError('Unknown synthetic grid')
                    result.append(v)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); raw=args.probe.read_bytes(); source=json.loads(raw)
    tables={p:table(p) for p in ('identity','modular','signed','impulse','overflow')}
    rows=[]
    for row in source['rows']:
        expected=interpolate(tables[row['pattern']],row['coordinates'])
        rows.append({'pattern':row['pattern'],'coordinates':row['coordinates'],
                     'guard':row.get('guard'),
                     'expected':expected,'native':row['output'],'passed':expected==row['output']})
    endpoint_pairs={}
    for row in source['rows']:
        if 'guard' in row:
            key=(row['pattern'],tuple(row['coordinates']))
            endpoint_pairs.setdefault(key,{})[row['guard']]=row['output']
    if any(set(pair)!={0,123456789} or pair[0]!=pair[123456789]
           for pair in endpoint_pairs.values()):
        raise ValueError('Endpoint padding independence not demonstrated')
    result={'cameraAccess':False,'probeSha256':hashlib.sha256(raw).hexdigest(),
            'nativeDllSha256':source.get('dllSha256'),
            'endpointGuardPairs':len(endpoint_pairs),
            'rows':rows,'passed':sum(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':result['passed']}))
    if result['passed'] != len(rows):
        raise ValueError('Independent tetrahedral replay differs from native output')


if __name__=='__main__': main()
