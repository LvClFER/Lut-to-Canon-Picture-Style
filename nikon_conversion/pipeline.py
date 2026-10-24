"""Verified colour-grid point arithmetic."""
from .grid import (grid_input,grid_matrix,grid_hue_position,grid_colour_coefficients,
    grid_base_coefficients,grid_intensity_indices,grid_response_gains,grid_remaining_response,
    grid_apply_colour,grid_rotation_matrix,grid_post_colour,grid_contrast,grid_tone_matrix,grid_gamut,grid_encode,grid_rgb)


def grid_point(coordinates,size,flags,mode,p,unclipped_rgb=False):
    """Return native encoded values, or extended RGB for relative-look construction."""
    values=grid_input(coordinates,size,p['inputCurves'])
    values=grid_matrix(values,p['inputMatrix'],p['margin'])
    luma,x,y=values
    _,lower,upper,fraction=grid_hue_position(x,y)
    creative=grid_colour_coefficients(lower,upper,fraction,p['colourRows'])
    base=grid_base_coefficients(lower,upper,fraction,p['baseRows'])
    indices=grid_intensity_indices(luma,[x,y],p['intensityCoefficients'])
    lookups=[curve[index] for curve,index in zip(p['intensityCurves'],indices)]
    gains=grid_response_gains(base[:6],lookups[:7])
    extra=grid_remaining_response(base[6:],lookups[7:],p['lumaCurve'][luma],p['rotationTables'])
    values=grid_apply_colour(luma,[x,y],creative,gains[1],extra[3],[extra[2],gains[0],gains[2]])
    values=grid_rotation_matrix(values[1:],extra[:2],p['mappedLuma'][values[0]],p['mix'],p['target'],p['rotationMatrix'],p['rotationOffsets'])
    luma=values[0]
    indexed=grid_post_colour(luma,values[1:],p['chromaGain'][luma],p['hueCurve'])
    contrast=grid_contrast([luma]+indexed[1:],[curve[indexed[0]] for curve in p['contrastCurves']])
    ranges=grid_tone_matrix(contrast,p['tone'],p['toneMatrix'],p['toneOffsets'])
    values=grid_gamut(ranges,[p['tone'][contrast[0]]]+contrast[1:],p['gamutControls'],p['gamutHigh'],p['gamutLow'])
    if unclipped_rgb:return [value*65280 for value in grid_rgb(values)]
    return grid_encode(values,flags,mode,p['xyzMatrix'])
