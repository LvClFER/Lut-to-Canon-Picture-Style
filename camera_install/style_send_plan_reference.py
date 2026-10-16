"""Pure58330 route/serialization reference, NOT registration authorization.

No discovery, session, state acquisition or transport is implemented here.
Capability selection precedes sending; a failed selected opcode does not
authorize retrying a different opcode.
"""
from dataclasses import dataclass,field
import struct
from .registration_encode_reference import encode_style,frame_property,MAX_TRANSFER_BYTES


@dataclass(frozen=True)
class StyleSendPlan:
    opcode:int
    parameters:tuple[int,...]
    data:bytes=field(repr=False)
    slot:int


def plan_style_send(carrier,handler_selector,supported_operations):
    """Known revision's selector21..23 and explicit DeviceInfo capabilities.

    The36 caption bytes are excluded, not interpreted as a portable name.
    Fresh state/session and a safe execution sequence remain caller problems;
    the result is an offline packet plan, never permission to write it.
    """
    if type(handler_selector) is not int or handler_selector not in (0x21,0x22,0x23):
        raise ValueError('Require observed handler selector21..23')
    if type(supported_operations) not in (tuple,frozenset):
        raise ValueError('Require immutable explicit operation codes')
    if len(supported_operations)>65535 or any(type(v) is not int or not 0<=v<=0xffff for v in supported_operations):
        raise ValueError('Invalid DeviceInfo operation codes')
    if not isinstance(carrier,(bytes,bytearray,memoryview)):
        raise ValueError('Require carrier bytes')
    size=carrier.nbytes if isinstance(carrier,memoryview) else len(carrier)
    if not 40<=size<=MAX_TRANSFER_BYTES-8:
        raise ValueError('Carrier outside bounded reference domain')
    carrier=bytes(carrier)
    validity,payload_size=struct.unpack_from('<II',carrier)
    if payload_size!=len(carrier)-40:
        raise ValueError('Carrier dataSize does not match envelope')
    serialized=encode_style(struct.pack('<II',validity,payload_size)+carrier[40:])
    slot=handler_selector-0x20
    for opcode in (0x9192,0x918a):
        if opcode in supported_operations:
            return StyleSendPlan(opcode,(slot,len(serialized)),serialized,slot)
    property_code=handler_selector+0xd14f
    return StyleSendPlan(0x9110,(),frame_property(property_code,serialized),slot)
