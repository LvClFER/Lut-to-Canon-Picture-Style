"""Independent six-axis processing for verified default sector geometry."""
import argparse
import json
import math
import struct
from pathlib import Path
from .axis_composition_reference import compose


def cone_hue(rgb):
    """Preserve native sector arithmetic at discontinuous transition endpoints."""
    r,g,b = rgb
    maximum,minimum = max(rgb),min(rgb)
    delta = maximum-minimum
    if not delta: return 0.
    rd,gd,bd = [(maximum-v)/delta for v in rgb]
    if maximum == r: hue=bd-gd
    elif maximum == g: hue=(rd+2)-bd
    else: hue=(gd+4)-rd
    return hue+6 if hue<0 else hue


def sector_weights(hue, softness=20):
    hue %= 6
    centre = math.floor(hue+.5)
    local = hue-centre
    centre %= 6
    weights = [0.]*6
    if not math.isfinite(softness) or softness < 0:
        raise ValueError('Invalid transition width')
    width = min(softness/60,.5)
    neighbor = None
    if local > .5-width:
        position = (.5-local+width)/(2*width)
        neighbor = (centre+1)%6
    elif local < -.5+width:
        position = (local+.5+width)/(2*width)
        neighbor = (centre-1)%6
    else:
        weights[centre] = 1.
        return weights
    logistic = 1/(1+math.exp(-12*(position-.5)))
    current = position+(logistic-position)/6
    weights[centre] = current
    weights[neighbor] = 1-current
    return weights


def adjustments(groups, softness=20):
    if len(groups) != 6: raise ValueError('Need six initialized groups')
    result = []
    for index, raw in enumerate(groups):
        words = struct.unpack('<21i',raw)
        centre = index*60
        expected = [5,0,centre,50,50,1,(centre-30)%360,0,0,2,(centre+30)%360,100,100,3,
                    words[14],words[15],words[16],5,softness,0,0]
        if list(words) != expected:
            raise ValueError('Nondefault sector geometry is not independently validated')
        result.append(words[14:17])
    return result


def transform(rgb, values, softness=20, *, allow_fixed_point_overshoot=False):
    if len(values) != 6 or any(len(row)!=3 for row in values):
        raise ValueError('Require six triplets')
    hue = cone_hue(rgb)
    weights = sector_weights(hue,softness)
    maximum,minimum = max(rgb),min(rgb)
    cone_saturation = (maximum-minimum)/((maximum+minimum) if (maximum+minimum)*.5>=.5 else (2-maximum)-minimum)
    hue += sum(w*(row[0]/60) for w,row in zip(weights,values))
    saturation_amount = sum(w*(row[1]/100) for w,row in zip(weights,values))
    sat = saturation_amount*(cone_saturation if saturation_amount > 0 else 1)
    light = sum(w*(row[2]/100) for w,row in zip(weights,values))*cone_saturation
    return compose(rgb,hue,sat,light,allow_fixed_point_overshoot=allow_fixed_point_overshoot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    source = json.loads(args.probe.read_text(encoding='utf-8'))
    groups = {}
    for row in source['helperCalls']:
        group = groups.setdefault(row['name'],{})
        raw = bytes.fromhex(row['currentGroupHex'])
        if len(raw)!=84:raise ValueError('Require a complete initialized five-point axis group')
        centre=struct.unpack_from('<i',raw,8)[0]
        if row.get('centre',centre)!=centre:raise ValueError('Recorded centre differs from initialized group')
        previous = group.setdefault(centre,raw)
        if raw != previous: raise ValueError('Parameters changed during a case')
    softness = {}
    values = {}
    for name,group in groups.items():
        widths = {struct.unpack('<21i',raw)[18] for raw in group.values()}
        if len(widths) != 1: raise ValueError('Unequal sector softness is not validated')
        softness[name] = widths.pop()
        values[name] = adjustments([group[i*60] for i in range(6)],softness[name])
    checks = []
    for row in source['rows']:
        expected = transform(row['rgb'],values[row['name']],softness[row['name']])
        error = max(abs(a-b) for a,b in zip(expected,row['output']))
        checks.append({'name':row['name'],'rgb':row['rgb'],'maxError':error,'passed':error<=1e-14})
    result = {'cameraAccess':False,'usesNativeIntermediateWeights':False,
              'scope':'default six-sector geometry only','checks':checks,
              'passed':sum(r['passed'] for r in checks)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(checks),'passed':result['passed'],'maxError':max(r['maxError'] for r in checks)}))
    if not checks or result['passed']!=len(checks):raise SystemExit(1)


if __name__ == '__main__': main()
