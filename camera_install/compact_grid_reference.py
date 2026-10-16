"""Independent research reference for observed 10-node null-curve paths.

Not a camera payload builder. Only observed null-curve 10-node paths.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def trilinear(source, coordinates):
    source = np.asarray(source, dtype=np.float64)
    coordinates = np.asarray(coordinates, dtype=np.float64)
    if source.shape != (33, 33, 33, 3) or coordinates.shape[-1:] != (3,):
        raise ValueError('Expected 33^3 RGB source and XYZ coordinates')
    if not np.isfinite(source).all() or not np.isfinite(coordinates).all():
        raise ValueError('Non-finite grid')
    position = np.clip(coordinates, 0, 1) * 32
    lower = np.minimum(position.astype(np.int64), 31)
    fraction = position - lower
    output = np.zeros(coordinates.shape, dtype=np.float64)
    for x in (0, 1):
        for y in (0, 1):
            for z in (0, 1):
                weight = ((fraction[..., 0] if x else 1 - fraction[..., 0]) *
                          (fraction[..., 1] if y else 1 - fraction[..., 1]) *
                          (fraction[..., 2] if z else 1 - fraction[..., 2]))
                output += source[lower[..., 0] + x, lower[..., 1] + y,
                                 lower[..., 2] + z] * weight[..., None]
    return output


def compact_flag2(source):
    axis = np.minimum(np.arange(10) * 32 / 255, 1)
    coordinates = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1)
    sampled = trilinear(source, coordinates) * 255
    return np.moveaxis(sampled, -1, 0)


def compact_flag1(source):
    # Boundary branch samples two points along a diagonal, not independent
    # extrapolation along each axis. For 10 nodes: 224 -> 255 -> 256.
    first = np.minimum(np.arange(10), 7) * 32 / 255
    second = np.minimum(np.arange(10) * 32 / 255, 1)
    a = trilinear(source, np.stack(np.meshgrid(first, first, first, indexing='ij'), axis=-1))
    b = trilinear(source, np.stack(np.meshgrid(second, second, second, indexing='ij'), axis=-1))
    return np.moveaxis(np.clip((a + (b-a) * (32/31)) * 255, 0, 288), -1, 0)


def compact_flag0(source):
    # The integer route has distinct boundary constants: 1.1 and 30.9,
    # not the floating route's 1 and 31. Interior samples are truncated.
    first = np.minimum(np.arange(10), 7)*32/255
    second = np.minimum(np.arange(10)*32/255, 1)
    a = trilinear(source, np.stack(np.meshgrid(first,first,first,indexing='ij'),axis=-1))
    b = trilinear(source, np.stack(np.meshgrid(second,second,second,indexing='ij'),axis=-1))
    boundary = np.any(np.indices((10,10,10)) >= 8, axis=0)
    values = np.where(boundary[...,None], (b*32-a*1.1)/30.9, b)*255
    return np.moveaxis(np.trunc(np.clip(values,0,288)), -1, 0)


def synthetic(name):
    coordinates = np.stack(np.meshgrid(*([np.arange(33)/32] * 3), indexing='ij'), axis=-1)
    if name == 'identity': return coordinates
    if name == 'constant': return np.broadcast_to([.2, .4, .8], coordinates.shape).copy()
    if name == 'rGain':
        coordinates[..., 0] *= .75
        return coordinates
    if name == 'rbSwap': return coordinates[..., [2, 1, 0]]
    if name == 'product':
        r, g, b = np.moveaxis(coordinates, -1, 0)
        return np.stack([r*g, g*b, b*r], axis=-1)
    if name == 'square': return coordinates ** 2
    r, g, b = np.indices((33,33,33))
    if name == 'impulse':
        return np.stack([(r==16)&(g==16)&(b==16), (r==28)&(g==31)&(b==7),
                         (r==32)&(g==32)&(b==32)], axis=-1).astype(float)
    if name == 'scrambled':
        return np.stack([((r*17+g*31+b*13)%97)/96, ((r*7+g*11+b*29)%83)/82,
                         ((r*19+g*5+b*23)%71)/70], axis=-1)
    raise ValueError('Unknown synthetic case')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('probe', 'trace', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    probe = json.loads(args.probe.read_text(encoding='utf-8'))
    trace = json.loads(args.trace.read_text(encoding='utf-8'))
    capture = next(item for item in trace['files'][0]['mlibCalls']['captures']
                   if item['functionRva'] == '0x196a0' and item['converterOption'] == 1)
    captured = np.frombuffer(bytes.fromhex(capture['sourceDenseFloat64Hex']), dtype='<f8').reshape(33,33,33,3)
    checks = []
    for row in probe['rows']:
        source = captured if row['name'] == 'captured' else synthetic(row['name'])
        expected = {0:compact_flag0,1:compact_flag1,2:compact_flag2}[row['flag']](source)
        actual = np.frombuffer(bytes.fromhex(row['outputDenseFloat64Hex']), dtype='<f8').reshape(3,10,10,10)
        error = float(np.max(np.abs(expected - actual)))
        checks.append({'name': row['name'], 'option': row['option'], 'flag': row['flag'], 'values': actual.size,
                       'maxError': error, 'passed': error <= 1e-10})
    result = {'cameraAccess': False, 'scope': '10-node flags 0/1/2, null curves only',
              'checks': checks, 'passed': sum(check['passed'] for check in checks)}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(checks), 'passed': result['passed'],
                      'maxError': max(check['maxError'] for check in checks)}))


if __name__ == '__main__':
    main()
