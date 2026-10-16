"""Bounded own-host replay of compact pixels and synthetic selector splits."""
import argparse
import copy
import hashlib
import json
import os
import struct
import threading
from pathlib import Path
from .compact_pixel_reference import prepare,point
from .virtual_compatibility import LOAD_COMPILER


def vectors(captures):
    result=[];seen=set()
    inputs=[[r/3,g/3,b/3] for r in range(4) for g in range(4) for b in range(4)]
    seed=0x13579bdf
    for _ in range(128):
        rgb=[]
        for c in range(3):
            seed=(seed*1664525+1013904223)&0xffffffff;rgb.append(seed/0xffffffff)
        inputs.append(rgb)
    def add(name,a,samples):
        prepare(a)
        result.append(dict(name=name,arguments=a,inputs=samples))
    for capture in captures:
        if capture['functionRva']!='0x1cab0':continue
        a=capture['initializedArguments'];key=json.dumps(a,sort_keys=True)
        if key in seen:continue
        seen.add(key);mode=a['mode']
        add(f'captured_mode{mode}',copy.deepcopy(a),[s['input'] for s in capture['samples'][:32]])
        add(f'grid_mode{mode}',copy.deepcopy(a),inputs)
        for stage in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
            b=copy.deepcopy(a);b[stage]=None
            add(f'null_{stage}_mode{mode}',b,inputs)
        nonlinear=(struct.pack('<25i',3,0,0,128,160,255,255,*([0]*18))*3).hex()
        for stage in ('preCurvesHex','postCurvesHex','thirdCurvesHex'):
            b=copy.deepcopy(a)
            b[stage]=nonlinear if stage!='thirdCurvesHex' else nonlinear[:200]+a[stage][200:]
            add(f'nonlinear_{stage}_mode{mode}',b,inputs)
        b=copy.deepcopy(a);b['axisBlock']=None
        add(f'null_axes_mode{mode}',b,inputs)
        if a['axisBlock']:
            for width in (0,5,10,30):
                b=copy.deepcopy(a);axis=list(struct.unpack('<128i',bytes.fromhex(b['axisBlock']['initializedHex'])))
                for c in range(6):axis[20+21*c]=width
                axis[16:19]=[5,2,1];b['axisBlock']['initializedHex']=struct.pack('<128i',*axis).hex()
                add(f'axes_width{width}_mode{mode}',b,inputs)
        for name,index,value in [('cross_red_blue',2,4096),('blue_cubic',58,2048)]:
            b=copy.deepcopy(a);words=list(struct.unpack('<60i',bytes.fromhex(b['matrix240Hex'])))
            words[index]=value;b['matrix240Hex']=struct.pack('<60i',*words).hex()
            add(f'matrix_{name}_mode{mode}',b,inputs)
        for split in (0,1):
            b=copy.deepcopy(a);words=[1,1,5,0,180,50,50,1,0,0,0,2,360,100,100,3,0,0,0,4,193,43,47]
            raw=struct.pack('<'+str(len(words))+'i',*words)
            b['selectorBlock']=dict(kind=1,count=1,points=5,bytes=len(raw),initializedHex=raw.hex());b['splitCount']=split
            add(f'target_split{split}_mode{mode}',b,inputs)
        for count in (1,2,3,12):
            groups=[]
            for i in range(count):groups.extend([4,0,180,50,50,1,0,0,0,2,360,100,100,3,5 if i==0 else -3,2,1])
            raw=struct.pack('<'+str(len(groups)+2)+'i',1,count,*groups)
            for split in range(count+1):
                b=copy.deepcopy(a);b['selectorBlock']=dict(kind=1,count=count,points=4,bytes=len(raw),initializedHex=raw.hex());b['splitCount']=split
                add(f'groups{count}_split{split}_mode{mode}',b,inputs)
                if count==2:
                    b=copy.deepcopy(b);b['preCurvesHex']=nonlinear;b['postCurvesHex']=nonlinear
                    b['thirdCurvesHex']=nonlinear[:200]+a['thirdCurvesHex'][200:]
                    matrix=list(struct.unpack('<60i',bytes.fromhex(b['matrix240Hex'])))
                    matrix[58]=2048;b['matrix240Hex']=struct.pack('<60i',*matrix).hex()
                    if b['axisBlock']:
                        axis=list(struct.unpack('<128i',bytes.fromhex(b['axisBlock']['initializedHex'])))
                        axis[16:19]=[5,2,1];b['axisBlock']['initializedHex']=struct.pack('<128i',*axis).hex()
                    add(f'combined_split{split}_mode{mode}',b,inputs)
    if not result:raise ValueError('No initialized compact pixel captures')
    return result


