"""Pure4ad40/9189 readback conversion; no reads, cache or confirmation claim."""
import struct
from .mtp_read_reference import receive


def receive_9189(adapter,handler_selector,supported_operations):
    """Injected adapter only: explicit supported read, completed before decode.

    No OS adapter is constructed. Unsupported9189 is an error, not permission
    to substitute a cached property read or claim confirmation from send status.
    """
    if type(handler_selector) is not int or handler_selector not in (0x21,0x22,0x23):
        raise ValueError('Require explicit user-slot handler21..23')
    if type(supported_operations) not in (tuple,frozenset):
        raise ValueError('Require immutable explicit DeviceInfo capabilities')
    if len(supported_operations)>65535 or any(type(v) is not int or not 0<=v<=0xffff for v in supported_operations):
        raise ValueError('Invalid DeviceInfo operation codes')
    if 0x9189 not in supported_operations:
        raise ValueError('Readback9189 was not advertised')
    data=receive(adapter,0x9189,(handler_selector-0x20,),max_bytes=1048576)
    return decode_9189(data)


def decode_9189(value):
    """Explicit length-including-header path, not701d0's dual-size decoder.

    Native4ad40 builds validity/dataSize/body from length/validity/body.
    Strict total-length bounds here are independent safety policy. A matching
    return value alone does not establish a fresh post-registration read.
    """
    if not isinstance(value,(bytes,bytearray,memoryview)):
        raise ValueError('Require readback byte buffer')
    size=value.nbytes if isinstance(value,memoryview) else len(value)
    if not 8<=size<=1048576:raise ValueError('Readback outside bounded domain')
    value=bytes(value)
    declared,validity=struct.unpack_from('<II',value)
    if declared!=len(value):raise ValueError('Readback declared length differs')
    normalized=bytearray(declared)
    struct.pack_into('<I',normalized,0,validity)
    if validity:
        struct.pack_into('<I',normalized,4,declared-8)
        normalized[8:]=value[8:]
    return bytes(normalized)
