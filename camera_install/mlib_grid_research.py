"""Direct isolated converter probe; verifies ABI against recorded stock compilation."""
import argparse
import hashlib
import json
import os
import copy
import struct
import threading
from pathlib import Path
from .compiler_regression import cipher_tables
from .virtual_compatibility import LOAD_COMPILER


def legacy_curve_vectors(cases):
    """Synthetic initialized inputs, explicitly not PF3 field acceptance tests."""
    identity=struct.pack('<25i',2,0,0,255,255,*([0]*20)).hex()
    shapes={
        'mid160':[(0,0),(128,160),(255,255)],
        'mid96':[(0,0),(128,96),(255,255)],
        'uneven5':[(0,0),(30,15),(90,120),(200,180),(255,255)],
        'zigzag6':[(0,0),(40,90),(80,30),(150,200),(220,170),(255,255)],
    }
    result=[]
    for base in cases:
        result.append(base)
        for stage in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
            for name,points in shapes.items():
                item=copy.deepcopy(base)
                words=[len(points)]+[v for point in points for v in point]
                changed=struct.pack('<25i',*(words+[0]*(25-len(words)))).hex()
                item['arguments'][stage]=changed+(identity*2 if stage=='thirdCurvesHex' else changed*2)
                item['name']=f'{stage}_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
                item['expectedHex']=None
                result.append(item)
    return result


def legacy_matrix_vectors(cases):
    result=[]
    for base in cases:
        result.append(base)
        # Native channel records contain 19 coefficients plus one reserved word.
        # Exercise cross terms and the pre-curve/post-curve clamp independently.
        for name,changes in (
            ('red_gain',[(0,1.125)]),
            ('green_gain',[(21,.875)]),
            ('blue_from_red',[(40,.125)]),
            ('red_blue_cubic',[(18,.03125)]),
            ('blue_negative_cubic',[(58,-.03125)]),
            ('red_quadratic',[(3,.125)]),
        ):
            item=copy.deepcopy(base)
            words=list(struct.unpack('<60i',bytes.fromhex(item['arguments']['matrix240Hex'])))
            for index,value in changes: words[index]=round(value*65536)
            item['arguments']['matrix240Hex']=struct.pack('<60i',*words).hex()
            item['name']=f'matrix_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
            item['expectedHex']=None
            result.append(item)
    return result


def legacy_additional_vectors(cases):
    result=[]
    groups=[]
    for dh,ds,dl in ((0,0,0),(20,10,10),(-20,-10,-10)):
        words=[1,1,5,0,193,43,47,1,100,10,15,2,300,90,85,
               3,0,0,0,4,193+dh,43+ds,47+dl]
        groups.append((f'target_H{dh}_S{ds}_L{dl}',words))
    for ds,dl in ((80,80),(80,-80),(0,80)):
        words=[1,1,4,0,180,50,50,1,0,0,0,2,360,100,100,3,30,ds,dl]
        groups.append((f'strong_S{ds}_L{dl}',words))
    for base in cases:
        result.append(base)
        for name,words in groups:
            item=copy.deepcopy(base)
            raw=struct.pack('<'+str(len(words))+'i',*words)
            item['arguments']['additionalParameterBlock']={'kind':1,'count':1,'points':words[2],
                'bytes':len(raw),'initializedHex':raw.hex()}
            item['name']=f'selective_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
            item['expectedHex']=None
            result.append(item)
    return result


def legacy_axis_chain_vectors(cases):
    from .legacy_axis_reference import adjustments
    result=[]
    for base in cases:
        result.append(base)
        block=base['arguments']['axisParameterBlock']
        if block is None:continue
        adjustments(bytes.fromhex(block['initializedHex']))
        original=list(struct.unpack('<44i',bytes.fromhex(block['initializedHex'])))
        for dh,ds,dl in ((10,0,0),(0,10,0),(0,-10,0),(0,0,10),(0,0,-10),(10,10,10)):
            item=copy.deepcopy(base);words=original.copy();words[37:40]=[dh,ds,dl]
            item['arguments']['axisParameterBlock']['initializedHex']=struct.pack('<44i',*words).hex()
            item['name']=f'global_H{dh}_S{ds}_L{dl}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
            item['expectedHex']=None;result.append(item)
    return result


