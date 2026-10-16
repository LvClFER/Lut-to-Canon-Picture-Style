"""Validate initialized full33 doubles against stock payload words, offline only."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


def pack_full33(values):
    if len(values)!=33**3*3 or any(not math.isfinite(v) or v!=int(v) or not 0<=v<=32768 for v in values):
        raise ValueError('Require exact bounded initialized full33 integers')
    return struct.pack('<107811H',*[int(v) for v in values])


def source_full33_table(records, mode):
    """Experimental normal11220 route from host-ordered PF3 records.

    Does not read captured grid arguments, Canon DLLs, or camera state.
    This normal route is distinct from acceptance of arbitrary dense tables.
    """
    from .tail_settings_reference import modern_user_grid_arguments
    from .modern_grid_reference import prepare, axis_settings, curve_settings, selector_settings, point
    if type(mode) is not int or mode not in (1, 2):
        raise ValueError('Require observed color mode1/2')
    arguments = modern_user_grid_arguments(records, mode)
    coefficients, color_mode = prepare(arguments, True)
    axis_values, softness = axis_settings(arguments)
    curves = curve_settings(arguments)
    curves['preGroups'], curves['postGroups'] = selector_settings(arguments)
    values = [point([r/32, g/32, b/32], coefficients, color_mode, True,
                    axis_values, softness, curves)
              for r in range(33) for g in range(33) for b in range(33)]
    return pack_full33([rgb[c] for c in range(3) for rgb in values])


def encode_app_dense_full33(raw):
    """Portable equivalent of the app's encodeFull33Planar policy.

    This is direct 12-bit-to32768 planar conversion, NOT a claim that the
    unmodified Canon compiler accepts dense PF3 tables through its normal
    full33 route. The production hook currently replaces output tables.
    """
    if type(raw) is not bytes or len(raw) != 215628:
        raise ValueError('Require complete host-ordered dense PF3 table')
    words = struct.unpack('<107814H', raw)
    if words[:3] != (12, 3, 33) or max(words[3:]) > 4095:
        raise ValueError('Invalid dense PF3 geometry or sample range')
    from .compiler_regression import full33_planar
    return full33_planar(raw[6:])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); source=json.loads(args.trace.read_text(encoding='utf-8'))
    rows=[]; failures=[]
    for case in source['files']:
        if case.get('error'):
            failures.append(case['error']); continue
        payload=Path(case['privateResearchPayload']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=case['payloadSha256']:
            raise ValueError('Private payload differs from recorded compiler output')
        if len(payload)!=431616: continue
        for capture in case['mlibCalls']['captures']:
            for grid in capture.get('gridArguments',[]):
                if grid['nodes']!=33 or not grid.get('initializedOutputFloat64Hex'): continue
                raw=bytes.fromhex(grid['initializedOutputFloat64Hex'])
                packed=pack_full33(struct.unpack('<107811d',raw))
                offsets=[o for o in (372,215994) if payload[o:o+len(packed)]==packed]
                rows.append({'model':case['model'],'source':case['source'],'offsets':offsets,'passed':bool(offsets)})
    result={'cameraAccess':False,'rows':rows,'traceFailures':failures,'passed':sum(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':result['passed'],'traceFailures':len(failures)}))


if __name__=='__main__': main()
