"""Experimental flexible NP3 colour-look conversion, using local profile data.

No Nikon DLL is executed or distributed. A validated local coefficient file is
required. This converts a colour look on encoded sRGB; RAW development and
sharpening are excluded. It does not reproduce Nikon camera RAW processing.
"""
from concurrent.futures import CancelledError
from nikon_np3 import decode
from nikon_profile_data import load_conversion_profile
from .prepare import prepare_grid
from .pipeline import grid_point


def compile_cube(data,profile_path,size=33,progress=None,cancel=None):
    if not isinstance(size,int) or size not in (17,33,65):
        raise ValueError('Expected NP3 conversion grid size 17, 33 or 65')
    style=decode(data)
    if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
    parameters=prepare_grid(style,load_conversion_profile(profile_path))
    if progress is not None:progress(0)
    values=[]
    for blue in range(size):
        for green in range(size):
            if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
            for red in range(size):
                values.extend(value/65280 for value in grid_point([red,green,blue],size,1,0,parameters))
        if progress is not None:progress(round((blue+1)*100/size))
    return dict(title=style.name,size=size,domain_min=[0.0]*3,domain_max=[1.0]*3,
        values=values,source='np3',color_space='RGB',bit_depth=16,lossy=True,
        conversion_note='Experimental Nikon colour look; excludes Nikon RAW development and sharpening')