def legacy_pre_axis_vectors(cases,safe_curves=False):
    result=[]
    for base in cases:
        result.append(base)
        for item in legacy_additional_vectors([base])[1:]:
            if safe_curves and ('target_H-20' in item['name'] or 'strong_S80_L-80' in item['name']):continue
            block=item['arguments']['additionalParameterBlock']
            item['arguments']['oldParameterBlock']=block
            item['arguments']['additionalParameterBlock']=copy.deepcopy(base['arguments']['additionalParameterBlock'])
            item['name']='pre_axis_'+item['name']
            result.append(item)
            if safe_curves:
                changed=next(v for v in legacy_curve_vectors([item])
                             if v.get('name','').startswith('postCurvesHex_mid160_'))
                changed['name']=item['name']+'_post_mid160'
                result.append(changed)
    return result


def legacy_multiple_group_vectors(cases):
    result=[]
    for base in cases:
        result.append(base)
        selectors=legacy_additional_vectors([base])[1:]
        target0=bytes.fromhex(selectors[0]['arguments']['additionalParameterBlock']['initializedHex'])[8:]
        target1=bytes.fromhex(selectors[1]['arguments']['additionalParameterBlock']['initializedHex'])[8:]
        def four(delta):
            return struct.pack('<17i',4,0,180,50,50,1,0,0,0,2,360,100,100,3,*delta)
        first,second=four((10,10,5)),four((-10,-10,-5))
        for name,points,groups in (
            ('four_forward',4,[first,second]),('four_reverse',4,[second,first]),
            ('four_three',4,[first,second,first]),
            ('five_forward',5,[target0,target1]),('five_reverse',5,[target1,target0]),
            ('five_three',5,[target1,target0,target1]),
        ):
            item=copy.deepcopy(base)
            raw=struct.pack('<2i',1,len(groups))+b''.join(groups)
            item['arguments']['additionalParameterBlock']={'kind':1,'count':len(groups),
                'points':points,'bytes':len(raw),'initializedHex':raw.hex()}
            item['name']=f'multiple_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
            item['expectedHex']=None;result.append(item)
    return result


def legacy_gamut_policy_vectors(cases,policy=2):
    if policy not in (0,2):raise ValueError('Only explicit alternate gamut policies')
    result=[]
    for base in cases:
        result.append(base)
        for candidate in legacy_matrix_vectors([base]):
            item=copy.deepcopy(candidate)
            item['arguments']['numericArguments'][1]=policy
            item['name']=f'policy{policy}_'+(item.get('name') or f'baseline_{item["nodes"]}_mode{item["arguments"]["numericArguments"][0]}')
            item['expectedHex']=None;result.append(item)
    return result


def legacy_grid_flag_vectors(cases,nonlinear=False,nine_nodes=False):
    result=[]
    for base in cases:
        result.append(base)
        if nine_nodes:
            base=copy.deepcopy(base)
            words=list(struct.unpack('<4I',bytes.fromhex(base['headerHex'])))
            words[1]=9;base['nodes']=9;base['headerHex']=struct.pack('<4I',*words).hex()
            base.pop('name',None)
        variants=[base]
        if nonlinear:
            variants.extend(legacy_matrix_vectors([base])[1:])
            variants.extend(v for v in legacy_curve_vectors([base])[1:]
                            if '_mid160_' in v['name'])
        for candidate in variants:
          for flag in (0,1,2):
            item=copy.deepcopy(candidate)
            words=list(struct.unpack('<4I',bytes.fromhex(item['headerHex'])))
            words[3]=flag;item['headerHex']=struct.pack('<4I',*words).hex()
            label=candidate.get('name') or f'{item["nodes"]}_mode{item["arguments"]["numericArguments"][0]}'
            item['name']=f'grid_flag{flag}_{label}'
            item['expectedHex']=None;result.append(item)
    return result


def chromatic_curve_vectors(cases):
    result=[]
    for base in cases:
        result.append(base)
        original=base['arguments']['thirdCurvesHex']
        if original is None:continue  # A null pointer also bypasses the Lab stage.
        for channel in (1,2):
            for name,words in (('end230',[2,0,0,255,230]),('mid160',[3,0,0,128,160,255,255])):
                item=copy.deepcopy(base)
                changed=struct.pack('<25i',*(words+[0]*(25-len(words)))).hex()
                records=[original[i:i+200] for i in range(0,600,200)]
                records[channel]=changed
                item['arguments']['thirdCurvesHex']=''.join(records)
                item['name']=f'chromatic_slot{channel}_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
                # Hypothesis explicitly compares against the captured baseline.
                result.append(item)
    return result


