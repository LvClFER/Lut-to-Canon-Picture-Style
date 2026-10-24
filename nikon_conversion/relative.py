"""Express a device-input look relative to its neutral colour transform."""
from concurrent.futures import CancelledError
import numpy as np


def sample_grid(grid,points):
    size=grid.shape[0]
    positions=np.clip(points,0,1)*(size-1)
    lower=np.minimum(positions.astype(int),size-2)
    fraction=positions-lower
    result=np.zeros_like(points)
    for blue in (0,1):
        for green in (0,1):
            for red in (0,1):
                weight=np.prod(np.where((red,green,blue),fraction,1-fraction),axis=-1)
                result+=grid[lower[...,2]+blue,lower[...,1]+green,lower[...,0]+red]*weight[...,None]
    return result


def relative_coordinates(neutral,neutral_size,size,cancel=None,progress=None):
    base=np.asarray(neutral,dtype=float).reshape(neutral_size,neutral_size,neutral_size,3)
    if not np.isfinite(base).all():
        raise ValueError('Non-finite NP3 colour grid')
    blue,green,red=np.meshgrid(*([np.linspace(0,1,size)]*3),indexing='ij')
    target=np.stack((red,green,blue),axis=-1)
    current=target.copy();best=current.copy()
    best_error=np.full(target.shape[:-1],np.inf)
    for iteration in range(20):
        if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
        error=sample_grid(base,current)-target
        magnitude=np.sum(error*error,axis=-1)
        improved=magnitude<best_error
        best[improved]=current[improved];best_error[improved]=magnitude[improved]
        jacobian=np.stack([(sample_grid(base,current+np.eye(3)[c]*.002)-
            sample_grid(base,current-np.eye(3)[c]*.002))/.004 for c in range(3)],axis=-1)
        # Clipped neutral colours are not invertible; use a bounded least-squares step.
        transpose=np.swapaxes(jacobian,-1,-2)
        delta=np.linalg.solve(transpose@jacobian+np.eye(3)*.001,
            transpose@error[...,None])[...,0]
        current=np.clip(current-np.clip(delta,-.1,.1)*.8,0,1)
        if progress is not None:progress(iteration+1)
    return np.rint(best*4095).astype(int)
