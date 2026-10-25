"""Observed integer RAW-recipe primitives; offline references, not a renderer."""


def _trunc_q12(value):
    return value//4096 if value>=0 else -((-value)//4096)


def scale_channel_q10(value, percent, coefficient, maximum):
    """Observed positive channel gain: truncate percentage, then Q10 gain, then cap."""
    for number, upper in ((value, 131070), (percent, 200), (coefficient, 8192), (maximum, 65535)):
        if type(number) is not int or not 0 <= number <= upper:
            raise ValueError('Require bounded positive channel-gain inputs')
    return min(maximum, (value * percent // 100) * coefficient // 1024)


def chroma_from_rgb16(rgb):
    if len(rgb)!=3 or any(type(v) is not int or not 0<=v<=65535 for v in rgb):
        raise ValueError('Require three unsigned RGB16 values')
    red,green,blue=rgb
    return [_trunc_q12(2048*blue-1356*green-691*red),
            _trunc_q12(2048*red-333*blue-1714*green)]


def rgb16_from_ycbcr(luma, chroma):
    """Final observed conversion, including RGB16 clipping."""
    if type(luma) is not int or not 0<=luma<=65535 or len(chroma)!=2 or any(
            type(v) is not int or not -32768<=v<=32767 for v in chroma):
        raise ValueError('Require unsigned 16-bit luma and signed 16-bit chroma')
    cb,cr=chroma
    values=(luma*4096+cr*5742-cb*2+2048,
            luma*4098-cr*2925-cb*1412+2048,
            luma*4095+cb*7254+2048)
    return [max(0,min(65535,_trunc_q12(v))) for v in values]


def sample_tone64(values, coordinate):
    """Observed step-64 interpolation; output retains six fractional bits."""
    if type(coordinate) is not int or not 0<=coordinate<131072:
        raise ValueError('Require a bounded unsigned tone coordinate')
    if len(values)!=2048 or any(type(v) is not int or not 0<=v<=1023 for v in values):
        raise ValueError('Require 2048 unsigned 10-bit tone values')
    lower=coordinate//64
    upper=min((coordinate+63)//64,2047)
    fraction=coordinate%64
    return values[lower]*(64-fraction)+values[upper]*fraction