def legacy_six_axis_chain_vectors(cases,raw,combined=False,interactions=False,geometry=False):
    """Inject verified canonical six-sector arguments, not camera payloads."""
    from .legacy_six_axis_reference import decode_block
    decode_block(raw)
    original=list(struct.unpack('<128i',raw))
    result=[]
    for base in cases:
        result.append(base)
        for name,values,widths in (
            ('neutral',[(0,0,0)]*6,[20]*6),
            ('red_hue',[(10,0,0)]+[(0,0,0)]*5,[20]*6),
            ('mixed',[(10,-10,10),(-10,10,-10)]*3,[20]*6),
            ('unequal',[(10,-10,10),(-10,10,-10)]*3,[0,5,10,20,30,60]),
        ):
            item=copy.deepcopy(base);words=original.copy()
            for i,value in enumerate(values):
                words[16+21*i:19+21*i]=value
                words[20+21*i]=widths[i]
            item['arguments']['axisParameterBlock']={'kind':2,'count':6,'points':5,
                'bytes':512,'initializedHex':struct.pack('<128i',*words).hex()}
            item['name']=f'six_axis_{name}_{base["nodes"]}_mode{base["arguments"]["numericArguments"][0]}'
            item['expectedHex']=None;result.append(item)
            if geometry and name=='mixed':
                for label,rotation,span,sbounds,lbounds in (
                    ('rotate15',15,30,(0,100),(0,100)),
                    ('rotate_minus15',-15,30,(0,100),(0,100)),
                    ('narrow20',0,20,(0,100),(0,100)),
                    ('wide40',0,40,(0,100),(0,100)),
                    ('saturation_gate',0,30,(20,80),(0,100)),
                    ('lightness_gate',0,30,(0,100),(20,80)),
                ):
                    changed=copy.deepcopy(item);geometry_words=words.copy()
                    for i in range(6):
                        centre=(i*60+rotation)%360
                        geometry_words[4+21*i]=centre
                        geometry_words[8+21*i:11+21*i]=[(centre-span)%360,sbounds[0],lbounds[0]]
                        geometry_words[12+21*i:15+21*i]=[(centre+span)%360,sbounds[1],lbounds[1]]
                    changed['arguments']['axisParameterBlock']['initializedHex']=struct.pack('<128i',*geometry_words).hex()
                    changed['name']=item['name']+'_geometry_'+label
                    result.append(changed)
            if combined:
                candidates=legacy_curve_vectors([item])
                # One nonlinear shape at each stage, preserving bounded scope.
                for stage in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
                    changed=next(v for v in candidates if v.get('name','').startswith(stage+'_mid160_'))
                    changed['name']=item['name']+'_'+stage+'_mid160'
                    result.append(changed)
            if interactions:
                mixed=copy.deepcopy(item)
                for stage in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
                    candidates=legacy_curve_vectors([mixed])
                    mixed=next(v for v in candidates if v.get('name','').startswith(stage+'_mid160_'))
                matrices=legacy_matrix_vectors([mixed])
                mixed=next(v for v in matrices if v.get('name','').startswith('matrix_red_gain_'))
                selectors=legacy_additional_vectors([mixed])
                for prefix in ('selective_strong_S80_L80_','selective_target_H20_S10_L10_'):
                    changed=next(v for v in selectors if v.get('name','').startswith(prefix))
                    changed['name']=item['name']+'_all_stages_'+prefix.rstrip('_')
                    result.append(changed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('dll', 'trace', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--basis', action='store_true', help='Probe the 19-term polynomial basis instead of compact grids')
    parser.add_argument('--curves', action='store_true', help='Probe cached curve evaluation using captured finalized curves')
    parser.add_argument('--lab', action='store_true', help='Probe fixed-point RGB/Lab helpers in the isolated host')
    parser.add_argument('--axes', action='store_true', help='Probe captured six-group parameter blocks against synthetic RGB')
    parser.add_argument('--axes-dense', action='store_true', help='Include sector boundary colors and negative/strong synthetic adjustments')
    parser.add_argument('--integer-tetrahedral', action='store_true', help='Probe Canon fixed-point tetrahedral interpolation offline')
    parser.add_argument('--modern-replay', action='store_true', help='Replay initialized modern conversion arguments in an isolated host')
    parser.add_argument('--legacy-replay', action='store_true', help='Replay the captured preceding conversion branch offline')
    parser.add_argument('--legacy-curve-vectors', action='store_true', help='With legacy replay, inject bounded synthetic curves into initialized arguments')
    parser.add_argument('--legacy-matrix-vectors', action='store_true', help='With legacy replay, inject bounded synthetic matrix coefficients')
    parser.add_argument('--legacy-additional-vectors', action='store_true', help='With legacy replay, inject four/five-point selective-color groups')
    parser.add_argument('--legacy-axis-chain-vectors', action='store_true', help='With legacy replay, inject nonneutral global two-group axis adjustments')
    parser.add_argument('--legacy-pre-axis-vectors', action='store_true', help='With legacy replay, inject selective color before post-RGB curves')
    parser.add_argument('--legacy-pre-axis-safe-curves', action='store_true', help='Use safe pre-axis vectors plus nonlinear post curves, excluding the two known unsafe patterns')
    parser.add_argument('--legacy-multiple-group-vectors',action='store_true',help='With legacy replay, test sequential two/three selective groups and reversed ordering')
    parser.add_argument('--legacy-gamut-policy-vectors',action='store_true',help='With legacy replay, test polynomial gamut policy2 and matrix perturbations')
    parser.add_argument('--modern-gamut-policy-vectors',action='store_true',help='With modern replay, test the shared polynomial gamut policy2 correction')
    parser.add_argument('--gamut-policy-zero',action='store_true',help='With gamut replay vectors, test policy0 bypass instead of policy2 correction')
    parser.add_argument('--legacy-grid-flag-vectors',action='store_true',help='With preceding replay, test grid header flags0/1/2')
    parser.add_argument('--legacy-grid-flag-nonlinear',action='store_true',help='Combine grid flags with polynomial and nonlinear curve perturbations')
    parser.add_argument('--legacy-grid-nine',action='store_true',help='Explicit synthetic nine-node geometry; does not claim camera payload packing')
    parser.add_argument('--legacy-six-axis-chain-vectors', action='store_true', help='With legacy replay, inject canonical six-sector axes and unequal widths')
    parser.add_argument('--legacy-six-axis-combined', action='store_true', help='Also combine six-sector arguments with nonlinear curves at each stage')
    parser.add_argument('--legacy-six-axis-interactions', action='store_true', help='Also combine all curves, matrix and strong/target selective color with six-sector axes')
    parser.add_argument('--legacy-six-axis-geometry-chain', action='store_true', help='Also probe nondefault six-sector bounds in complete initialized chains')
    parser.add_argument('--chromatic-curve-vectors', action='store_true', help='With replay, test whether luminance-record chromatic slots affect output')
    parser.add_argument('--legacy-sectors', action='store_true', help='Measure bounded captured legacy selective-color groups offline')
    parser.add_argument('--legacy-sector-vectors', action='store_true', help='With legacy sectors, include strong synthetic gamut adjustments')
    parser.add_argument('--legacy-target-vectors', action='store_true', help='With legacy sectors, include five-point target-color groups')
    parser.add_argument('--legacy-target-nodes', action='store_true', help='With target vectors, test 9/10/17/33 quantization and an unsupported node count')
    parser.add_argument('--legacy-axis-vectors', action='store_true', help='With legacy sectors, measure captured two-group kind2 axes and bounded adjustments')
    parser.add_argument('--legacy-six-axis-vectors', action='store_true', help='With legacy sectors, compare six-axis blocks through the preceding helper')
    parser.add_argument('--legacy-axis-dense', action='store_true', help='With legacy sectors, add deterministic random RGB and exact transition neighborhoods')
    parser.add_argument('--legacy-axis-widths', action='store_true', help='With preceding six-axis vectors, also test widths0/5/10/30/60')
    parser.add_argument('--legacy-axis-unequal', action='store_true', help='With preceding six-axis vectors, test unequal neighboring transition widths')
    parser.add_argument('--legacy-axis-geometry', action='store_true', help='Probe nondefault six-sector hue and saturation/lightness bounds separately')
    parser.add_argument('--legacy-sector-case', help='With legacy sectors, select one exact case name to bound instrumented batches')
    parser.add_argument('--observe-negative-curves',action='store_true',help='Read-only observation of cached curve indices in replay; retain events if native test fails')
    parser.add_argument('--curve-negative-subsample',action='store_true',help='With cached curves, test bounded negative inputs whose truncated index is zero')
    parser.add_argument('--gamut',action='store_true',help='Probe bounded polynomial gamut policy2 correction in the isolated host')
    parser.add_argument('--dispatch',action='store_true',help='Read only verified compiler binding slots in the own isolated host')
    args = parser.parse_args()
    if (args.legacy_grid_flag_nonlinear or args.legacy_grid_nine) and not args.legacy_grid_flag_vectors:
        parser.error('Grid refinements require --legacy-grid-flag-vectors')
    if (args.legacy_sector_vectors or args.legacy_target_vectors or args.legacy_axis_vectors or args.legacy_six_axis_vectors) and not args.legacy_sectors:
        parser.error('Selective synthetic vectors require --legacy-sectors')
    if args.legacy_target_nodes and not args.legacy_target_vectors:
        parser.error('--legacy-target-nodes requires --legacy-target-vectors')
    if args.legacy_axis_dense and not args.legacy_sectors:
        parser.error('--legacy-axis-dense requires --legacy-sectors')
    if (args.legacy_axis_widths or args.legacy_axis_unequal or args.legacy_axis_geometry) and not args.legacy_six_axis_vectors:
        parser.error('Width vectors require --legacy-six-axis-vectors')
    if sum((args.legacy_axis_vectors,args.legacy_six_axis_vectors,args.legacy_sector_vectors,args.legacy_target_vectors))>1:
        parser.error('Select one synthetic selector family to isolate effects')
    initialized_vectors=(args.legacy_curve_vectors,args.legacy_matrix_vectors,args.legacy_additional_vectors,args.legacy_axis_chain_vectors,args.legacy_six_axis_chain_vectors,args.legacy_pre_axis_vectors,args.legacy_multiple_group_vectors,args.legacy_gamut_policy_vectors,args.legacy_grid_flag_vectors)
    if args.modern_gamut_policy_vectors and (not args.modern_replay or any(initialized_vectors)):
        parser.error('Modern gamut vectors require --modern-replay without legacy vectors')
    if args.gamut_policy_zero and not (args.modern_gamut_policy_vectors or args.legacy_gamut_policy_vectors):
        parser.error('--gamut-policy-zero requires gamut replay vectors')
    if args.legacy_pre_axis_safe_curves and not args.legacy_pre_axis_vectors:
        parser.error('--legacy-pre-axis-safe-curves requires --legacy-pre-axis-vectors')
    if args.curve_negative_subsample and not args.curves:parser.error('--curve-negative-subsample requires --curves')
    if args.legacy_sector_case and not args.legacy_sectors:
        parser.error('--legacy-sector-case requires --legacy-sectors')
    if (args.legacy_six_axis_combined or args.legacy_six_axis_interactions or args.legacy_six_axis_geometry_chain) and not args.legacy_six_axis_chain_vectors:
        parser.error('--legacy-six-axis-combined requires --legacy-six-axis-chain-vectors')
    if any(initialized_vectors) and not args.legacy_replay:
        parser.error('Legacy synthetic vectors require --legacy-replay')
    if sum(initialized_vectors)>1:
        parser.error('Select one initialized vector family to isolate effects')
    if args.chromatic_curve_vectors and (any(initialized_vectors) or not (args.modern_replay or args.legacy_replay)):
        parser.error('Chromatic vectors require a replay without other synthetic vectors')
    cipher_tables(args.dll)
    dll = args.dll.resolve()
    mlib = dll.parent / 'MLib.dll'
    if hashlib.sha256(mlib.read_bytes()).hexdigest() != 'a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a':
        raise ValueError('Unknown MLib revision')
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    special = args.integer_tetrahedral or args.modern_replay or args.legacy_replay or args.legacy_sectors or args.gamut or args.dispatch
    if sum((args.basis, args.curves, args.lab, args.axes,args.integer_tetrahedral,args.modern_replay,args.legacy_replay,args.legacy_sectors,args.gamut,args.dispatch)) > 1: raise ValueError('Select only one math probe')
    capture = None
    if not args.curves and not args.lab and not args.axes and not special:
        capture = next(item for item in trace['files'][0]['mlibCalls']['captures']
                       if item['functionRva'] == '0x196a0' and item['converterOption'] == 1)
    import frida
    device = frida.get_local_device()
    host = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    pid = device.spawn([str(host), '-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', 'Start-Sleep -Seconds 3600'])
    session, scripts = None, []
    observations=[]
    watchdog=None
    try:
        session = device.attach(pid)
        loader = session.create_script(LOAD_COMPILER); scripts.append(loader); loader.load()
        device.resume(pid); loader.exports_sync.load(str(dll))
        source = Path(__file__).with_name('mlib_grid_probe.js').read_text(encoding='utf-8')
        probe = session.create_script(source); scripts.append(probe)
        def observe(message,data):
            observations.append(message)
            if args.gamut and message.get('type')=='send':
                args.output.with_suffix('.progress.json').write_text(json.dumps(message,indent=2),encoding='utf-8')
        probe.on('message',observe)
        probe.load()
        if args.dispatch:
            result=probe.exports_sync.dispatch()
        elif args.legacy_sectors:
            import struct
            unique={}
            for row in trace['files']:
                for item in row['mlibCalls']['captures']:
                    if item['functionRva']!='0x14bd0': continue
                    block=item['initializedArguments']['additionalParameterBlock']
                    if block is None:continue
                    if block['kind']!=1 or block['points']!=4: raise ValueError('Only captured four-point legacy groups')
                    raw=bytes.fromhex(block['initializedHex']);stride=68
                    if len(raw)!=8+block['count']*stride: raise ValueError('Invalid legacy block size')
                    for index in range(block['count']):
                        group=raw[8+index*stride:8+(index+1)*stride]
                        unique.setdefault(group.hex(),{'name':f'mode{item["initializedArguments"]["numericArguments"][0]}_group{index}',
                                         'parametersHex':(struct.pack('<2I',1,1)+group).hex()})
            if not unique: raise ValueError('No verified legacy groups')
            if args.legacy_six_axis_vectors:
                from .default_axis_reference import adjustments
                captured=next(item['initializedArguments']['sixAxes512Hex'] for row in trace['files']
                    for item in row['mlibCalls']['captures'] if item['functionRva']=='0x11220')
                raw=bytes.fromhex(captured)
                adjustments([raw[8+i*84:8+(i+1)*84] for i in range(6)],20)
                original=list(struct.unpack('<128i',raw));unique={}
                vectors=[('baseline',[(0,0,0)]*6),('red_hue',[(10,0,0)]+[(0,0,0)]*5),
                         ('red_sat',[(0,10,0)]+[(0,0,0)]*5),('red_light',[(0,0,10)]+[(0,0,0)]*5),
                         ('all_axes',[(10,10,10)]*6),('mixed',[(10,-10,10),(-10,10,-10)]*3)]
                for name,values in vectors:
                    words=original.copy()
                    for i,value in enumerate(values):words[16+21*i:19+21*i]=value
                    raw=struct.pack('<128i',*words).hex()
                    unique[raw]={'name':f'preceding_six_{name}','parametersHex':raw}
                if args.legacy_axis_geometry:
                    for label,rotation,span,sbounds,lbounds in (
                        ('rotate15',15,30,(0,100),(0,100)),
                        ('rotate_minus15',-15,30,(0,100),(0,100)),
                        ('narrow20',0,20,(0,100),(0,100)),
                        ('wide40',0,40,(0,100),(0,100)),
                        ('saturation20_80',0,30,(20,80),(0,100)),
                        ('lightness20_80',0,30,(0,100),(20,80)),
                    ):
                        words=original.copy()
                        for i in range(6):
                            centre=(i*60+rotation)%360
                            words[4+21*i]=centre
                            words[8+21*i:11+21*i]=[(centre-span)%360,sbounds[0],lbounds[0]]
                            words[12+21*i:15+21*i]=[(centre+span)%360,sbounds[1],lbounds[1]]
                            words[16+21*i:19+21*i]=[(10,-10,10),(-10,10,-10)][i%2]
                        raw=struct.pack('<128i',*words).hex()
                        unique[raw]={'name':'geometry_'+label,'parametersHex':raw}
            if args.legacy_axis_vectors:
                captured=next(item['initializedArguments']['axisParameterBlock'] for row in trace['files']
                    for item in row['mlibCalls']['captures'] if item['functionRva']=='0x14bd0'
                    and item['initializedArguments']['axisParameterBlock'] is not None)
                if (captured['kind'],captured['count'],captured['points'])!=(2,2,5):
                    raise ValueError('Require captured two-group axis layout')
                original=list(struct.unpack('<44i',bytes.fromhex(captured['initializedHex'])))
                unique={}
                for dh,ds,dl in ((0,0,0),(10,0,0),(0,10,0),(0,-10,0),(0,0,10),(0,0,-10),(10,10,10)):
                    words=original.copy()
                    words[37:40]=[dh,ds,dl]
                    raw=struct.pack('<44i',*words).hex()
                    unique[raw]={'name':f'legacy_axis_H{dh}_S{ds}_L{dl}','parametersHex':raw}
            if args.legacy_sector_vectors:
                vectors=[(30,ds,dl) for ds,dl in ((80,0),(0,80),(0,-80),(80,80),(80,-80),(-80,80),
                              (-80,-80),(20,10),(20,-10),(0,0))]
                vectors.extend(((180,80,0),(-180,-80,10),(180,0,0),(-180,0,0)))
                for dh,ds,dl in vectors:
                    words=[1,1,4,0,180,50,50,1,0,0,0,2,360,100,100,3,dh,ds,dl]
                    raw=struct.pack('<19i',*words).hex()
                    unique[raw]={'name':f'synthetic_H{dh}_S{ds}_L{dl}','parametersHex':raw}
            if args.legacy_target_vectors:
                for h,s,l in ((180,50,50),(200,50,50),(180,60,50),(180,50,60),
                              (200,60,60),(160,40,40)):
                    words=[1,1,5,0,180,50,50,1,0,0,0,2,360,100,100,3,0,0,0,4,h,s,l]
                    raw=struct.pack('<23i',*words).hex()
                    unique[raw]={'name':f'synthetic_target_H{h}_S{s}_L{l}','parametersHex':raw}
                for dh,ds,dl in ((0,0,0),(20,10,10),(-20,-10,-10)):
                    words=[1,1,5,0,193,43,47,1,100,10,15,2,300,90,85,
                           3,0,0,0,4,193+dh,43+ds,47+dl]
                    raw=struct.pack('<23i',*words).hex()
                    unique[raw]={'name':f'nonaligned_target_H{dh}_S{ds}_L{dl}','parametersHex':raw}
            sector_cases=list(unique.values())
            if args.legacy_axis_widths:
                for case in list(sector_cases):
                    if case['name'] not in ('preceding_six_red_hue','preceding_six_mixed'):continue
                    for softness in (0,5,10,30,60):
                        words=list(struct.unpack('<128i',bytes.fromhex(case['parametersHex'])))
                        for i in range(6):words[20+21*i]=softness
                        sector_cases.append(dict(case,name=case['name']+f'_width{softness}',
                            softness=softness,parametersHex=struct.pack('<128i',*words).hex()))
            if args.legacy_axis_unequal:
                patterns=((0,5,10,20,30,60),(60,30,20,10,5,0),(0,30,0,30,0,30),(5,60,5,60,5,60))
                for case in list(sector_cases):
                    if case['name'] not in ('preceding_six_red_hue','preceding_six_mixed'):continue
                    for index,widths in enumerate(patterns):
                        words=list(struct.unpack('<128i',bytes.fromhex(case['parametersHex'])))
                        for i,width in enumerate(widths):words[20+21*i]=width
                        sector_cases.append(dict(case,name=case['name']+f'_unequal{index}',
                            softness=list(widths),parametersHex=struct.pack('<128i',*words).hex()))
            if args.legacy_target_nodes:
                sector_cases=[dict(case,name=case['name']+f'_nodes{nodes}',nodes=nodes)
                    for case in sector_cases for nodes in ((9,10,17,33,25) if len(case['parametersHex'])==184 else (33,))]
            if args.legacy_sector_case:
                sector_cases=[case for case in sector_cases if case['name']==args.legacy_sector_case]
                if not sector_cases:raise ValueError('No matching legacy sector case')
            result=probe.exports_sync.legacySectors(sector_cases,args.legacy_axis_dense)
        elif args.modern_replay or args.legacy_replay:
            cases = []
            for row in trace['files']:
                for item in row['mlibCalls']['captures']:
                    if item['functionRva'] != ('0x14bd0' if args.legacy_replay else '0x11220'): continue
                    grid = next(g for g in item['gridArguments'] if g.get('initializedOutputFloat64Hex'))
                    cases.append({'arguments':item['initializedArguments'],'nodes':grid['nodes'],
                                  'model':row.get('model'),'source':row['source'],
                                  'headerHex':grid['beforeHeader16Hex'],'expectedHex':grid['initializedOutputFloat64Hex']})
            if not cases: raise ValueError('No complete modern replay captures')
            if args.legacy_curve_vectors: cases=legacy_curve_vectors(cases)
            if args.legacy_matrix_vectors: cases=legacy_matrix_vectors(cases)
            if args.legacy_additional_vectors: cases=legacy_additional_vectors(cases)
            if args.legacy_pre_axis_vectors:cases=legacy_pre_axis_vectors(cases,args.legacy_pre_axis_safe_curves)
            if args.legacy_multiple_group_vectors:cases=legacy_multiple_group_vectors(cases)
            if args.legacy_gamut_policy_vectors:cases=legacy_gamut_policy_vectors(cases,0 if args.gamut_policy_zero else 2)
            if args.modern_gamut_policy_vectors:cases=legacy_gamut_policy_vectors(cases,0 if args.gamut_policy_zero else 2)
            if args.legacy_grid_flag_vectors:cases=legacy_grid_flag_vectors(cases,args.legacy_grid_flag_nonlinear,args.legacy_grid_nine)
            if args.legacy_axis_chain_vectors: cases=legacy_axis_chain_vectors(cases)
            if args.legacy_six_axis_chain_vectors:
                raw=next(bytes.fromhex(item['initializedArguments']['sixAxes512Hex'])
                    for row in trace['files'] for item in row['mlibCalls']['captures']
                    if item['functionRva']=='0x11220')
                cases=legacy_six_axis_chain_vectors(cases,raw,args.legacy_six_axis_combined,args.legacy_six_axis_interactions,args.legacy_six_axis_geometry_chain)
            if args.chromatic_curve_vectors: cases=chromatic_curve_vectors(cases)
            result = probe.exports_sync.modernReplay(cases,args.legacy_replay,args.observe_negative_curves)
            if any(initialized_vectors) or args.modern_gamut_policy_vectors:
                result['syntheticInitializedArguments']=True
                result['files']=[{'source':item.get('name') or 'captured-baseline',
                    'model':item.get('model') or 'isolated-function-vector','originSource':item.get('source'),
                    'mlibCalls':{'captures':[{'functionRva':'0x14bd0' if args.legacy_replay else '0x11220','initializedArguments':item['arguments'],
                    'gridArguments':[{'nodes':item['nodes'],'beforeHeader16Hex':item['headerHex'],
                    'initializedOutputFloat64Hex':row['outputDenseFloat64Hex']}]}]}}
                    for item,row in zip(cases,result['rows'])]
        elif args.gamut:
            watchdog=threading.Timer(15,lambda:device.kill(pid))
            watchdog.daemon=True;watchdog.start()
            result=probe.exports_sync.gamut()
        elif args.integer_tetrahedral:
            result = probe.exports_sync.integer_tetrahedral()
        elif args.axes:
            baseline = next(x['parameters512Hex'] for x in trace['baseline']['mlibCalls']['captures'] if x['functionRva'] == '0xfa40')
            cases = [{'name':'baseline','parametersHex':baseline}]
            for row in trace['experiments']:
                changed = next(x['parameters512Hex'] for x in row['mlibCalls']['captures'] if x['functionRva'] == '0xfa40' and x['parameters512Hex'] != baseline)
                cases.append({'name':row['name'],'parametersHex':changed})
            result = probe.exports_sync.axes(cases,args.axes_dense)
        elif args.lab:
            result = probe.exports_sync.lab()
        elif args.curves:
            unique = {}
            for row in trace['files']:
                for item in row['mlibCalls']['captures']:
                    if item['functionRva'] == '0x1df30' and item.get('finalizedPairsFloat64Hex'):
                        unique[(item['domainSize'], item['finalizedPairsFloat64Hex'])] = {
                            'domainSize': item['domainSize'], 'pairsHex': item['finalizedPairsFloat64Hex']}
            if not unique: raise ValueError('No finalized curve captures')
            result = probe.exports_sync.curves(list(unique.values()),args.curve_negative_subsample)
        else:
            result = probe.exports_sync.basis() if args.basis else probe.exports_sync.run(capture['sourceDenseFloat64Hex'])
        if Path(result['mlibPath']).resolve() != mlib:
            raise ValueError('Loaded MLib differs from verified path')
        if not args.basis and not args.curves and not args.lab and not args.axes and not special:
            baseline = next(row for row in result['rows'] if row['name'] == 'captured' and row['option'] == 1 and row['flag'] == 1)
            result['directCallMatchesStockByteForByte'] = baseline['outputDenseFloat64Hex'] == capture['outputDenseFloat64Hex']
        result.update(dllSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                      probeSha256=hashlib.sha256(source.encode()).hexdigest())
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        if (args.modern_replay or args.legacy_replay) and not all(r['stockExact'] is not False for r in result['rows']):
            raise ValueError('Modern replay differs from stock capture; see retained output')
        if not args.basis and not args.curves and not args.lab and not args.axes and not special and not result['directCallMatchesStockByteForByte']:
            raise ValueError('Direct-call ABI/baseline is not validated')
        print(json.dumps({'cases': len(result['rows']), 'stockExact': result.get('directCallMatchesStockByteForByte'),
                          'basisOnly': args.basis, 'curvesOnly': args.curves}))
    except Exception as error:
        if args.observe_negative_curves or args.gamut:
            args.output.write_text(json.dumps({'cameraAccess':False,'probeFailed':True,
                'error':str(error),'observations':observations},indent=2),encoding='utf-8')
        raise
    finally:
        if watchdog is not None:watchdog.cancel()
        for script in reversed(scripts):
            try: script.unload()
            except Exception: pass
        if session is not None:
            try: session.detach()
            except Exception: pass
        try: device.kill(pid)
        except Exception: pass


if __name__ == '__main__':
    main()
