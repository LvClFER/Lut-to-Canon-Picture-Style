"""Observed integer RAW-recipe primitives; offline references, not a renderer."""

from bisect import bisect_right
from math import isfinite
import struct


def decode_model_tone_record(data, mode, normalize_ranges):
    """Observed bounded big-endian model record to the padded native descriptor."""
    if not isinstance(data, (bytes, bytearray, memoryview)) or len(data) < 6:
        raise ValueError('Require a complete model tone header')
    if type(mode) is not int or not 0 <= mode <= 65535 or type(normalize_ranges) is not bool:
        raise ValueError('Require an unsigned mode and boolean range normalization')
    count, version, active = struct.unpack_from('>3H', data)
    if not 2 <= active <= count <= 64:
        raise ValueError('Require bounded model tone point counts')
    consumed = 2*(3+2*count+6+max(0, version-9))
    if len(data) < consumed:
        raise ValueError('Truncated model tone record')
    knots = list(struct.unpack_from('>'+str(count)+'H', data, 6))
    values = list(struct.unpack_from('>'+str(count)+'H', data, 6+2*count))
    limits = list(struct.unpack_from('>6H', data, 6+4*count))
    limits[4] = mode
    if limits[0] == 4095:
        knots = [(v*16383//4095)&65535 for v in knots]
        values = [(v*16383//4095)&65535 for v in values]
        limits[5] = (limits[5]*4)&65535
    elif limits[2] == 16383 and normalize_ranges:
        limits[0] = limits[2] = 4095
    descriptor = bytearray(274)
    struct.pack_into('<3H', descriptor, 0, count, version, active)
    struct.pack_into('<'+str(count)+'H', descriptor, 6, *knots)
    struct.pack_into('<'+str(count)+'H', descriptor, 134, *values)
    struct.pack_into('<6H', descriptor, 262, *limits)
    return bytes(descriptor), consumed


def spline_second_derivatives(knots, values, left_slope=None, right_slope=None):
    """Observed tridiagonal spline solver; None selects a natural endpoint."""
    if not 2 <= len(knots) <= 65535 or len(values) != len(knots):
        raise ValueError('Require matching spline arrays with at least two knots')
    numbers = (*knots, *values, *(s for s in (left_slope, right_slope) if s is not None))
    if any(type(v) not in (int, float) or not isfinite(v) for v in numbers):
        raise ValueError('Require finite spline numbers')
    if any(left >= right for left, right in zip(knots, knots[1:])):
        raise ValueError('Require strictly increasing spline knots')
    second = [0.0]*len(knots)
    work = [0.0]*len(knots)
    if left_slope is not None and left_slope <= 9.9e29:
        width = knots[1]-knots[0]
        second[0] = -0.5
        work[0] = (3/width)*((values[1]-values[0])/width-left_slope)
    for i in range(1, len(knots)-1):
        width = knots[i+1]-knots[i-1]
        ratio = (knots[i]-knots[i-1])/width
        pivot = ratio*second[i-1]+2
        second[i] = (ratio-1)/pivot
        difference = (values[i+1]-values[i])/(knots[i+1]-knots[i]) - (values[i]-values[i-1])/(knots[i]-knots[i-1])
        work[i] = (6*difference/width-ratio*work[i-1])/pivot
    q = u = 0.0
    if right_slope is not None and right_slope <= 9.9e29:
        width = knots[-1]-knots[-2]
        q = 0.5
        u = (3/width)*(right_slope-(values[-1]-values[-2])/width)
    second[-1] = (u-q*work[-2])/(q*second[-2]+1)
    for i in range(len(knots)-2, -1, -1):
        second[i] = second[i]*second[i+1]+work[i]
    return second


def sample_cubic_spline(knots, values, second_derivatives, coordinate):
    """Observed spline evaluation; endpoint intervals also serve extrapolation."""
    if not 2 <= len(knots) <= 65535 or len(values) != len(knots) or len(second_derivatives) != len(knots):
        raise ValueError('Require matching spline arrays with at least two knots')
    if any(type(v) not in (int, float) or not isfinite(v)
           for array in (knots, values, second_derivatives, (coordinate,)) for v in array):
        raise ValueError('Require finite spline numbers')
    if any(left >= right for left, right in zip(knots, knots[1:])):
        raise ValueError('Require strictly increasing spline knots')
    upper = min(len(knots)-1, max(1, bisect_right(knots, coordinate)))
    lower = upper-1
    width = knots[upper]-knots[lower]
    a = (knots[upper]-coordinate)/width
    b = (coordinate-knots[lower])/width
    correction = (a*a*a-a)*second_derivatives[lower] + (b*b*b-b)*second_derivatives[upper]
    return correction*(width*width)/6 + (a*values[lower] + b*values[upper])


def build_spline_lookup(knots, values, size, maximum):
    """Observed natural spline LUT: truncate, clamp, then enforce nondecreasing output."""
    if any(type(v) is not int or not 1 <= v <= 65535 for v in (size, maximum)):
        raise ValueError('Require bounded positive LUT size and exclusive maximum')
    second = spline_second_derivatives(knots, values)
    result = []
    previous = 0
    for coordinate in range(size):
        value = int(max(0, min(maximum-1, sample_cubic_spline(knots, values, second, coordinate))))
        previous = max(previous, value)
        result.append(previous)
    return result


def densify_spline(knots, values):
    """Observed 251-budget subdivision, preserving original control points."""
    if len(knots) > 251:
        raise ValueError('Require at most 251 source knots')
    second = spline_second_derivatives(knots, values)
    subdivisions = 251//len(knots)
    dense_knots, dense_values = [], []
    for i, coordinate in enumerate(knots):
        dense_knots.append(coordinate)
        dense_values.append(values[i])
        if i == len(knots)-1:
            break
        width = knots[i+1]-coordinate
        for j in range(1, subdivisions):
            query = j*width/subdivisions+coordinate
            dense_knots.append(query)
            dense_values.append(min(values[-1], sample_cubic_spline(knots, values, second, query)))
    return dense_knots, dense_values


def _trunc_q12(value):
    return value//4096 if value>=0 else -((-value)//4096)


def scale_channel_q10(value, percent, coefficient, maximum):
    """Observed positive channel gain: truncate percentage, then Q10 gain, then cap."""
    for number, upper in ((value, 131070), (percent, 200), (coefficient, 8192), (maximum, 65535)):
        if type(number) is not int or not 0 <= number <= upper:
            raise ValueError('Require bounded positive channel-gain inputs')
    return min(maximum, (value * percent // 100) * coefficient // 1024)


def auxiliary_luma_bin(rgb, gains=None):
    """Observed scalar branches' 10-bit table index, not standard luminance."""
    if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 65535 for v in rgb):
        raise ValueError('Require three unsigned RGB16 values')
    red, green, blue = rgb
    if gains is not None:
        if len(gains) != 3 or any(type(v) is not int or not 0 <= v <= 8192 for v in gains):
            raise ValueError('Require three bounded positive Q10 gains')
        return min(1023, min(v * gain // 1024 for v, gain in zip(rgb, gains)) // 32)
    return min(1023, (2 * red + green + blue) // 128)


def auxiliary_indices(rgb, gains=None, vectorized=False):
    """Observed luma/chroma lookup coordinates and green-minus-blue table sign."""
    luma = auxiliary_luma_bin(rgb, gains)
    if type(vectorized) is not bool:
        raise ValueError('Require a boolean processing mode')
    red, green, blue = rgb
    delta = green - blue
    difference = delta // 32 if vectorized or delta >= 0 else -((-delta) // 32)
    nonnegative = delta >= 0 if vectorized else difference >= 0
    return luma, min(1023, abs(difference)), min(1023, max(0, (green - red) // 32)), nonnegative


def scale_chroma_pair(chroma, amount, gains):
    """Observed sign-dependent Q10 then Q7 gain, before subsequent clipping."""
    if len(chroma) != 2 or any(type(v) is not int or not -32768 <= v <= 32767 for v in chroma):
        raise ValueError('Require two signed 16-bit chroma values')
    if type(amount) is not int or not 0 <= amount <= 1024:
        raise ValueError('Require a bounded Q10 amount')
    if len(gains) != 4 or any(type(v) is not int or not 0 <= v <= 256 for v in gains):
        raise ValueError('Require four bounded Q7 gains')
    result = []
    for index, value in enumerate(chroma):
        product = value * amount
        scaled = product // 1024 if product >= 0 else -((-product) // 1024)
        product = scaled * gains[index * 2 + (0 if value > 0 else 1)]
        result.append(product // 128 if product >= 0 else -((-product) // 128))
    return result


def mix_chroma_luma(channels, weights, chroma, maximum):
    """Observed post-gain mix before optional exposure scaling and clipping."""
    if len(channels) != 3 or any(type(v) is not int or not 0 <= v <= 65535 for v in channels):
        raise ValueError('Require three unsigned 16-bit channels')
    if len(weights) != 3 or any(type(v) is not int or not 0 <= v <= 1024 for v in weights) or sum(weights) > 1024:
        raise ValueError('Require bounded positive Q10 weights summing to at most 1024')
    if len(chroma) != 2 or any(type(v) is not int or not -65536 <= v <= 65535 for v in chroma):
        raise ValueError('Require bounded post-gain chroma')
    if type(maximum) is not int or not 0 <= maximum <= 65535:
        raise ValueError('Require unsigned 16-bit upper limit')
    base = sum(value * weight for value, weight in zip(channels, weights)) // 1024
    first, second = (min(value, maximum) for value in chroma)
    numerator = base * 8192 - first * 1536 - second * 4096
    mixed = numerator // 8192 if numerator >= 0 else -((-numerator) // 8192)
    return [base + first, base + second, mixed]


def scale_mixed_channels(values, factor, minimum, maximum):
    """Observed Q14 scaling and signed bounds following the chroma mix."""
    if len(values) != 3 or any(type(v) is not int or not -131072 <= v <= 131072 for v in values):
        raise ValueError('Require three bounded signed mixed channels')
    if type(factor) is not int or not 0 <= factor <= 65536:
        raise ValueError('Require a bounded positive Q14 factor')
    if type(minimum) is not int or type(maximum) is not int or not -131071 <= minimum <= maximum <= 131071:
        raise ValueError('Invalid signed channel bounds')
    output = []
    for value in values:
        product = value * factor
        scaled = product // 16384 if product >= 0 else -((-product) // 16384)
        output.append(max(minimum, min(maximum, scaled)))
    return output


def signed_curve_lookup(value, positive_limit, full=None, coarse=None):
    """Observed post-mix signed lookup, including reflection about lookup(0)."""
    if type(value) is not int or not -131072 <= value <= 131072 or type(positive_limit) is not int or not 0 <= positive_limit <= 131072:
        raise ValueError('Invalid signed lookup coordinate or positive limit')
    table = full if full is not None else coarse
    if table is not None:
        length, maximum = (131073, 65535) if full is not None else (4097, 4095)
        if len(table) != length or any(type(v) is not int or not 0 <= v <= maximum for v in table):
            raise ValueError('Invalid signed lookup table')

    def lookup(index):
        if full is not None:
            return full[index]
        if coarse is not None:
            return coarse[(index + 1) // 32] * 32
        return index * 2

    if value >= 0:
        return lookup(min(value, positive_limit))
    return 2 * lookup(0) - lookup(-value)


def post_lookup_chroma(rgb, boost_first=False):
    """Observed second chroma conversion, distinct from the pre-tone matrix."""
    if len(rgb) != 3 or any(type(v) is not int or not -262144 <= v <= 262144 for v in rgb) or type(boost_first) is not bool:
        raise ValueError('Require bounded signed lookup outputs and a boolean mode')
    red, green, blue = rgb
    first = _trunc_q12(2048 * blue - 1360 * green - 688 * red)
    if boost_first:
        product = first * 9
        first = product // 8 if product >= 0 else -((-product) // 8)
    second = _trunc_q12(2048 * red - 1712 * green - 336 * blue)
    return [max(-32768, min(32767, value)) for value in (first, second)]


def chroma_from_rgb16(rgb, vectorized=False):
    if len(rgb)!=3 or any(type(v) is not int or not 0<=v<=65535 for v in rgb):
        raise ValueError('Require three unsigned RGB16 values')
    if type(vectorized) is not bool:
        raise ValueError('Require a boolean processing mode')
    red,green,blue=rgb
    numerators=(2048*blue-1356*green-691*red, 2048*red-333*blue-1714*green)
    return [value//4096 if vectorized else _trunc_q12(value) for value in numerators]


def pre_tone_rgb16(rgb, vectorized=False):
    """Observed Q10 luminance and first chroma round trip, before tone processing."""
    cb, cr = chroma_from_rgb16(rgb, vectorized=vectorized)
    red, green, blue = rgb
    luma = (306*red + 601*green + 117*blue)//1024
    values = (4096*luma + 5742*cr - 2*cb + 2048,
              4098*luma - 2925*cr - 1412*cb + 2048,
              4095*luma + 7254*cb + 2048)
    return [2*(value//4096 if vectorized else _trunc_q12(value)) for value in values]


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
