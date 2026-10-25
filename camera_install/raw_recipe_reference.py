"""Observed integer RAW-recipe primitives; offline references, not a renderer."""


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
