"""Experimental offline source-to-carrier accepted modern17 reference.

No Canon execution or discovery, device transport, registration or capability
inference. Caller supplies normalized descriptor and cipher keys. Observed
Neutral83076 archive is validated; other bases/layouts require independent
evidence. Production installation does not call this module.
"""
import numpy as np
from .cipher_stream_reference import decode
from .control_section_reference import build_control_plain
from .modern_header_reference import build_modern17_prefix
from .descriptor_import_reference import modern_grid_arguments
from .legacy_grid_reference import prepare, flagged_point
from .modern_composition_reference import sample17
from .dense17_reference import convert17
from .compact_grid_reference import compact_flag1
from .packed17_reference import pack17_for_style
from .packed10_reference import pack10


def dense_source(data):
    if type(data) is not bytes or len(data) != 215628:
        raise ValueError('Require exact host-ordered12-bit33 RGB record')
    words = np.frombuffer(data, dtype='<u2')
    if words[:3].tolist() != [12, 3, 33] or np.any(words[3:] > 4095):
        raise ValueError('Invalid dense source geometry/range')
    return words[3:].reshape(33,33,33,3).astype(np.float64) / 4095


def build_accepted_modern17(fields, normalized_descriptor, keys, *, extended=True):
    if type(extended) is not bool or len(normalized_descriptor) != 14796:
        raise ValueError('Require modern descriptor and explicit extension flag')
    try:
        style_bytes = fields[0x1009][1]
        first = dense_source(fields[0x1070][1])
        second = dense_source(fields[0x1071][1])
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('Missing complete source records') from error
    if type(style_bytes) is not bytes or len(style_bytes) != 2:
        raise ValueError('Require exact host-ordered base selector')
    style = int.from_bytes(style_bytes, 'little')
    blocks = [None] * 4
    for mode, source in enumerate((first, second), 1):
        arguments = modern_grid_arguments(normalized_descriptor, style, mode, mode)
        coefficients, color_mode, curves, groups = prepare(arguments)
        descriptor_rgb = [flagged_point((r,g,b), coefficients, color_mode, curves, groups, 17, 2)
                          for r in range(17) for g in range(17) for b in range(17)]
        user = convert17(source).ravel().tolist()
        combined = [sample17(user, rgb) for rgb in descriptor_rgb]
        for index, values in ((mode-1, [rgb[c] for c in range(3) for rgb in combined]), (mode+1, user)):
            packed = pack17_for_style(values, style, mode)
            blocks[index] = decode(packed, keys, 0xb8ed if index%2 == 0 else 0x33137)
    control = build_control_plain({i: fields[i] for i in (0x100a,0x100d) if i in fields})
    encoded_control = control[:8] + decode(control[8:], keys, 0x22e1)
    prefix = build_modern17_prefix(fields, encoded_control, 83076 if extended else 78980)
    result = prefix + b''.join(blocks)
    if extended:
        # Observed auxiliary reads source index1; false coefficient mode.
        result += decode(pack10(compact_flag1(first).ravel().tolist(), False), keys, 0xb8ed)
    return result