def preflight(cases):
    references={};unsupported=[];safe_cases=[]
    for case in cases:
        settings=prepare(case['arguments']);safe=copy.deepcopy(case);safe['inputs']=[]
        for rgb in case['inputs']:
            try:reference=point(rgb,settings)
            except ValueError as error:
                unsupported.append(dict(name=case['name'],input=rgb,reason=str(error),nativeCallSkipped=True));continue
            references[(case['name'],tuple(rgb))]=reference;safe['inputs'].append(rgb)
        if safe['inputs']:safe_cases.append(safe)
    return safe_cases,references,unsupported


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--selector-margin',type=float,default=.05,help='Explicit bounded reference domain, at most.25; does not change native arguments')
    args=parser.parse_args()
    expected='7ec553fe47352c7d24e83299aee9f8031a38e150d47ca33c9fb02c8fa1c5b3f0'
    if hashlib.sha256(args.dll.read_bytes()).hexdigest()!=expected:raise ValueError('Unverified compiler revision')
    if hashlib.sha256((args.dll.parent/'MLib.dll').read_bytes()).hexdigest()!='a36f3cea5ea5776cb542282ccf832abf9a0952eeb4d284db329a1463cd4a922a':
        raise ValueError('Unverified MLib revision')
    source=json.loads(args.trace.read_text(encoding='utf-8'))
    cases=vectors(source['baseline']['mlibCalls']['captures'])
    for case in cases:
        case['arguments']['researchSelectorMargin']=args.selector_margin;prepare(case['arguments'])
    # Reject unverified curve indices before native execution. Earlier raw
    # reports remain negative evidence, not a portable memory-dependent oracle.
    safe_cases,references,unsupported=preflight(cases)
    if not safe_cases:
        args.output.write_text(json.dumps(dict(cameraAccess=False,compilerPatched=False,nativePreflightGuard=True,
            cases=cases,rows=[],passed=0,unsupported=unsupported),indent=2),encoding='utf-8')
        raise SystemExit(1)
    import frida
    device=frida.get_local_device();host=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    pid=device.spawn([str(host),'-NoLogo','-NoProfile','-WindowStyle','Hidden','-Command','Start-Sleep -Seconds 3600'])
    session=None;loader=None;script=None
    watchdog=threading.Timer(45,lambda:device.kill(pid));watchdog.daemon=True;watchdog.start()
    try:
        session=device.attach(pid);loader=session.create_script(LOAD_COMPILER);loader.load();device.resume(pid);loader.exports_sync.load(str(args.dll.resolve()))
        script=session.create_script(Path(__file__).with_name('compact_pixel_probe.js').read_text(encoding='utf-8'));script.load()
        result=script.exports_sync.run(safe_cases)
        failures=[];maximum=0.;passed=0
        for row in result['rows']:
            reference=references[(row['name'],tuple(row['input']))]
            error=max(abs(a-b) for a,b in zip(reference,row['output']))
            maximum=max(maximum,float(error));passed+=int(error<=1e-12)
            if error>1e-12 and len(failures)<20:failures.append(dict(row,reference=reference,error=error))
        report=dict(result,cases=cases,passed=passed,maxError=maximum,firstMismatches=failures,unsupported=unsupported,compilerPatched=False,
                    nativePreflightGuard=True,requestedSamples=sum(len(c['inputs']) for c in cases))
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(cases=len(cases),samples=len(result['rows']),passed=passed,unsupported=len(unsupported),maxError=maximum)))
        if not result['rows'] or unsupported or passed!=len(result['rows']):raise SystemExit(1)
    finally:
        watchdog.cancel()
        for item in (script,loader):
            if item:
                try:item.unload()
                except Exception:pass
        if session:
            try:session.detach()
            except Exception:pass
        try:device.kill(pid)
        except Exception:pass


if __name__=='__main__':main()
