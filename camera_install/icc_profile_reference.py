"""Read-only bounded ICC/mft2 geometry reference; no Canon fixtures or writer."""
import hashlib
import math
import struct


def encode_observed_lab16(lightness, axis_a, axis_b):
    """Reference for observed MLib2590 finite Lab encoding, not an ICC writer.

    Formula is statically derived; native intermediate-value equivalence remains
    a separate gate. The conversion helper discards fractional bits.
    """
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (lightness, axis_a, axis_b)):
        raise ValueError('Expected finite numeric Lab values')
    scaled_l = min(65535.0, max(0.0, lightness * 65535.0 / 100.0))
    def axis(value):
        # Preserve the two observed multiplications rather than reassociate.
        scaled = value * 65536.0 * (1.0 / 256.0)
        return math.trunc(min(32767.0, max(-32768.0, scaled)) + 32768.0)
    return struct.pack('>3H', math.trunc(scaled_l), axis(axis_a), axis(axis_b))


def inspect_profile(data):
    if not isinstance(data, bytes) or len(data) < 132:
        raise ValueError('Expected complete ICC bytes')
    size = struct.unpack_from('>I', data)[0]
    if size != len(data) or data[36:40] != b'acsp':
        raise ValueError('Invalid ICC envelope')
    count = struct.unpack_from('>I', data, 128)[0]
    end = 132 + count * 12
    if end > size:
        raise ValueError('Truncated tag table')
    tags, seen, ranges = [], set(), []
    for index in range(count):
        signature, offset, length = struct.unpack_from('>4sII', data, 132 + index * 12)
        if signature in seen or offset % 4 or offset < end or length < 8 or offset + length > size:
            raise ValueError('Invalid tag geometry or duplicate signature')
        seen.add(signature)
        for other_offset, other_length in ranges:
            overlap = max(offset, other_offset) < min(offset + length, other_offset + other_length)
            if overlap and (offset, length) != (other_offset, other_length):
                raise ValueError('Partially overlapping tags')
        ranges.append((offset, length))
        payload = data[offset:offset + length]
        tag = {'signature': signature.decode('ascii'), 'offset': offset, 'size': length,
               'type': payload[:4].decode('ascii'), 'sha256': hashlib.sha256(payload).hexdigest()}
        if payload[:4] == b'mft2':
            tag['lut16'] = inspect_lut16(payload)
        tags.append(tag)
    return {'size': size, 'profileClass': data[12:16].decode('ascii'),
            'inputColorSpace': data[16:20].decode('ascii'),
            'connectionSpace': data[20:24].decode('ascii'), 'tags': tags}


def inspect_lut16(data):
    if len(data) < 52 or data[:4] != b'mft2' or data[4:8] != bytes(4):
        raise ValueError('Invalid LUT16 header')
    inputs, outputs, grid = data[8:11]
    if not 1 <= inputs <= 4 or not 1 <= outputs <= 16 or grid < 2 or data[11] != 0:
        raise ValueError('Unsupported or invalid LUT16 geometry')
    input_entries, output_entries = struct.unpack_from('>HH', data, 48)
    if min(input_entries, output_entries) < 2:
        raise ValueError('Invalid LUT16 curve sizes')
    clut_offset = 52 + inputs * input_entries * 2
    clut_size = grid ** inputs * outputs * 2
    output_offset = clut_offset + clut_size
    required = output_offset + outputs * output_entries * 2
    padding = len(data) - required
    if len(data) not in (required, (required + 3) & ~3) or any(data[required:]):
        raise ValueError('LUT16 payload size does not match geometry')
    def linear_curves(offset, channels, entries):
        expected = tuple(round(i * 65535 / (entries - 1)) for i in range(entries))
        return [struct.unpack_from(f'>{entries}H',data,offset+channel*entries*2)==expected
                for channel in range(channels)]
    return {'inputChannels': inputs, 'outputChannels': outputs, 'gridNodes': grid,
            'inputEntries': input_entries, 'outputEntries': output_entries,
            'clutOffset': clut_offset, 'clutSize': clut_size,
            'paddingBytes': padding,
            'outputCurvesOffset': output_offset,
            'matrix16_16': list(struct.unpack_from('>9i',data,12)),
            'linearInputCurves': linear_curves(52,inputs,input_entries),
            'linearOutputCurves': linear_curves(output_offset,outputs,output_entries),
            'firstClutNode': list(struct.unpack_from(f'>{outputs}H',data,clut_offset)),
            'lastClutNode': list(struct.unpack_from(f'>{outputs}H',data,output_offset-outputs*2)),
            'clutSha256': hashlib.sha256(data[clut_offset:output_offset]).hexdigest()}
