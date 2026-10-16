"""Bounded opaque 1007 research extraction; never validates camera styles."""


def extract_opaque_record(payload):
    offset={8164:0x4c,8168:0x14c}.get(len(payload))
    if offset is None:
        raise ValueError('Unknown observed old-family geometry')
    return offset,bytes(payload[offset:offset+1460])


def verify_seed_influence(zero_payload,ff_payload):
    offset,zero=extract_opaque_record(zero_payload)
    other,ff=extract_opaque_record(ff_payload)
    if len(zero_payload)!=len(ff_payload) or offset!=other:
        raise ValueError('Mismatched diagnostic geometries')
    if zero!=bytes(1460) or ff!=bytes([255])*1460:
        raise ValueError('Not the observed zero/FF diagnostic records')
    if (zero_payload[:offset]!=ff_payload[:offset] or
            zero_payload[offset+1460:]!=ff_payload[offset+1460:]):
        raise ValueError('Changes extend outside opaque 1007')
    return {'property':'0x1007','offset':offset,'bytes':1460,
            'outsideRecordByteExact':True,'cameraInstallValidated':False,
            'syntheticDiagnosticOnly':True}
