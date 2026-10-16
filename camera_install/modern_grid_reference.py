"""Independent modern chain for default axis geometry and sampled curves."""
import argparse
import json
import math
import struct
import hashlib
from pathlib import Path
from .cached_curve_reference import evaluate
from .color_math_reference import forward_color,inverse_color
from .float_lab_reference import forward as xyz_lab,inverse as lab_xyz
from .lab_math_reference import rgb_to_lab,lab_to_rgb
from .polynomial_color_reference import transform
from .gamut_policy_reference import correct as gamut_correct
from .default_axis_reference import transform as axis_transform, adjustments
from .packed17_reference import pack17
from .full33_packing_reference import pack_full33
from .cipher_stream_reference import decode
from .curve_normalization_research import normalize_curve
from .curve_bspline_research import quadratic_samples
from .curve_finalization_research import finalize_samples
from .legacy_sector_reference import transform as selective


def curve_settings(arguments,allow_unused_third_channels=False):
    result={}
    result['gamutPolicy']=arguments.get('numericArguments',[1,1])[1]
    for key in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
        raw=bytes.fromhex(arguments[key])
        if len(raw)!=300: raise ValueError('Require three initialized curve records')
        curves=[]
        for offset in range(0,300,100):
            # Observed zero-count fallback initializes a 301-sample identity,
            # unlike the normal explicit 255 endpoint (256 samples).
            if raw[offset:offset+100]==bytes(100):
                curves.append([i/300 for i in range(301)])
                continue
            normalized,domain=normalize_curve(raw[offset:offset+100])
            values=struct.unpack('<'+str(len(normalized)//8)+'d',normalized)
            points=list(zip(values[::2],values[1::2]))
            if len(points)<2 or points[0][0]!=0 or points[-1][0]!=1:
                raise ValueError('Unverified curve endpoints')
            if len(points)==2:
                samples=[points[0][1]+(points[1][1]-points[0][1])*(i/(domain-1)) for i in range(domain)]
            else: samples=list(quadratic_samples(points,domain))
            curves.append(finalize_samples(points,samples))
        result[key]=curves
    # Only luminance is mapped in the XYZ/Lab stage; reject nonidentity
    # chromatic curves rather than silently ignoring unverified behavior.
    if not allow_unused_third_channels and any(curve!=[i/(len(curve)-1) for i in range(len(curve))] for curve in result['thirdCurvesHex'][1:]):
        raise ValueError('Chromatic Lab curves not independently mapped')
    return result


def axis_settings(arguments):
    raw=bytes.fromhex(arguments['sixAxes512Hex'])
    axes=struct.unpack('<128i',raw)
    if axes[:2]!=(2,6): raise ValueError('Unverified axis header')
    softness=axes[20]
    return adjustments([raw[8+i*84:8+(i+1)*84] for i in range(6)],softness),softness


def selector_settings(arguments):
    # Local import avoids the preceding reference's curve-settings dependency.
    from .legacy_grid_reference import selective_groups
    if 'oldParameterBlock' not in arguments or 'additionalParameterBlock' not in arguments:
        raise ValueError('Require bounded initialized selector captures')
    return selective_groups(arguments['oldParameterBlock']),selective_groups(arguments['additionalParameterBlock'])


def apply_selectors(rgb,groups,nodes,*,inplace_margin=.05):
    for group in groups:
        original=tuple(rgb)
        changed=selective(original,group,allow_inplace_gamut=True,allow_strong_gamut=True,nodes=nodes,inplace_margin=inplace_margin)
        rgb=[(v-old)+current for v,old,current in zip(changed,original,rgb)]
    return rgb


def prepare(arguments,experimental_selectors=False,allow_unused_third_channels=False):
    curve_settings(arguments,allow_unused_third_channels)
    if experimental_selectors:selector_settings(arguments)
    elif arguments['oldParameters512Hex'] is not None: raise ValueError('Legacy sectors not yet supported')
    header=arguments.get('additionalParametersHeader8Hex')
    if not experimental_selectors and header not in (None,'0100000000000000'): raise ValueError('Unverified additional parameter header')
    empty=arguments.get('additionalEmptyParametersHex')
    if empty is None and arguments.get('additionalParameters512Hex'): empty=arguments['additionalParameters512Hex'][:16]
    if not experimental_selectors and empty not in (None,'0100000000000000'): raise ValueError('Nonempty additional sectors')
    axis_settings(arguments)
    words=struct.unpack('<60i',bytes.fromhex(arguments['matrix240Hex']))
    coefficients=[math.trunc(words[r*20+c]/65536*1e6)/1e6 for r in range(3) for c in range(19)]
    mode,policy=arguments['numericArguments']
    if mode not in (1,2) or policy not in (0,1,2): raise ValueError('Unverified profile/gamut route')
    return coefficients,mode


def point(rgb,coefficients,mode,full33=False,axis_values=None,softness=20,curves=None):
    if axis_values is None: axis_values=[(0,0,0)]*6
    values=[i/255 for i in range(256)]
    pre=curves['preCurvesHex'] if curves else [values]*3
    post=curves['postCurvesHex'] if curves else [values]*3
    luminance=curves['thirdCurvesHex'][0] if curves else values
    rgb=[evaluate(pre[c],v) for c,v in enumerate(rgb)]
    policy=curves.get('gamutPolicy',1) if curves else 1
    rgb=(gamut_correct(rgb,coefficients) if policy==2 else
         transform(rgb,coefficients) if policy==0 else
         [min(1,max(0,v)) for v in transform(rgb,coefficients)])
    rgb=apply_selectors(rgb,curves.get('preGroups',[]) if curves else [],33 if full33 else 17)
    rgb=[evaluate(post[c],v,allow_negative_subsample=policy!=1 or bool(curves and curves.get('preGroups'))) for c,v in enumerate(rgb)]
    maximum=2**24
    if mode==1:
        scale=2**24
        integers=[min(maximum,max(0,math.trunc(v*scale))) for v in rgb]
        rgb=[v/scale for v in lab_to_rgb(rgb_to_lab(integers,24,1),24,2)]
        rgb=axis_transform(rgb,axis_values,softness,allow_fixed_point_overshoot=True)
        integers=[min(maximum,max(0,math.trunc(v*scale))) for v in rgb]
        rgb=[v/scale for v in lab_to_rgb(rgb_to_lab(integers,24,2),24,1)]
    else:
        rgb=axis_transform(rgb,axis_values,softness)
    rgb=apply_selectors(rgb,curves.get('postGroups',[]) if curves else [],33 if full33 else 17)
    rgb=[min(1,max(0,v)) for v in rgb]
    lab=xyz_lab(forward_color(rgb,mode),12)
    lab[0]=evaluate(luminance,lab[0]/100)*100
    rgb=inverse_color(lab_xyz(lab,12),mode)[0]
    if full33: return [float(math.trunc(v*65536*.5+.5)) for v in rgb]
    return [min(255.75,max(0,v*256)) for v in rgb]


def packing_passed(checks,require_payload=False):
    if not checks or not all(p['independentEqualsNativeGrid'] for p in checks):return False
    # The two coefficient matrices are candidates, not two blocks emitted
    # for every profile. Mode1/mode2 choose different native packers.
    return not require_payload or any(p.get('nativePayloadBlocks') or p.get('nativePayloadOffsets') for p in checks)


def named_field_cases(experiments,name):
    selected=[row for row in experiments if row['name']==name]
    if len(selected)!=1:raise ValueError('Require one exact named experiment')
    return selected


def main():
    from .compiler_regression import cipher_tables
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dll',type=Path,help='Also verify independently computed bytes in captured private native payloads')
    parser.add_argument('--start-case',type=int,default=0,help='Validate an explicit suffix of file cases; earlier cases are not claimed by this report')
    parser.add_argument('--experimental-selectors',action='store_true',help='Explicitly validate bounded pre/post kind1 selector captures')
    parser.add_argument('--field-experiments',action='store_true',help='Read a private FIELD_EXPERIMENTS report rather than a route trace')
    parser.add_argument('--case-name',help='Validate one exact named field experiment; does not claim the other cases')
    parser.add_argument('--experimental-unused-third-channels',action='store_true',help='Explicit research hypothesis:11220 uses only channel0 of third curve group; not a general format claim')
    args=parser.parse_args(); source=json.loads(args.trace.read_text(encoding='utf-8'))
    if args.field_experiments:
        if args.case_name:
            try:source['experiments']=named_field_cases(source['experiments'],args.case_name)
            except ValueError as error:parser.error(str(error))
        if args.dll and any(not row.get('privateResearchPayload') for row in source['experiments']):
            parser.error('Final comparison requires retained private field payloads')
        if any('error' in row for row in source['experiments']):parser.error('Field report contains failed compiler experiments')
        source={'files':[{'source':row['name'],'model':hex(source['cameraId']),
            'originSource':str(args.trace.resolve()),'mlibCalls':row['mlibCalls'],
            'privateResearchPayload':row.get('privateResearchPayload'),'payloadSha256':row.get('payloadSha256')}
            for row in source['experiments']]}
    if args.case_name and not args.field_experiments:parser.error('--case-name requires --field-experiments')
    keys=cipher_tables(args.dll) if args.dll else None
    checks=[];unsupported=[]
    if not 0<=args.start_case<len(source['files']):parser.error('Invalid start-case index')
    for row in source['files'][args.start_case:]:
        payload=None;decoded=[]
        if keys is not None and any(c['functionRva']=='0x11220' for c in row['mlibCalls']['captures']):
            payload=Path(row['privateResearchPayload']).read_bytes()
            if hashlib.sha256(payload).hexdigest()!=row['payloadSha256']:
                raise ValueError('Private payload differs from recorded compiler output')
            if len(payload) in (78980,83076):
                decoded=[decode(payload[o:o+19652],keys,0xb8ed if i%2==0 else 0x33137)
                         for i,o in enumerate((372,20024,39676,59328))]
            elif len(payload)!=431616: raise ValueError('Unverified modern native payload geometry')
        for capture in row['mlibCalls']['captures']:
            if capture['functionRva']!='0x11220': continue
            coefficients,mode=prepare(capture['initializedArguments'],args.experimental_selectors,args.experimental_unused_third_channels)
            axis_values,softness=axis_settings(capture['initializedArguments'])
            curves=curve_settings(capture['initializedArguments'],args.experimental_unused_third_channels)
            if args.experimental_selectors:
                curves['preGroups'],curves['postGroups']=selector_settings(capture['initializedArguments'])
            grid=next(g for g in capture['gridArguments'] if g.get('initializedOutputFloat64Hex'))
            nodes=grid['nodes']; n=nodes**3
            native=struct.unpack('<'+str(n*3)+'d',bytes.fromhex(grid['initializedOutputFloat64Hex']))
            failures=[]; max_error=0.; computed=[0.]*(n*3); mismatches=0;unsafe=None
            for r in range(nodes):
                if unsafe:break
                for g in range(nodes):
                    if unsafe:break
                    for b in range(nodes):
                        rgb=[min(v/(nodes-1),1 if nodes==33 else .9990234375) for v in (r,g,b)]
                        try:
                            expected=point(rgb,coefficients,mode,nodes==33,axis_values,softness,curves)
                        except ValueError as error:
                            unsafe={'source':row['source'],'nodes':nodes,'mode':mode,
                                    'coordinates':[r,g,b],'reason':str(error)}
                            break
                        index=(r*nodes+g)*nodes+b
                        for c in range(3): computed[c*n+index]=expected[c]
                        error=max(abs(expected[c]-native[c*n+index]) for c in range(3))
                        max_error=max(max_error,error)
                        if error>1e-10:
                            mismatches+=1
                            if len(failures)<12: failures.append({'coordinates':[r,g,b],'expected':expected,'native':[native[c*n+index] for c in range(3)],'error':error})
            if unsafe:
                unsupported.append(unsafe)
                args.output.write_text(json.dumps({'cameraAccess':False,'complete':False,
                    'startCase':args.start_case,'checks':checks,'unsupported':unsupported},indent=2),encoding='utf-8')
                print(json.dumps({'unsupported':unsafe}),flush=True)
                continue
            packing=[]
            if nodes==17:
                observed=[bytes.fromhex(c['nativePackedHex']) for c in row['mlibCalls']['captures'] if c['functionRva']=='0x4bb40']
                for alternate in (False,True):
                    expected_pack=pack17(computed,alternate); native_pack=pack17(native,alternate)
                    packing.append({'alternate':alternate,'independentEqualsNativeGrid':expected_pack==native_pack,
                                    'observedFinalPackerMatches':sum(native_pack==p for p in observed),
                                    'nativePayloadBlocks':[i for i,p in enumerate(decoded) if p==expected_pack] if payload is not None else None})
            elif nodes==33:
                expected_pack=pack_full33(computed);native_pack=pack_full33(native)
                packing.append({'independentEqualsNativeGrid':expected_pack==native_pack,
                    'nativePayloadOffsets':[o for o in (372,215994) if payload[o:o+len(expected_pack)]==expected_pack] if payload is not None else None})
            checks.append({'source':row['source'],'model':row.get('model'),'originSource':row.get('originSource'),'nodes':nodes,'mode':mode,'maxError':max_error,
                           'mismatchedNodes':mismatches,'passed':not failures,'firstMismatches':failures,'packingChecks':packing})
            # Retain completed comparisons if a later unverified record fails.
            args.output.write_text(json.dumps({'cameraAccess':False,'complete':False,'startCase':args.start_case,'checks':checks,'unsupported':unsupported},indent=2),encoding='utf-8')
            print(json.dumps({'source':Path(row['source']).name,'nodes':nodes,'mode':mode,
                              'maxError':max_error,'mismatchedNodes':mismatches}),flush=True)
    result={'cameraAccess':False,'complete':True,'startCase':args.start_case,'scope':'sampled RGB/luminance curves and verified default axis geometry',
            'selectedCaseName':args.case_name,
            'experimentalUnusedThirdChannels':args.experimental_unused_third_channels,
            'experimentalSelectors':args.experimental_selectors,'checks':checks,'unsupported':unsupported}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(checks),'passed':sum(c['passed'] for c in checks)}))
    if unsupported or not checks or not all(c['passed'] and packing_passed(c['packingChecks'],keys is not None) for c in checks):
        raise SystemExit(1)


if __name__=='__main__': main()
