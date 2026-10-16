"""Validate sampled stage math and report actual call ordering, research only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from .color_trace_validation import validate as validate_color
from .lab_math_reference import rgb_to_lab, lab_to_rgb
from .polynomial_color_reference import transform


def validate(trace):
    checks, routes = [], []
    for row in trace['files']:
        if 'error' in row:
            routes.append({'model':row['model'],'error':row['error']})
            continue
        phases = {}
        for item in row['mlibCalls']['captures']:
            phase = item.get('phase')
            if phase is None: continue
            group = phases.setdefault(phase, {'phase':phase,'sampledOrder':[], 'curveCaches':{}})
            rva = item['functionRva']
            if len(group['sampledOrder']) < 48:
                group['sampledOrder'].append({'functionRva':rva,'callerRva':item.get('callerRva'),
                                             'callIndex':item.get('callIndex')})
            if rva in ('0xf070','0xee40'):
                function = rgb_to_lab if rva == '0xf070' else lab_to_rgb
                expected = function(item['input'],item['bits'],item['mode'])
                checks.append({'model':row['model'],'phase':phase,'kind':'lab','functionRva':rva,
                    'bits':item['bits'],'mode':item['mode'],'passed':expected == item['output'],
                    'maxError':max(abs(a-b) for a,b in zip(expected,item['output']))})
            elif rva == '0x1d380':
                coefficients = struct.unpack('<57d',bytes.fromhex(item['coefficientsFloat64Hex']))
                expected = transform(item['input'],coefficients)
                error = max(abs(a-b) for a,b in zip(expected,item['output']))
                checks.append({'model':row['model'],'phase':phase,'kind':'polynomial',
                               'maxError':error,'passed':error <= 1e-14})
            elif rva == '0x1dd50':
                raw = bytes.fromhex(item['pairsHex'])
                if len(raw) != item['domainSize']*16:
                    raise ValueError('Invalid initialized curve cache length')
                key = item['callerRva']
                cache = group['curveCaches'].setdefault(key, {'domainSize':item['domainSize'],'hashes':[]})
                digest = hashlib.sha256(raw).hexdigest()
                if digest not in cache['hashes']: cache['hashes'].append(digest)
        routes.append({'model':row['model'],'payloadSize':row['payloadSize'],
                       'phases':list(phases.values())})
    color = validate_color(trace)
    return {'cameraAcceptanceEstablished':False,'sampledOrderIsNotFullInstructionTrace':True,
            'curveInputsOutputsNotCaptured':True,'routes':routes,'checks':checks,
            'passed':sum(item['passed'] for item in checks),
            'colorCases':len(color['checks']),'colorPassed':color['passed']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = validate(json.loads(args.trace.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'routes':len(result['routes']),'stageCases':len(result['checks']),
        'stagePassed':result['passed'],'colorCases':result['colorCases'],'colorPassed':result['colorPassed'],
        'maxStageError':max((x['maxError'] for x in result['checks']),default=None)}))


if __name__ == '__main__': main()
