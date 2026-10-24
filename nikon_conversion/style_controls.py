"""Compile observed flexible-colour controls; shared bases remain explicit inputs."""
from .grading import grading_vector,grading_ramps,grading_curves,expand_curve65,round_divide
from .mixer import mixer_accumulate,mixer_finalize
from .tone import custom_tone_curve,expand_tone_curve
from .global_controls import highlights_shadows_curve,white_black_curve,saturation_matrix,contrast_select,contrast_expand


def basic_saturation_adjustment(saturation):
    if not isinstance(saturation,int) or not -100<=saturation<=100:
        raise ValueError('Expected integer global saturation from -100 to 100')
    return max(-12,min(12,round_divide(saturation*24,100)))


def compile_style_controls(style,bases):
    if style.block(0x300)!=b'\x00\x20':
        raise ValueError('Only the observed flexible-colour base has been calibrated')
    values=style.color_values
    if len(values)!=41:
        raise ValueError('Expected complete flexible colour controls')
    if any(not -100<=v<=100 for v in values[:30]) or not 0<=values[39]<=100 or not -100<=values[40]<=100:
        raise ValueError('Flexible colour control outside calibrated range')
    if any(not 0<=values[i]<360 or not 0<=values[i+1]<=100 or not -100<=values[i+2]<=100 for i in (30,33,36)):
        raise ValueError('Grading control outside calibrated range')
    hue=bases['gradingHue'];ramps=bases['gradingRamps']
    vectors=[grading_vector(*values[i:i+3],hue['values'],hue['lightnessScale']) for i in (30,33,36)]
    lightness,colour=grading_ramps(vectors,values[39],values[40],ramps['values'])
    input_curves=[expand_curve65(row) for row in grading_curves(lightness,colour,ramps['gain'])]
    mixer=bases['mixer']
    h,s,l=mixer_accumulate(values[6:30],mixer)
    colour_rows=[row[:32] for row in mixer_finalize(h,s,l,bases['mixerNeutral'],mixer['quarter'])]
    record=style.block(2)
    if record is not None:
        tone=custom_tone_curve(record)
    else:
        _,high,shadow,white,black,_=values[:6]
        hs=highlights_shadows_curve(round_divide(high*120,100),round_divide(shadow*120,100),bases['tone'])
        wb=white_black_curve(white,black,bases['whiteBlack'])
        tone=[min(4095,max(0,a+b-min(4095,i*16))) for i,(a,b) in enumerate(zip(hs,wb))]
    saturation=bases['globalSaturation']
    matrix=saturation_matrix(values[5],saturation['strength'],saturation['base'])
    contrast=bases['globalContrast']
    native_contrast=0 if record is not None else round_divide(values[0]*256,100)
    selected,weights=contrast_select(native_contrast,6,contrast['baseFirst'],contrast['baseSecond'],
        contrast['brightnessFirst'],contrast['brightnessSecond'])
    contrast_curves=[contrast_expand(selected[i],selected[i+1],*weights) for i in (0,2)]
    return dict(inputCurves=input_curves,colourRows=colour_rows,tone=expand_tone_curve(tone),inputMatrix=matrix,
                contrastCurves=contrast_curves)
