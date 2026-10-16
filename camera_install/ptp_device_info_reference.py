"""Bounded DeviceInfo dataset decoder; no USB/session or model assumptions."""
import struct
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeviceInfo:
    standard_version: int
    vendor_extension_id: int
    vendor_extension_version: int
    vendor_extension_description: str
    functional_mode: int
    operations: tuple[int, ...]
    events: tuple[int, ...]
    properties: tuple[int, ...]
    capture_formats: tuple[int, ...]
    image_formats: tuple[int, ...]
    manufacturer: str
    model: str
    device_version: str
    serial_number: str = field(repr=False)


def decode(data: bytes) -> DeviceInfo:
    if not isinstance(data,(bytes,bytearray,memoryview)):
        raise ValueError('DeviceInfo must be a byte buffer')
    length=data.nbytes if isinstance(data,memoryview) else len(data)
    if length > 1024*1024:
        raise ValueError('DeviceInfo exceeds bounded dataset size')
    data=bytes(data)
    cursor=0
    def read(size):
        nonlocal cursor
        if cursor+size > len(data):
            raise ValueError('Truncated DeviceInfo dataset')
        value=data[cursor:cursor+size];cursor+=size
        return value
    def number(fmt):
        return struct.unpack(fmt,read(struct.calcsize(fmt)))[0]
    def string():
        count=number('<B')
        if not count: return ''
        raw=read(count*2)
        if raw[-2:]!=b'\0\0':
            raise ValueError('Unterminated PTP string')
        try: value=raw[:-2].decode('utf-16-le')
        except UnicodeDecodeError as error:
            raise ValueError('Invalid PTP UTF16 string') from error
        if '\0' in value: raise ValueError('Embedded PTP string terminator')
        return value
    def array():
        count=number('<I')
        if count>4096: raise ValueError('DeviceInfo array exceeds safety bound')
        return struct.unpack('<'+'H'*count,read(count*2))
    header=(number('<H'),number('<I'),number('<H'),string(),number('<H'))
    arrays=tuple(array() for _ in range(5))
    strings=tuple(string() for _ in range(4))
    if cursor!=len(data): raise ValueError('Unexpected DeviceInfo trailing bytes')
    return DeviceInfo(*header,*arrays,*strings)
