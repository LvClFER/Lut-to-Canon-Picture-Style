"""Independent linkage of observed null-curve converter to float packer.

Intermediate equality is not final camera-payload equivalence.
"""
import numpy as np
from .compact_grid_reference import compact_flag1
from .packed10_reference import pack10


def verify_links(captures):
    packers = [c for c in captures if c.get('functionRva') == '0x4b760']
    rows = []
    for capture in captures:
        if capture.get('functionRva') != '0x196a0':
            continue
        if (capture.get('optionalCurves300Hex') is not None
                or capture.get('converterOption') not in (1,2)
                or capture.get('outputGrid',{}).get('headerWord12') != 1):
            raise ValueError('Unobserved converter configuration')
        source = np.frombuffer(bytes.fromhex(capture['sourceDenseFloat64Hex']),dtype='<f8').reshape(33,33,33,3)
        output_hex = capture['outputDenseFloat64Hex']
        output = np.frombuffer(bytes.fromhex(output_hex),dtype='<f8').reshape(3,10,10,10)
        error = float(np.max(np.abs(compact_flag1(source)-output)))
        if not np.isfinite(output).all() or not np.isfinite(error) or error > 1e-10:
            raise ValueError('Independent converter replay differs')
        matches = [p for p in packers if p.get('inputPlanarFloat64Hex') == output_hex]
        if not matches:
            raise ValueError('No exact converter-output/packer-input link')
        for packer in matches:
            if type(packer.get('coefficientMode')) is not bool:
                raise ValueError('Missing native packing coefficient mode')
            predicted = pack10(output.ravel().tolist(),packer['coefficientMode'])
            if predicted != bytes.fromhex(packer['nativePackedHex']):
                raise ValueError('Independent linked packing differs')
        rows.append(dict(option=capture['converterOption'],converterMaxError=error,
                         exactPackerInput=True,exactPacking=True,matchingPackers=len(matches)))
    if not rows:
        raise ValueError('Missing converter observations')
    return rows
