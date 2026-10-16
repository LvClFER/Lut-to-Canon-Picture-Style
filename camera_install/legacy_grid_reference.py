"""Independent preceding 17-node branch, neutral kind-2 and kind-1 groups."""
import argparse
import json
import math
import struct
from pathlib import Path
from .modern_grid_reference import curve_settings
from .cached_curve_reference import evaluate
from .polynomial_color_reference import transform as polynomial
from .gamut_policy_reference import correct as gamut_correct
from .legacy_axis_reference import transform as axes,adjustments as axis_adjustments
from .legacy_six_axis_reference import transform as six_axes,decode_block as six_axis_block
from .legacy_axis_geometry_reference import transform as geometry_axes
from .legacy_sector_reference import decode_group,transform as selective
from .color_math_reference import forward_color,inverse_color
from .float_lab_reference import forward,inverse
from .packed17_reference import pack17
from .packed10_reference import pack10


def selective_groups(block):
    if block is None:return []
    if block.get('count')==0:
        if block.get('kind')!=1 or block.get('initializedHex')!=struct.pack('<2i',1,0).hex():
            raise ValueError('Invalid empty selective block')
        return []
    if block.get('kind')!=1 or block.get('points') not in (4,5) or not isinstance(block.get('count'),int) or not 1<=block['count']<=12:
        raise ValueError('Unverified selective group geometry')
    raw=bytes.fromhex(block['initializedHex']);stride=4+16*block['points']
    if len(raw)!=8+block['count']*stride or raw[:8]!=struct.pack('<2i',1,block['count']):
        raise ValueError('Invalid selective group block size/header')
    return [decode_group(struct.pack('<2i',1,1)+raw[o:o+stride]) for o in range(8,len(raw),stride)]


def prepare(a,experimental_geometry=False):
    pre_groups=selective_groups(a['oldParameterBlock'])
    neutral=a['axisParameterBlock']
    axis_values=(0,0,0)
    axis_kind='global'
    axis_widths=None
    if neutral is not None:
        if neutral['kind']!=2 or neutral['points']!=5: raise ValueError('Unverified neutral group geometry')
        raw=bytes.fromhex(neutral['initializedHex'])
        if experimental_geometry and len(raw)==260:
            axis_values=raw;axis_kind='geometry'
        elif len(raw)==512:
            if experimental_geometry:
                axis_values=raw;axis_kind='geometry'
            else:
                axis_values,axis_widths=six_axis_block(raw)
                axis_kind='six'
        else:
            axis_values=axis_adjustments(raw)
    groups=selective_groups(a['additionalParameterBlock'])
    raw=struct.unpack('<60i',bytes.fromhex(a['matrix240Hex']))
    coefficients=[math.trunc(raw[r*20+c]/65536*1e6)/1e6 for r in range(3) for c in range(19)]
    mode,policy=a['numericArguments']
    if mode not in (1,2) or policy not in (0,1,2): raise ValueError('Unverified profile/policy')
    curves=curve_settings({k:(v if v is not None else bytes(300).hex()) for k,v in a.items()
                           if k in ('preCurvesHex','postCurvesHex','thirdCurvesHex')})
    curves['applyLuminance']=a['thirdCurvesHex'] is not None
    curves['applyAxis']=neutral is not None
    curves['axisValues']=axis_values
    curves['axisKind']=axis_kind
    curves['axisWidths']=axis_widths
    curves['preGroups']=pre_groups
    curves['gamutPolicy']=policy
    return coefficients,mode,curves,groups


def point(rgb,coefficients,mode,curves,groups,output_scale=256,output_limit=255.75,selective_nodes=17):
    rgb=[evaluate(curves['preCurvesHex'][c],v) for c,v in enumerate(rgb)]
    policy=curves.get('gamutPolicy',1)
    rgb=(gamut_correct(rgb,coefficients) if policy==2 else
         polynomial(rgb,coefficients) if policy==0 else
         [min(1,max(0,v)) for v in polynomial(rgb,coefficients)])
    for group in curves.get('preGroups',[]):
        original=tuple(rgb)
        changed=selective(original,group,allow_inplace_gamut=True,allow_strong_gamut=True,nodes=selective_nodes,inplace_margin=curves.get('selectorMargin',.05))
        rgb=[(v-old)+current for v,old,current in zip(changed,original,rgb)]
    rgb=[evaluate(curves['postCurvesHex'][c],v,allow_negative_subsample=bool(curves.get('preGroups')) or policy!=1) for c,v in enumerate(rgb)]
    if curves.get('applyAxis',True):
        if curves.get('axisKind')=='geometry':rgb=list(geometry_axes(rgb,curves['axisValues']))
        else:
            rgb=list(six_axes(rgb,curves['axisValues'],curves['axisWidths'])
                     if curves.get('axisKind')=='six' else axes(rgb,curves.get('axisValues',(0,0,0))))
    # The captured compiler aliases fa40 input/output. Each ff60 group thus
    # sees the RGB modified by the preceding group, unlike disjoint buffers.
    for group in groups:
        original=tuple(rgb)
        changed=selective(original,group,allow_inplace_gamut=True,allow_strong_gamut=True,nodes=selective_nodes,inplace_margin=curves.get('selectorMargin',.05))
        rgb=[(v-old)+current for v,old,current in zip(changed,original,rgb)]
    if curves['applyLuminance']:
        rgb=[min(1,max(0,v)) for v in rgb]
        lab=forward(forward_color(rgb,mode),12)
        lab[0]=evaluate(curves['thirdCurvesHex'][0],lab[0]/100)*100
        rgb=inverse_color(inverse(lab,12),mode)[0]
    return ([v*output_scale for v in rgb] if output_limit is None else
            [min(output_limit,max(0,v*output_scale)) for v in rgb])


