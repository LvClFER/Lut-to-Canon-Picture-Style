"""Private independent reference for the bounded MLib 1cab0 pixel captures."""
import argparse
import json
import math
import struct
import hashlib
from pathlib import Path
from .modern_grid_reference import curve_settings, apply_selectors, axis_settings
from .legacy_grid_reference import selective_groups
from .cached_curve_reference import evaluate
from .polynomial_color_reference import transform
from .default_axis_reference import transform as axes
from .lab_math_reference import rgb_to_lab, lab_to_rgb
from .float_lab_reference import forward, inverse
from .color_math_reference import forward_color, inverse_color
from .packed10_reference import pack10,decoded_payload_blocks


def prepare(arguments):
    margin=arguments.get('researchSelectorMargin',.05)
    if not math.isfinite(margin) or not 0<=margin<=.25:raise ValueError('Unverified selector research margin')
    mode=arguments['mode']
    if mode not in (1,2): raise ValueError('Unverified pixel profile')
    groups=selective_groups(arguments['selectorBlock'])
    split=arguments['splitCount']
    if type(split) is not int or not 0<=split<=len(groups):
        raise ValueError('Invalid selector split')
    raw=bytes.fromhex(arguments['matrix240Hex'])
    if len(raw)!=240:raise ValueError('Require initialized 240-byte matrix')
    words=struct.unpack('<60i',raw)
    # a7f0 passes fixed16.16 coefficients straight to f620. Unlike the grid
    # wrappers, this path does not first truncate them to six decimals.
    coefficients=[words[r*20+c]/65536 for r in range(3) for c in range(19)]
    curves=curve_settings({key:arguments[key] or bytes(300).hex()
                           for key in ('preCurvesHex','postCurvesHex','thirdCurvesHex')})
    axis=arguments['axisBlock']
    if axis is not None:
        if axis['kind']!=2 or axis['count']!=6 or axis['points']!=5:
            raise ValueError('Unverified pixel axis geometry')
        axis_values,softness=axis_settings({'sixAxes512Hex':axis['initializedHex']})
    else:axis_values,softness=None,None
    return coefficients,mode,curves,groups[:split],groups[split:],axis_values,softness,arguments['thirdCurvesHex'] is not None,margin


def point(rgb,settings):
    coefficients,mode,curves,pre_groups,post_groups,axis_values,softness,luminance,margin=settings
    rgb=[evaluate(curves['preCurvesHex'][c],v) for c,v in enumerate(rgb)]
    rgb=[min(1,max(0,v)) for v in transform(rgb,coefficients)]
    rgb=apply_selectors(rgb,pre_groups,33,inplace_margin=margin)
    post=[]
    for c,v in enumerate(rgb):
        try:post.append(evaluate(curves['postCurvesHex'][c],v,allow_negative_subsample=bool(pre_groups)))
        except ValueError as error:
            raise ValueError(f'Post-curve channel{c}, position{v!r}, truncated index{math.trunc(v*(len(curves["postCurvesHex"][c])-1))}: {error}') from error
    rgb=post
    scale=2**24
    if axis_values is not None:
        if mode==1:
            rgb=[v/scale for v in lab_to_rgb(rgb_to_lab([math.trunc(v*scale) for v in rgb],24,2),24,2)]
        rgb=axes(rgb,axis_values,softness,allow_fixed_point_overshoot=mode==1)
        if mode==1:
            rgb=[v/scale for v in lab_to_rgb(rgb_to_lab([math.trunc(v*scale) for v in rgb],24,2),24,2)]
    rgb=apply_selectors(rgb,post_groups,33,inplace_margin=margin)
    if luminance:
        rgb=[min(1,max(0,v)) for v in rgb]
        lab=forward(forward_color(rgb,mode+9),12)
        # Native 1de30 evaluates the unnormalized 0..255 cached coordinate.
        values=curves['thirdCurvesHex'][0]
        position=(lab[0]/100*255)/(len(values)-1)
        lab[0]=(evaluate(values,position)*255)/255*100
        rgb=inverse_color(inverse(lab,12),mode+9)[0]
    return [min(1,max(0,v)) for v in rgb]


def main():
    from .compiler_regression import cipher_tables
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dll',type=Path,help='Require all 1000 pixels and compare packed bytes to private native output')
    parser.add_argument('--route-trace',action='store_true',help='Read private per-model trace files instead of field experiments')
    args=parser.parse_args();source=json.loads(args.trace.read_text(encoding='utf-8'))
    keys=cipher_tables(args.dll) if args.dll else None
    checks=[]
    for row in source['files'] if args.route_trace else source['experiments']:
        if row.get('error'):raise ValueError('Trace includes a failed native compilation')
        name=row['source'] if args.route_trace else row['name']
        captures=row['mlibCalls']['captures']
        pixels=[c for c in captures if c['functionRva']=='0x1cab0']
        packers=[c for c in captures if c['functionRva']=='0x49e00']
        decoded=[]
        if keys:
            payload=Path(row['privateResearchPayload']).read_bytes()
            if hashlib.sha256(payload).hexdigest()!=row['payloadSha256']:raise ValueError('Private payload hash mismatch')
            decoded=decoded_payload_blocks(payload,keys)
            if len(pixels)!=len(packers):raise ValueError('Pixel/packer contexts do not map one-to-one')
        for context_index,capture in enumerate(pixels):
            if capture['functionRva']!='0x1cab0':continue
            settings=prepare(capture['initializedArguments'])
            failures=[];maximum=0.;total=0;computed=[]
            for sample in capture['samples']:
                reference=point(sample['input'],settings)
                computed.append(reference)
                error=max(abs(a-b) for a,b in zip(reference,sample['output']))
                maximum=max(maximum,error);total+=1
                if error>1e-12 and len(failures)<4:failures.append({'sample':sample,'reference':reference,'error':error})
            packing=[]
            if keys:
                if total!=1000 or [s['callIndex'] for s in capture['samples']]!=list(range(1,1001)):
                    raise ValueError('Require all ordered 1000 pixel calls')
                scale=255 if row.get('cameraId',source['cameraId']) in (0x80000382,0x80000401) else 256
                values=[min(288,max(0,rgb[c]*scale)) for c in range(3) for rgb in computed]
                expected=bytes.fromhex(packers[context_index]['nativePackedHex'])
                for alternate in (False,True):
                    packed=pack10(values,alternate)
                    packing.append({'alternate':alternate,'nativePackedExact':packed==expected,
                                    'payloadLocations':[{'offset':o,'seed':s} for o,s,block in decoded if block==packed]})
            checks.append({'source':name,'cameraId':row.get('cameraId',source['cameraId']),'mode':settings[1],'samples':total,'maxError':maximum,
                           'passed':total>0 and maximum<=1e-12 and (not keys or any(p['nativePackedExact'] and p['payloadLocations'] for p in packing)),
                           'packing':packing,'failures':failures})
    report={'cameraAccess':False,'compilerPatched':False,'sampledOnly':True,'checks':checks,
            'passed':sum(c['passed'] for c in checks)}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(checks),'passed':report['passed'],'maxError':max((c['maxError'] for c in checks),default=0)}))
    if not checks or report['passed']!=len(checks):raise SystemExit(1)


if __name__=='__main__':main()
