"""Source-record settings for observed49830/4d8d0 complete-record branches.

Not a PF3 parser or complete compiler. Input records are already host-ordered
immutable bytes. Missing records and unobserved geometries are rejected.
"""
import struct


def settings_from_records(records, mode=1):
    if type(mode) is not int or mode not in (1, 2):
        raise ValueError('Unobserved source settings mode')
    def exact(identifier, length):
        value = records.get(identifier)
        if type(value) is not bytes or len(value) != length:
            raise ValueError(f'Require complete record {identifier:x}/{length}')
        return value

    axis = exact(0x1061 if mode == 1 else 0x1062, 512)
    axis_kind, axis_count = struct.unpack_from('<II', axis)
    if axis_kind != 2 or axis_count not in (0,6) or (axis_count == 0 and any(axis[8:])):
        raise ValueError('Require canonical empty or six-axis source geometry')
    if any(struct.unpack_from('<I', axis, 8 + n * 84)[0] != 5 for n in range(axis_count)):
        raise ValueError('Require five-point axes')
    selector = records.get(0x1023 if mode == 1 else 0x102b)
    if type(selector) is not bytes or not 8 <= len(selector) <= 2400:
        raise ValueError('Require bounded selector record1023')
    kind, count = struct.unpack_from('<II', selector)
    if kind != 1 or count > 12:
        raise ValueError('Unsupported selector geometry')
    block = {'kind': kind, 'count': count, 'bytes': len(selector), 'initializedHex': selector.hex()}
    if count:
        points = struct.unpack_from('<I', selector, 8)[0] if len(selector) >= 12 else 0
        if points not in (4, 5) or len(selector) != 8 + count * (4 + 16 * points):
            raise ValueError('Invalid selector span')
        block['points'] = points
    elif len(selector) != 8:
        raise ValueError('Unexpected empty-selector tail')
    return {'preCurvesHex': exact(0x1018, 300).hex(),
            'postCurvesHex': exact(0x1065, 300).hex(),
            'thirdCurvesHex': exact(0x1019, 300).hex(),
            'matrix240Hex': exact(0x1021 if mode == 1 else 0x1029, 240).hex(), 'mode': mode, 'splitCount': 0,
            'axisBlock': {'kind': 2, 'count': axis_count, 'points': 5,
                          'bytes': 512, 'initializedHex': axis.hex()},
            'selectorBlock': block}


def modern_user_grid_arguments(records, mode):
    """Complete-record4d8d0 zero-split branch, independently source-derived."""
    settings = settings_from_records(records, mode)
    axis, selector = settings['axisBlock'], settings['selectorBlock']
    return dict(preCurvesHex=settings['preCurvesHex'],
                postCurvesHex=settings['postCurvesHex'], thirdCurvesHex=settings['thirdCurvesHex'],
                matrix240Hex=settings['matrix240Hex'], numericArguments=[mode, 1],
                oldParameterBlock=None, oldParameters512Hex=None,
                axisParameterBlock=axis, sixAxes512Hex=axis['initializedHex'],
                axisParametersHex=axis['initializedHex'], additionalParameterBlock=selector,
                additionalParametersHeader8Hex=selector['initializedHex'][:16],
                additionalEmptyParametersHex=selector['initializedHex'] if selector['count'] == 0 else None)
