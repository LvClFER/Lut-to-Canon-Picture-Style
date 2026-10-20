"""Normalize already-open native/WPD connections without opening devices."""
from dataclasses import dataclass
from .wpd_data_phase_reference import COMMON,MTP,CommandPropertyMapAdapter,ReadPropertyMapAdapter,PropertyMapAdapter


@dataclass(frozen=True)
class Profile:
    commands:object
    reader:object
    writer:object
    operations:tuple
    device_info:object=None


def load(connection):
    if callable(getattr(type(connection),'native_profile',None)):
        return connection.native_profile()
    result=connection.capabilities({(COMMON,1001):MTP,(COMMON,1002):11})
    error=result.get((COMMON,1003));codes=result.get((MTP,1005))
    if (type(error) is not int or not 0<=error<=0xffffffff or error&0x80000000
            or type(codes) is not tuple or len(codes)>4096
            or any(type(code) is not int or not 0<=code<=0xffff for code in codes)):
        raise RuntimeError('Missing or invalid vendor operation capabilities')
    return Profile(CommandPropertyMapAdapter(connection.commands),ReadPropertyMapAdapter(connection.data),
        PropertyMapAdapter(connection.data),codes)
