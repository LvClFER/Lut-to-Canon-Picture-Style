"""Preparation from observed flexible NP3 and coefficient profile."""
from .style_controls import compile_style_controls,basic_saturation_adjustment
from .profile_parameters import (flexible_colour_bases,profile_gamut_parameters,
    profile_chroma_parameters,profile_base_rows,profile_intensity_parameters,
    flexible_intensity_curves,flexible_special_intensity_curve,profile_luma_curve,
    profile_target_parameters,flexible_neutral_rotation,SRGB_D50_XYZ)
from .grid import grid_rotation_tables
from nikon_np3 import NP3Style


def neutral_style(style):
    records={tag:b'\x80\x01' for tag in range(0x1900,0x1f00,0x100)}
    records.update({0x300:style.block(0x300),0xb00:b'\xff\x04',
        0x1f00:bytes([128]*24+[1,1,1,0]),
        0x2000:bytes.fromhex('80008080'*3+'01010100b2018001')})
    return NP3Style('Neutral flexible colour',tuple(records.items()))


def prepare_grid(style,profile):
    if style.block(0x300)!=b'\x00\x20' or style.block(0xb00)!=b'\xff\x04':
        raise ValueError('Only observed flexible base with neutral basic hue is supported')
    parameters=compile_style_controls(style,flexible_colour_bases(profile))
    for fields in (profile_gamut_parameters(profile,14),profile_chroma_parameters(profile,14),
            profile_base_rows(profile,14),profile_target_parameters(profile),flexible_neutral_rotation(profile)):
        parameters.update(fields)
    intensity=profile_intensity_parameters(profile,0)
    curves=flexible_intensity_curves(profile)
    curves[2]=flexible_special_intensity_curve(profile,basic_saturation_adjustment(style.color_values[5]))
    curves.update(zip((9,10),intensity['toneIntensityCurves']))
    parameters.update(intensityCoefficients=intensity['intensityCoefficients'],
        intensityCurves=[curves[i] for i in range(12)],lumaCurve=profile_luma_curve(profile,14),
        rotationTables=grid_rotation_tables(),xyzMatrix=SRGB_D50_XYZ)
    return parameters
