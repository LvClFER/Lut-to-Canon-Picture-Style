"""Pure known-revision event-to-compiler-input mapping, no device/cache I/O."""
import struct
from .canon_events import PropertyEvent


def initial_property_dispatch_order(events,*,initial):
    """48850 property-event projection: firstD116 prepass, then ALL events.

    The first ID is processed twice, not moved/deleted. Nonproperty native
    events are outside this projection. This produces indices, not callbacks
    or a session/state-machine implementation.
    """
    if type(initial) is not bool or type(events) is not tuple or len(events)>65536:
        raise ValueError('Require bounded immutable event batch and explicit initial flag')
    if any(not isinstance(event,PropertyEvent) or type(event.property_code) is not int
           or not 0<=event.property_code<=0xffffffff for event in events):
        raise ValueError('Require decoded property events')
    order=tuple(range(len(events)))
    if initial:
        first=next((i for i,event in enumerate(events) if event.property_code==0xd116),None)
        if first is not None:return (first,)+order
    return order


def camera_id_from_d116(value):
    """6fbe0/3b6c0: exact uint32 value and SDK's observed special alias.

    This does not enumerate models or predict a supported compiler family.
    """
    if not isinstance(value,(bytes,bytearray,memoryview)):
        raise ValueError('Require four-byte ID event')
    size=value.nbytes if isinstance(value,memoryview) else len(value)
    if size!=4:raise ValueError('Require four-byte ID event')
    identifier=struct.unpack('<I',bytes(value))[0]
    return 0x40000227 if identifier==0x80000227 else identifier


def descriptor_from_d17f(value):
    """70c80 copies declared bytes;3ba40 publishes the bytes after length.

    Bounded exact-length policy is stricter than native. Returned raw descriptor
    still requires independent cipher/store normalization before compilation.
    Parsing alone neither proves freshness nor supplies registration permission.
    """
    if not isinstance(value,(bytes,bytearray,memoryview)):
        raise ValueError('Require descriptor event byte buffer')
    size=value.nbytes if isinstance(value,memoryview) else len(value)
    if not 4<=size<=1048576:raise ValueError('Descriptor event outside bounds')
    value=bytes(value)
    declared=struct.unpack_from('<I',value)[0]
    if declared!=size:raise ValueError('Descriptor event length differs')
    return value[4:]
