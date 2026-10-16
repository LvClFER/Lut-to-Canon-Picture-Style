"""Independent post-weight six-axis composition; sector weights remain separate."""
import argparse
import colorsys
import json
import math
from pathlib import Path


def compose(rgb, adjusted_hue, saturation_adjustment, lightness_adjustment, *, allow_fixed_point_overshoot=False):
    # The modern 24-bit roundtrip can overshoot by a few hundred integer
    # units. It enters the existing cone compression, not channel clipping.
    upper = 1.001 if allow_fixed_point_overshoot else 1
    if len(rgb) != 3 or not all(math.isfinite(v) and 0 <= v <= upper for v in rgb):
        raise ValueError('Require bounded finite RGB')
    if not all(math.isfinite(v) for v in (adjusted_hue,saturation_adjustment,lightness_adjustment)):
        raise ValueError('Nonfinite adjustment')
    maximum, minimum = max(rgb), min(rgb)
    lightness = (maximum+minimum)*.5
    # Canon uses a double-cone coordinate, not conventional HSL saturation.
    saturation = (maximum-minimum)/((maximum+minimum) if lightness>=.5 else (2-maximum)-minimum)
    gain = saturation_adjustment*(5 if saturation_adjustment > 0 else 1)
    saturation *= max(0,1+gain)
    lightness *= max(0,1+lightness_adjustment)
    boundary = (lightness/(1-lightness) if lightness < .5 else
                (1-lightness)/lightness) if lightness else 0
    if saturation > 1 or lightness > 1 or saturation > boundary:
        distance = abs(lightness-.5)
        if distance:
            root = math.sqrt(saturation*saturation+12*saturation*distance+4*distance*distance)
            adjusted = (root-(2*distance+saturation))/(4*distance)
            if adjusted <= 0:
                adjusted = (-saturation-2*distance-root)/(4*distance)
            saturation = adjusted
            ratio = saturation/(saturation+1)
            lightness = ratio if lightness < .5 else 1-ratio
        elif lightness == 0:
            saturation = 0
        else:
            saturation = boundary
    saturation = min(1,max(0,saturation)); lightness = min(1,max(0,lightness))
    high = lightness+(1+abs(2*lightness-1))*saturation*.5
    low = 2*lightness-high
    h = adjusted_hue % 6
    sector = int(h); fraction = h-sector
    up = high-(high-low)*(1-fraction); down = high-(high-low)*fraction
    return ((high,up,low),(down,high,low),(low,high,up),
            (low,down,high),(up,low,high),(high,low,down))[sector]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    source = json.loads(args.probe.read_text(encoding='utf-8'))
    weights = {}
    for row in source['helperCalls']:
        weights.setdefault((row['name'],tuple(row['rgb'])),[]).append(row['adjustments'])
    checks = []
    for row in source['rows']:
        original_hue = colorsys.rgb_to_hls(*row['rgb'])[0]*6
        # The dense grid repeats exact primaries. Do not sum two identical
        # six-sector evaluations just because their RGB keys coincide.
        groups = weights[(row['name'],tuple(row['rgb']))][:6]
        hue = original_hue+sum((a[0]-original_hue+3)%6-3 for a in groups)
        sat = sum(a[2] for a in groups); light = sum(a[3] for a in groups)
        expected = compose(row['rgb'],hue,sat,light)
        error = max(abs(a-b) for a,b in zip(expected,row['output']))
        checks.append({'name':row['name'],'rgb':row['rgb'],'maxError':error,'passed':error<=1e-14})
    result = {'cameraAccess':False,'sectorWeightsIndependentlyReproduced':False,
              'checks':checks,'passed':sum(r['passed'] for r in checks)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(checks),'passed':result['passed'],'maxError':max(r['maxError'] for r in checks)}))


if __name__ == '__main__': main()
