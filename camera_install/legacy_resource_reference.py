"""Observed old-EU2 1007 resource selection; no resource bytes or transport.

This mapping belongs only to the archived 8837dc... compiler's 7b60 routine.
It is not a policy for modern cameras or a camera-install capability claim.
"""


def legacy_1007_resource_id(camera_selector: int, style: int) -> int:
    if type(camera_selector) is not int or type(style) is not int:
        raise TypeError('Selector and style must be integer IDs')
    bases = {0x80000213: 102, 0x80000232: 108,
             0x80000234: 114, 0x80000236: 120}
    if camera_selector not in bases or not 0x81 <= style <= 0x86:
        raise ValueError('Unmapped legacy selector or unsupported base style')
    return bases[camera_selector] + style - 0x81
