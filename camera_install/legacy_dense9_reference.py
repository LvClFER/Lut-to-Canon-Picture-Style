"""Offline dense PF3 to observed nine-node flag0; no Canon calls or transport.

Applies only to the direct dense-source subclass, not the preceding legacy
curve/matrix MLIBcalcLuckyEx branch. Twelve retained source vectors and seven
own synthetic grids have exact native comparisons; arbitrary inputs remain
outside that empirical coverage.
"""
import numpy as np
from .accepted_modern_reference import dense_source
from .compact_grid_reference import trilinear


def dense9_flag0(record):
    source = dense_source(record)
    first = np.minimum(np.arange(9), 6) * 40 / 255
    second = np.minimum(np.arange(9) * 40 / 255, 1)
    a = trilinear(source, np.stack(np.meshgrid(first, first, first, indexing='ij'), axis=-1))
    b = trilinear(source, np.stack(np.meshgrid(second, second, second, indexing='ij'), axis=-1))
    boundary = np.any(np.indices((9, 9, 9)) >= 7, axis=0)
    values = np.where(boundary[..., None], (b*8-a*5.2)/2.8, b)*255
    return np.moveaxis(np.trunc(np.clip(values, 0, 320)), -1, 0)
