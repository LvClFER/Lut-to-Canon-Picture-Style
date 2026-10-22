"""Bounded data-phase controller; injected adapter only, no device discovery.

This is not a camera registration state machine. Callers must separately
establish valid live state, carrier format and permission before any real use.
"""
from typing import Protocol


class Adapter(Protocol):
    def begin(self, opcode: int, parameters: tuple[int, ...], size: int) -> str: ...
    def write(self, context: str, chunk: bytes) -> int: ...
    def complete(self, context: str) -> int: ...


def transfer(adapter: Adapter, opcode: int, parameters: tuple[int, ...], payload: bytes,
             *, chunk_size: int = 65536, max_bytes: int = 1048576) -> int:
    """Require exact acknowledged bytes and final PTP OK; never retry a write.

    Completion is attempted once after any opened data phase, including failures.
    An unsuccessful transfer is never promoted to success by cleanup.
    """
    if type(opcode) is not int or not 0 <= opcode <= 0xffff:
        raise ValueError('Opcode is outside uint16')
    parameters = tuple(parameters)
    if len(parameters) > 5 or any(type(p) is not int or not 0 <= p <= 0xffffffff for p in parameters):
        raise ValueError('Invalid PTP parameters')
    if type(max_bytes) is not int or type(chunk_size) is not int or not 0 < chunk_size <= max_bytes <= 1048576:
        raise ValueError('Invalid data phase bounds')
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise ValueError('Payload must be a byte buffer')
    size = payload.nbytes if isinstance(payload,memoryview) else len(payload)
    if not 0 < size <= max_bytes:
        raise ValueError('Invalid data phase bounds')
    payload = bytes(payload)
    if callable(getattr(type(adapter),'transfer_atomic',None)):
        response=adapter.transfer_atomic(opcode,parameters,payload)
        if type(response) is not int or response!=0x2001:
            raise RuntimeError('Atomic data phase did not return PTP OK')
        return response
    context = adapter.begin(opcode, parameters, len(payload))
    if not isinstance(context, str) or not context:
        raise RuntimeError('Adapter returned no transfer context')
    completed = False
    try:
        for offset in range(0, len(payload), chunk_size):
            chunk = payload[offset:offset+chunk_size]
            acknowledged = adapter.write(context, chunk)
            if type(acknowledged) is not int or acknowledged != len(chunk):
                raise RuntimeError('Adapter did not acknowledge the exact written byte count')
        completed = True  # Never issue completion twice if it raises.
        response = adapter.complete(context)
        if response != 0x2001:
            raise RuntimeError(f'PTP data phase failed: response {response!r}')
        return response
    finally:
        if not completed:
            try:
                adapter.complete(context)
            except Exception:
                pass
