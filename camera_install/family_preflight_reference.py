"""Read-only candidate preparation for exact observed profiles, not a write registry."""
import hashlib
from . import rp_preflight_reference as rp
from .descriptor_import_reference import normalize_observed_raw
from .accepted_modern_reference import inspect_extended17_style
from .offline_registration_reference import prepare


R8_DESCRIPTOR_SHA256='27c7378123643a23c9d21d0ea00cc5ae734dc98415dfd60ec3935fd787665642'


def prepare_observed_preflight(raw,keys,*,camera_id,descriptor,slot_style,slot,
                               vendor_operations,device_operations):
    if type(camera_id) is int and camera_id==0x80000433:
        return rp.prepare_rp_preflight(raw,keys,camera_id=camera_id,descriptor=descriptor,
            slot_style=slot_style,slot=slot,vendor_operations=vendor_operations,
            device_operations=device_operations)
    if type(camera_id) is not int or camera_id!=0x80000421:
        raise ValueError('No established independent compiler profile for this identifier')
    if type(slot) is not int or slot not in (1,2,3):
        raise ValueError('Require explicit user slot1..3')
    required={0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127}
    for codes in (vendor_operations,device_operations):
        if (type(codes) is not tuple or len(codes)>4096
                or any(type(code) is not int or not 0<=code<=0xffff for code in codes)
                or not required.issubset(codes)):
            raise ValueError('Required observed-profile operations were not advertised')
    if (type(descriptor) is not bytes or len(descriptor)!=15076
            or hashlib.sha256(descriptor).hexdigest()!=R8_DESCRIPTOR_SHA256):
        raise ValueError('Descriptor differs from the observed extended17 profile')
    inspect_extended17_style(slot_style,keys)
    normalized,_=normalize_observed_raw(descriptor,keys)
    job=prepare(raw,keys,route='modern83076-dense',normalized_descriptor=normalized,
        handler_selector=0x20+slot,supported_operations=(0x9110,))
    return job,dict(compilerProfileMatched=True,route=job.route,slot=slot,
        sourceSha256=job.source_sha256,carrierSha256=hashlib.sha256(job.carrier).hexdigest(),
        packetSha256=hashlib.sha256(job.send.data).hexdigest(),packetBytes=len(job.send.data),
        opcode=hex(job.send.opcode),physicalAcceptanceEstablished=False,
        stateFreshnessEstablished=False,liveRegistrationEnabled=False)
