"""Research-only independent replay of known-revision modern descriptor import.

Input is the actual 51b90 argument, not an assumed raw-file slice. Opaque
regions are preserved; this does not create descriptors for other cameras.
"""
import hashlib
import struct

from .cipher_stream_reference import decode


def validated_style_ordinal(selector):
    """Six independently observed Canon base selectors; no unknown fallback."""
    mapping = {0x81:0,0x82:1,0x83:2,0x84:3,0x85:4,0x88:5}
    if type(selector) is not int or selector not in mapping:
        raise ValueError('Unobserved base-style selector')
    return mapping[selector]


def parameterless_matrix_reference():
    """Observed49d76..49db6 fixed matrix; not an exact unity assumption."""
    words = [0] * 60
    for position in (0,21,42):
        words[position] = 0xffff
    return struct.pack('<60I', *words)


def importer_kind(version):
    """Known-revision 51590 selection, not model or payload-family prediction."""
    if type(version) is not int or not 0 <= version <= 0xffffffff:
        raise ValueError('Expected unsigned descriptor version')
    if version == 0x20000001:
        return 'compact'
    if version < 0x20000003:
        raise ValueError('Native descriptor version rejected with 81')
    if version < 0x20000008 or version == 0x2000000a:
        return 'compact'
    return 'modern'


def normalize_observed_raw(raw, keys):
    """Strictly replay only the two observed raw geometries, preserving the tail.

    The tail is returned uninterpreted, not asserted to be ignored globally.
    """
    if len(raw) < 4:
        raise ValueError('Missing descriptor version')
    kind = importer_kind(int.from_bytes(raw[:4], 'little'))
    length = 7492 if kind == 'compact' else 14796
    if len(raw) != length + 280:
        raise ValueError('Unobserved raw descriptor geometry')
    normalized = (normalize_compact if kind == 'compact' else normalize_modern)(raw[:length], keys)
    return normalized, raw[length:]


def normalize_modern(source, keys):
    if len(source) != 14796:
        raise ValueError('Expected exact observed modern import buffer')
    return _normalize(source, keys, 6, 0x9a0)


def modern_parameter_matrix(normalized, style_ordinal, index):
    """Static48a82..48ab1 matrix selection; runtime consumer proof is pending."""
    if (len(normalized) != 14796 or type(style_ordinal) is not int
            or not 0 <= style_ordinal < 6 or type(index) is not int or index not in (1, 2)):
        raise ValueError('Unobserved matrix selector or descriptor geometry')
    offset = 0x104 + style_ordinal * 0x9a0 + index * 0xf0
    return normalized[offset:offset + 240]


def modern_axis_parameters(normalized, style_ordinal, index):
    """Independent48b98..48ca2 five-point parameter expansion."""
    modern_parameter_matrix(normalized, style_ordinal, index)  # selector guard
    offset = 0x3f8 + style_ordinal * 0x9a0 + index * 0x1e4
    kind, count = struct.unpack_from('<HH', normalized, offset)
    if count > 12:
        raise ValueError('Axis group count exceeds the observed region')
    words = [kind, count]
    for group in range(count):
        words.append(5)
        start = offset + 4 + group * 40
        for position in range(20):
            fmt = '<H' if position % 4 == 0 else '<h'
            words.append(struct.unpack_from(fmt, normalized, start + position * 2)[0])
    return struct.pack('<' + 'I' * len(words), *(word & 0xffffffff for word in words))


def modern_four_point_parameters(normalized, style_ordinal, index):
    """Independent48aaa..48b98 expansion before the MLib wrapper."""
    modern_parameter_matrix(normalized, style_ordinal, index)
    offset = 0x2d0 + style_ordinal * 0x9a0 + index * 0x104
    kind, count = struct.unpack_from('<HH', normalized, offset)
    if count > 8:
        raise ValueError('Four-point group count exceeds observed region')
    words = [kind, count]
    for group in range(count):
        words.append(4)
        start = offset + 4 + group * 32
        for position in range(16):
            words.append(struct.unpack_from('<H' if position % 4 == 0 else '<h',
                                            normalized,start+position*2)[0])
    return struct.pack('<' + 'I' * len(words), *(word & 0xffffffff for word in words))


def modern_grid_arguments(normalized, style_selector, index, mode=1, policy=1):
    """Descriptor-derived zero-split arguments, without captured grid pixels.

    Only observed modern geometry and modes are accepted. This is a research
    reference, not a capability declaration for an attached camera.
    """
    if type(mode) is not int or mode not in (1, 2) or type(policy) is not int or policy not in (0, 1, 2):
        raise ValueError('Unobserved grid mode/policy')
    ordinal = validated_style_ordinal(style_selector)
    def block(raw, points):
        kind, count = struct.unpack_from('<2I', raw)
        return dict(kind=kind, count=count, points=points, bytes=len(raw), initializedHex=raw.hex())
    return dict(oldParameterBlock=None,
                axisParameterBlock=block(modern_axis_parameters(normalized, ordinal, index), 5),
                additionalParameterBlock=block(modern_four_point_parameters(normalized, ordinal, index), 4),
                matrix240Hex=modern_parameter_matrix(normalized, ordinal, index).hex(),
                preCurvesHex=None, postCurvesHex=None, thirdCurvesHex=None,
                numericArguments=[mode, policy])


