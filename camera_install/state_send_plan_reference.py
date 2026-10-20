"""Pure56650 slot-state framing, not fresh state acquisition or a send API.

The original32-byte control remains opaque and immutable. Caller must supply
an independently acquired marker/selector; saved captures do not prove freshness.
Only explicit user-slot21..23 branches are represented, not parameter0 aliases.
"""
from dataclasses import dataclass,field
import struct
from .registration_encode_reference import encode_state,frame_property


@dataclass(frozen=True)
class StateSendPlan:
    property_code:int
    data:bytes=field(repr=False)
    handler_selector:int
    extended:bool


def plan_slot_state(control,handler_selector,*,observed_marker,observed_selector):
    if type(handler_selector) is not int or handler_selector not in (0x21,0x22,0x23):
        raise ValueError('Require explicit observed user-slot handler')
    for value in (observed_marker,observed_selector):
        if type(value) is not int or not 0<=value<=0xffffffff:
            raise ValueError('Require independently observed uint32 state fields')
    if not isinstance(control,(bytes,bytearray,memoryview)):
        raise ValueError('Require opaque32-byte control buffer')
    size=control.nbytes if isinstance(control,memoryview) else len(control)
    if size not in ((32,) if observed_marker else (24,32)):
        raise ValueError('Control must preserve the observed legacy24 or extended32 bytes')
    control=bytes(control)
    extended=observed_marker!=0
    if extended:
        normalized=struct.pack('<II',observed_marker,observed_selector)+control
        property_code=handler_selector+0xd142
    else:
        # Native legacy wire representation copies six words; never alter the
        # original control blob or claim those omitted words are meaningless.
        normalized=struct.pack('<I',observed_selector)+control[:24]
        property_code=handler_selector+0xd13f
    return StateSendPlan(property_code,frame_property(property_code,
        encode_state(normalized,extended=extended)),handler_selector,extended)