def flagged_point(indices,coefficients,mode,curves,groups,nodes=10,flag=1):
    """14bd0 sampling; the final two planes share a boundary extrapolation.

    Flag0 truncates after its distinct 1.1/30.9 correction. Flag1 uses
    1/31. Neither is an independent extrapolation on each RGB axis.
    """
    if nodes not in (9,10,17) or flag not in (0,1,2):
        raise ValueError('Unverified preceding grid nodes/flag')
    if len(indices)!=3 or any(not isinstance(i,int) or not 0<=i<nodes for i in indices):
        raise ValueError('Invalid preceding grid indices')
    scale,step,cap={9:(255.,40.,1.),10:(255.,32.,1.),17:(256.,16.,.9990234375)}[nodes]
    boundary=flag<2 and any(i>=nodes-2 for i in indices)
    if boundary:
        first=[min(min(i,nodes-3)*step/scale,cap) for i in indices]
        second=[min(min(i,nodes-2)*step/scale,cap) for i in indices]
        a=point(first,coefficients,mode,curves,groups,1,None,nodes)
        b=point(second,coefficients,mode,curves,groups,1,None,nodes)
        multiplier,subtraction,divisor=((8.,5.2,2.8) if flag==0 else (8.,5.,3.)) if nodes==9 else ((32.,1.1,30.9) if flag==0 else (32.,1.,31.))
        values=[(y*multiplier-x*subtraction)/divisor for x,y in zip(a,b)]
    else:
        values=point([min(i*step/scale,cap) for i in indices],coefficients,mode,curves,groups,1,None,nodes)
    limit=(nodes-1)*step if flag<2 or nodes in (9,10) else 255.75
    values=[min(limit,max(0,v*scale)) for v in values]
    return [float(math.trunc(v)) for v in values] if flag==0 else values


def compact_point(indices,coefficients,mode,curves,groups):
    return flagged_point(indices,coefficients,mode,curves,groups,10,1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--experimental-axis-geometry',action='store_true',help='Explicitly enable the nondefault six-sector reference')
    p.add_argument('--wide-selector-margin',action='store_true',help='Explicitly test accumulated selective RGB overshoot up to0.25; not clipping')
    p.add_argument('--field-experiments',action='store_true',help='Read a private FIELD_EXPERIMENTS report rather than a route trace')
    args=p.parse_args();source=json.loads(args.trace.read_text(encoding='utf-8'))
    if args.field_experiments:
        if any('error' in row for row in source['experiments']):p.error('Field report contains failed compiler experiments')
        source={'files':[{'source':row['name'],'model':hex(source['cameraId']),
            'originSource':str(args.trace.resolve()),'mlibCalls':row['mlibCalls']}
            for row in source['experiments']]}
    rows=[];unsupported=[]
    for case in source['files']:
        for item in case['mlibCalls']['captures']:
            if item['functionRva']!='0x14bd0': continue
            grid=next(g for g in item['gridArguments'] if g.get('initializedOutputFloat64Hex'))
            nodes=grid['nodes']
            if nodes not in (9,10,17):
                unsupported.append({'nodes':nodes,'reason':'Unverified grid geometry'});continue
            flag=struct.unpack_from('<I',bytes.fromhex(grid['beforeHeader16Hex']),12)[0]
            if flag not in (0,1,2):
                unsupported.append({'nodes':nodes,'flag':flag,'reason':'Unverified grid flag'});continue
            coefficients,mode,curves,groups=prepare(item['initializedArguments'],args.experimental_axis_geometry)
            if args.wide_selector_margin:curves['selectorMargin']=.25
            n=nodes**3;native=struct.unpack('<'+str(n*3)+'d',bytes.fromhex(grid['initializedOutputFloat64Hex']))
            if not all(math.isfinite(v) for v in native):
                unsupported.append({'source':case['source'],'nodes':nodes,'reason':'Native output contains non-finite components'})
                continue
            computed=[0.]*(n*3);failures=[];maximum=0.;mismatches=0
            unsafe_case=None
            for r in range(nodes):
                if unsafe_case:break
                for g in range(nodes):
                    if unsafe_case:break
                    for b in range(nodes):
                        try:
                            actual=flagged_point((r,g,b),coefficients,mode,curves,groups,nodes,flag)
                        except ValueError as error:
                            unsafe_case={'source':case['source'],'nodes':nodes,'mode':mode,
                                         'rgbIndex':[r,g,b],'reason':str(error)}
                            break
                        index=(r*nodes+g)*nodes+b
                        for c in range(3):computed[c*n+index]=actual[c]
                        expected=[native[c*n+index] for c in range(3)]
                        error=max(abs(a-b) for a,b in zip(actual,expected));maximum=max(maximum,error)
                        if error>1e-10:
                            mismatches+=1
                            if len(failures)<12:failures.append({'rgbIndex':[r,g,b],'reference':actual,'native':expected,'error':error})
            if unsafe_case:
                unsupported.append(unsafe_case);continue
            pack={10:pack10,17:pack17}.get(nodes)
            rows.append({'model':case['model'],'source':case['source'],'nodes':nodes,'flag':flag,'mode':mode,'maxError':maximum,'mismatchedNodes':mismatches,'passed':not mismatches,
                         'packingApplicable':pack is not None,
                         'packingExact':[pack(computed,a)==pack(native,a) for a in (False,True)] if pack else [],'firstMismatches':failures})
    result={'cameraAccess':False,'rows':rows,'unsupported':unsupported}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    if not rows or unsupported or not all(r['passed'] and all(r['packingExact']) for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
