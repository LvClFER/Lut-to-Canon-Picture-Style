"""Observed MLib fixed-point RGB/Lab helpers, not camera transport code."""
import argparse
import json
import math
from pathlib import Path
from .color_math_reference import forward_color, inverse_color


def _validate(values, bits):
    if bits not in (8, 12, 16, 24) or len(values) != 3 or any(type(v) is not int for v in values):
        raise ValueError('Require three integer components and a tested bit depth')


def rgb_to_lab(rgb, bits, mode):
    _validate(rgb, bits)
    maximum = 2**bits-1
    # Modern full33 passes 2**bits at unit-valued endpoints, while the
    # helper still normalizes by 2**bits-1. Preserve that observed boundary.
    # A repeated 24-bit RGB/Lab roundtrip can add one integer unit at an endpoint.
    upper = maximum+2 if bits == 24 else maximum
    if any(v < 0 or v > upper for v in rgb):
        raise ValueError('RGB outside unsigned input domain')
    x, y, z = forward_color([v/maximum for v in rgb], 1 if mode == 1 else 2)
    def f(value):
        return value**(1/3) if value > .008856 else 7.787*value + 16/116
    lightness = 116*y**(1/3)-16 if y > .008856 else 903.29*y
    return [math.trunc(lightness*65536), math.trunc(500*(f(x/.9505)-f(y))*65536),
            math.trunc(200*(f(y)-f(z/1.089))*65536)]


def lab_to_rgb(lab, bits, mode):
    _validate(lab, bits)
    lightness, a, b = [v/65536 for v in lab]
    fy = (lightness+16)/116 if lightness > 7.99953624 else lightness*7.787/903.29+16/116
    def f_inverse(value):
        cube = value**3
        return cube if cube > .008856 else (value-16/116)/7.787
    xyz = [f_inverse(fy+a/500)*.9505, f_inverse(fy), f_inverse(fy-b/200)*1.089]
    rgb, _ = inverse_color(xyz, 1 if mode == 1 else 2)
    return [math.trunc(v*(2**bits-1)+.5) for v in rgb]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    for row in json.loads(args.probe.read_text(encoding='utf-8'))['rows']:
        forward = rgb_to_lab(row['rgb'], row['bits'], row['mode'])
        inverse = lab_to_rgb(row['lab'], row['bits'], row['mode'])
        checks.append({**row, 'forwardReference': forward, 'inverseReference': inverse,
                       'forwardExact': forward == row['lab'], 'inverseExact': inverse == row['inverse']})
    result = {'cameraAccess': False, 'checks': checks,
              'forwardPassed': sum(r['forwardExact'] for r in checks),
              'inversePassed': sum(r['inverseExact'] for r in checks)}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'checks'}))


if __name__ == '__main__':
    main()
