"""Bounded independent 47f60 floating sampler for observed 17-node grids.

Research reference only; not a camera transport or full PF3 compiler.
"""
import math


def sample17(values, rgb):
    if len(values) != 17 ** 3 * 3 or len(rgb) != 3:
        raise ValueError('Require planar17 RGB grid and one RGB coordinate')
    if any(not math.isfinite(v) or not 0 <= v <= 256 for v in rgb):
        raise ValueError('Unobserved coordinate domain')
    step = 16.0
    cells, fractions = [], []
    for value in rgb:
        cell = math.trunc(value / step)
        fraction = value - cell * step
        # Native last cell spans240..255, then extends to256.
        if cell == 15 and fraction > 0:
            value = fraction / (step - 1) + value
            cell = math.trunc(value / step)
            fraction = value - cell * step
        cells.append(min(16, max(0, cell)))
        fractions.append(fraction)
    order = sorted(range(3), key=lambda axis: fractions[axis], reverse=True)
    vertices = [cells.copy()]
    for axis in order:
        vertex = vertices[-1].copy()
        vertex[axis] = min(16, vertex[axis] + 1)
        vertices.append(vertex)
    a, b, c = [fractions[axis] for axis in order]
    weights = (step - a, a - b, b - c, c)
    result = []
    for channel in range(3):
        samples = [values[channel * 4913 + (v[0] * 17 + v[1]) * 17 + v[2]] for v in vertices]
        if any(not math.isfinite(v) for v in samples):
            raise ValueError('Nonfinite sampled grid value')
        result.append(sum(v * w for v, w in zip(samples, weights)) / step)
    return result
