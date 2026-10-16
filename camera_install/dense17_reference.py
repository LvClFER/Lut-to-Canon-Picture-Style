"""Independent null-curve33-to17 flag2 conversion; offline research only."""
import numpy as np
from .compact_grid_reference import trilinear


def convert17(source):
    # MLib196a0: coordinate domain256, last coordinate255.75/256.
    axis = np.minimum(np.arange(17, dtype=np.float64) / 16, .9990234375)
    coordinates = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1)
    rgb = np.clip(trilinear(source, coordinates) * 256, 0, 255.75)
    return np.moveaxis(rgb, -1, 0)
