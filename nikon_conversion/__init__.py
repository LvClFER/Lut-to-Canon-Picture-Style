"""Experimental flexible NP3 colour-look conversion, using local profile data.

No Nikon DLL is executed or distributed. A validated local coefficient file is
required. Device-input colour transforms are normalized against neutral
Flexible Color before use on developed RGB. RAW development and sharpening
are excluded. It does not reproduce Nikon camera RAW processing.
"""
from concurrent.futures import CancelledError
from nikon_np3 import decode
from nikon_profile_data import load_conversion_profile
from .prepare import prepare_grid,neutral_style
from .pipeline import grid_point
from .relative import relative_coordinates

CONVERSION_VERSION='relative-flexible-v3'


def compile_cube(data,profile_path,size=33,progress=None,cancel=None):
    if not isinstance(size,int) or size not in (17,33,65):
        raise ValueError('Expected NP3 conversion grid size 17, 33 or 65')
    style=decode(data)
    if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
    profile=load_conversion_profile(profile_path)
    parameters=prepare_grid(style,profile)
    neutral=prepare_grid(neutral_style(style),profile)
    if progress is not None:progress(0)
    # The coarse neutral grid only seeds inversion; final colours use the full arithmetic.
    neutral_size=17;neutral_values=[]
    for blue in range(neutral_size):
        for green in range(neutral_size):
            if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
            for red in range(neutral_size):
                neutral_values.extend(value/65280 for value in grid_point([red,green,blue],neutral_size,1,0,neutral))
        if progress is not None:progress(round((blue+1)*20/neutral_size))
    coordinates=relative_coordinates(neutral_values,neutral_size,size,cancel,
        (lambda step:progress(20+step)) if progress is not None else None)
    values=[]
    for blue in range(size):
        for green in range(size):
            if cancel is not None and cancel():raise CancelledError('NP3 conversion cancelled')
            for red in range(size):
                point=coordinates[blue,green,red].tolist()
                look=grid_point(point,4096,1,0,parameters)
                base=grid_point(point,4096,1,0,neutral)
                # A clipped device colour has no exact inverse; retain the unmatched RGB residual.
                values.extend(min(1,max(0,target/(size-1)+(a-b)/65280))
                    for target,a,b in zip((red,green,blue),look,base))
        if progress is not None:progress(40+round((blue+1)*60/size))
    return dict(title=style.name,size=size,domain_min=[0.0]*3,domain_max=[1.0]*3,
        values=values,source='np3',color_space='RGB',bit_depth=16,lossy=True,
        conversion_version=CONVERSION_VERSION,
        conversion_note='Experimental relative Nikon colour look; excludes Nikon RAW development and sharpening')
