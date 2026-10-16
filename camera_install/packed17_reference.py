"""Independent observed Canon 17-node packing, private offline research only."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from .cipher_stream_reference import decode


def pack17_for_style(values, style_code: int, table_selector: int):
    """Apply the observed 4bb40 matrix branch, not a camera/model heuristic.

    style_code is the internal uint16 property1009, not a UI style index.
    This selects packing only; it does not compile a complete carrier.
    """
    if type(style_code) is not int or not 0 <= style_code <= 0xffff:
        raise ValueError('Require internal uint16 Picture Style code')
    if type(table_selector) is not int or not 0 <= table_selector <= 0xffffffff:
        raise ValueError('Require uint32 native table selector')
    return pack17(values, style_code in (0x81, 0x84) and table_selector == 1)


def pack17(values, alternate=False):
    if type(alternate) is not bool:
        raise ValueError('alternate must explicitly be boolean')
    n = 17**3
    if len(values)!=n*3 or not all(math.isfinite(v) for v in values):
        raise ValueError('Require three finite planar 17-node channels')
    if alternate:
        yr,yg,yb,br,bg,bb,rr,rg,rb = (.29922207,.586998487,.113779442,
            -.168724339,-.330994742,.499719081,.499719081,.41858388,.081135201)
    else:
        yr,yg,yb,br,bg,bb,rr,rg,rb = (.2979874,.5851238,.1168888,
            -.173047,-.339793,.5128404,.5009222,.417349,.0833729)
    result = [0]*n
    def chroma(v):
        v = max(-512.,min(511.,v*4))
        if v<0: v+=1024
        q = math.floor(v+.5)
        return (q if q<1024 else 0)&1023
    for r in range(17):
        for g in range(17):
            for b in range(17):
                i=(r*17+g)*17+b
                red,green,blue = values[i],values[n+i],values[2*n+i]
                y = min(1023,math.floor(((red*yr+green*yg)+blue*yb)*4+.5))&1023
                cb = chroma((red*br+green*bg)+blue*bb)
                cr = chroma((red*rr-green*rg)-blue*rb)
                result[(b*17+g)*17+r] = (y<<20)|(cb<<10)|cr
    return struct.pack('<'+str(n)+'I',*result)


def main():
    from .compiler_regression import cipher_tables
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=json.loads(args.trace.read_text(encoding='utf-8')); keys=cipher_tables(args.dll)
    rows=[]; failures=[]
    for case in source['files']:
        if case.get('error'):
            failures.append({'model':case['model'],'source':case['source'],'error':case['error']})
            continue
        payload=Path(case['privateResearchPayload']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=case['payloadSha256']:
            raise ValueError('Private payload differs from recorded compiler output')
        if len(payload) not in (78980,83076): continue
        decoded=[decode(payload[o:o+19652],keys,0xb8ed if i%2==0 else 0x33137)
                 for i,o in enumerate((372,20024,39676,59328))]
        for capture in case['mlibCalls']['captures']:
            if capture['functionRva']=='0x4bb40':
                values=struct.unpack('<'+str(17**3*3)+'d',bytes.fromhex(capture['inputPlanarFloat64Hex']))
                native=bytes.fromhex(capture['nativePackedHex'])
                modes=[mode for mode in (False,True) if pack17(values,mode)==native]
                matches=[i for i,block in enumerate(decoded) if native==block]
                rows.append({'model':case['model'],'functionRva':capture['functionRva'],
                             'tableIndex':capture['tableIndex'],'alternateModes':modes,
                             'payloadBlocks':matches,'passed':bool(modes) and bool(matches)})
                continue
            # Upstream stages can be changed again before packing. Do not
            # classify such intermediary grids as final packing failures.
            if any(c['functionRva']=='0x4bb40' for c in case['mlibCalls']['captures']): continue
            for grid in capture.get('gridArguments',[]):
                if grid['nodes']!=17 or not grid.get('initializedOutputFloat64Hex'): continue
                values=struct.unpack('<'+str(17**3*3)+'d',bytes.fromhex(grid['initializedOutputFloat64Hex']))
                candidates=[pack17(values,alternate) for alternate in (False,True)]
                matches=[(mode,i) for mode,candidate in enumerate(candidates) for i,block in enumerate(decoded) if candidate==block]
                rows.append({'model':case['model'],'functionRva':capture['functionRva'],
                             'matches':matches,'passed':bool(matches)})
    result={'cameraAccess':False,'compilerPatched':False,'rows':rows,'traceFailures':failures,'passed':sum(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':result['passed'],'traceFailures':len(failures)}))


if __name__=='__main__': main()
