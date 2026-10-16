"""Research-only complete-record modern17 carrier replay.

Inputs are PF3 host-ordered records, a recorded normalized modern descriptor,
and explicitly supplied cipher tables. No camera support inference, transport,
Canon execution or automatic dependency discovery. Experimental scale256 and
alternate tail packing are restricted to the observed compiler route.
"""
from .cipher_stream_reference import decode
from .control_section_reference import build_control_plain
from .modern_header_reference import build_modern17_prefix
from .descriptor_import_reference import modern_grid_arguments
from .legacy_grid_reference import prepare as prepare_descriptor, flagged_point
from .modern_grid_reference import prepare, point, axis_settings, curve_settings, selector_settings
from .modern_composition_reference import sample17
from .packed17_reference import pack17_for_style
from .packed10_reference import pack10_for_style
from .tail_settings_reference import modern_user_grid_arguments, settings_from_records
from .compact_pixel_reference import prepare as prepare_pixel, point as pixel


def build_observed_modern17(fields, normalized_descriptor, keys, *, extended=False):
    if type(extended) is not bool or len(normalized_descriptor) != 14796:
        raise ValueError('Require observed modern descriptor and explicit extension flag')
    data = {identifier: value for identifier, (_, value) in fields.items()}
    style = int.from_bytes(data[0x1009], 'little')
    control = build_control_plain({i: fields[i] for i in (0x100a, 0x100d) if i in fields})
    encoded_control = control[:8] + decode(control[8:], keys, 0x22e1)
    prefix = build_modern17_prefix(fields, encoded_control, 83076 if extended else 78980)
    blocks = [None] * 4
    for mode in (1, 2):
        descriptor_args = modern_grid_arguments(normalized_descriptor, style, mode, mode)
        dcoeff, dmode, dcurves, dgroups = prepare_descriptor(descriptor_args)
        descriptor_rgb = [flagged_point((r, g, b), dcoeff, dmode, dcurves, dgroups, 17, 2)
                          for r in range(17) for g in range(17) for b in range(17)]
        arguments = modern_user_grid_arguments(data, mode)
        coefficients, color_mode = prepare(arguments, True)
        axes, softness = axis_settings(arguments)
        curves = curve_settings(arguments)
        curves['preGroups'], curves['postGroups'] = selector_settings(arguments)
        user_rgb = [point([min(v / 16, .9990234375) for v in (r, g, b)],
                          coefficients, color_mode, False, axes, softness, curves)
                    for r in range(17) for g in range(17) for b in range(17)]
        user_planar = [rgb[c] for c in range(3) for rgb in user_rgb]
        combined = [sample17(user_planar, rgb) for rgb in descriptor_rgb]
        combined_planar = [rgb[c] for c in range(3) for rgb in combined]
        for destination, values in ((mode - 1, combined_planar), (mode + 1, user_planar)):
            packed = pack17_for_style(values, style, mode)
            blocks[destination] = decode(packed, keys, 0xb8ed if destination % 2 == 0 else 0x33137)
    result = prefix + b''.join(blocks)
    if extended:
        dcoeff, dmode, dcurves, dgroups = prepare_descriptor(modern_grid_arguments(normalized_descriptor, style, 1))
        settings = prepare_pixel(settings_from_records(data))
        tail_rgb = [pixel([v / 256 for v in flagged_point((r, g, b), dcoeff, dmode, dcurves, dgroups, 10, 1)], settings)
                    for r in range(10) for g in range(10) for b in range(10)]
        tail_planar = [min(288, max(0, rgb[c] * 256)) for c in range(3) for rgb in tail_rgb]
        result += decode(pack10_for_style(tail_planar, style, 1), keys, 0xb8ed)
    return result