def match_modern_matrix_calls(normalized, style_ordinal, captures):
    """Check stable MLib14bd0 entry observations, retaining index ambiguity."""
    matches = []
    for capture in captures:
        if capture.get('functionRva') != '0x14bd0':
            continue
        arguments = capture.get('initializedArguments', {})
        data = bytes.fromhex(arguments.get('matrix240Hex', ''))
        numeric = arguments.get('numericArguments', [])
        if len(data) != 240 or len(numeric) != 2 or numeric[0] not in (1, 2) or capture.get('result') != 1:
            raise ValueError('Incomplete or unsuccessful modern matrix consumer observation')
        indices = [index for index in (1, 2)
                   if data == modern_parameter_matrix(normalized, style_ordinal, index)]
        if not indices:
            raise ValueError('MLib matrix differs from both descriptor selections')
        matches.append(dict(mode=numeric[0],possibleDescriptorIndices=indices,
                            matrixSha256=hashlib.sha256(data).hexdigest(),exact=True))
    if not matches:
        raise ValueError('Missing stable modern matrix consumer observations')
    return matches


def match_modern_descriptor_calls(normalized, style_ordinal, captures):
    """Match all three initialized descriptor arguments on the zero-split route."""
    matches = []
    for capture in captures:
        if capture.get('functionRva') != '0x14bd0':
            continue
        args = capture.get('initializedArguments', {})
        if capture.get('result') != 1 or args.get('oldParameterBlock') is not None:
            raise ValueError('Require successful observed zero-split route')
        additional, axis = args.get('additionalParameterBlock'), args.get('axisParameterBlock')
        numeric = args.get('numericArguments', [])
        if len(numeric) != 2 or numeric[0] not in (1,2):
            raise ValueError('Missing observed modern mode')
        if not additional or not axis:
            raise ValueError('Missing initialized descriptor parameter blocks')
        indices = []
        for index in (1,2):
            if (additional.get('initializedHex') == modern_four_point_parameters(normalized,style_ordinal,index).hex()
                    and axis.get('initializedHex') == modern_axis_parameters(normalized,style_ordinal,index).hex()
                    and args.get('matrix240Hex') == modern_parameter_matrix(normalized,style_ordinal,index).hex()):
                indices.append(index)
        if not indices:
            raise ValueError('MLib descriptor arguments do not match any selected index')
        matches.append(dict(possibleDescriptorIndices=indices,
                            numericArguments=numeric,exact=True))
    if not matches:
        raise ValueError('Missing modern descriptor consumer observations')
    return matches


def normalize_compact(source, keys):
    if len(source) != 7492:
        raise ValueError('Expected exact observed compact import buffer')
    return _normalize(source, keys, 5, 0x5d8)


def _normalize(source, keys, count, stride):
    result = bytearray(source)
    for ordinal in range(count):
        base = ordinal * stride
        for index, seed in enumerate((0x3fcb, 0xc7)):
            for start in (base + 0x10 + index * 0xf0,
                          base + 0x1f4 + index * 0xf0):
                result[start:start + 0xf0] = decode(result[start:start + 0xf0], keys, seed)
    return bytes(result)


def verify_import_report(report, raw, keys):
    if any(report.get(field) is not False for field in
           ('cameraAccess', 'compilerPatched', 'sourceFilesModified')) or report.get('changedInputs') != []:
        raise ValueError('Require unchanged offline evidence')
    digest = hashlib.sha256(raw).hexdigest()
    if digest not in report.get('inputHashes', {}).values():
        raise ValueError('Descriptor hash missing from verified inputs')
    normalized, tail = normalize_observed_raw(raw, keys)
    kind = importer_kind(int.from_bytes(raw[:4], 'little'))
    source_field = kind + 'DescriptorSources'
    caller = '0x51b6f' if kind == 'compact' else '0x52093'
    checked = []
    if not report.get('rows'):
        raise ValueError('No native evidence rows')
    for row in report['rows']:
        sources = row.get(source_field, [])
        imports = row.get('descriptorImports', [])
        if not sources or not imports:
            raise ValueError('Missing native source/import observations')
        for source in sources:
            data = bytes.fromhex(source['dataHex'])
            if source['stage'] != 'inputs' or source['length'] != len(normalized) or data != raw[:len(normalized)]:
                raise ValueError('Import argument is not the verified raw prefix')
        for item in imports:
            if (item['stage'] != 'inputs' or item['callerRva'] != caller
                    or item['length'] != len(normalized) or bytes.fromhex(item['dataHex']) != normalized):
                raise ValueError('Independent import replay differs from native store')
        copies = row.get('descriptorCopies')
        if copies is None:
            raise ValueError('Missing reader-copy observations')
        for copy in copies:
            data = bytes.fromhex(copy['dataHex'])
            if (copy['length'] not in (7492, 14796) or len(data) != copy['length']
                    or len(data) > len(normalized) or data != normalized[:len(data)]):
                raise ValueError('Reader copy differs from normalized prefix')
        checked.append(dict(model=row['model'],cameraId=row['cameraId'],
                            imports=len(imports),copies=len(copies),exact=True))
    return dict(scope='Observed descriptor import/store/copy only; not camera compatibility',
                physicalValidation=False,descriptorSha256=digest,kind=kind,
                normalizedSha256=hashlib.sha256(normalized).hexdigest(),
                opaqueTailLength=len(tail),opaqueTailSha256=hashlib.sha256(tail).hexdigest(),rows=checked)


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    from .compiler_regression import cipher_tables
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('report', 'descriptor', 'dll', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    keys = cipher_tables(args.dll)
    if hashlib.sha256(args.dll.read_bytes()).hexdigest() not in report.get('inputHashes', {}).values():
        raise ValueError('Known DLL is not among verified native inputs')
    result = verify_import_report(report, args.descriptor.read_bytes(), keys)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print('Exact descriptor import rows:', len(result['rows']))
