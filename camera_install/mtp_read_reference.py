"""Bounded receive controller using an injected adapter; no device/session I/O.

Transport completion is not event freshness or camera-registration acceptance.
"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ReadStart:
    context: str
    total_size: int | None
    optimal_size: int


@dataclass(frozen=True)
class ReadChunk:
    buffer: bytes = field(repr=False)
    actual: int


class Adapter(Protocol):
    def begin(self, opcode: int, parameters: tuple[int, ...]) -> ReadStart: ...
    def read(self, context: str, requested: int) -> ReadChunk: ...
    def complete(self, context: str) -> int: ...


def receive(adapter: Adapter, opcode: int, parameters: tuple[int, ...] = (),
            *, max_bytes: int = 1048576, max_chunks: int = 256) -> bytes:
    """Return actual bytes only after exact known length and final PTP OK.

    Unknown size ends only on a short read; reaching a bound is not EOF.
    Completion is attempted once, including cleanup after a failed read.
    """
    if type(opcode) is not int or not 0 <= opcode <= 0xffff:
        raise ValueError('Invalid receive opcode')
    parameters = tuple(parameters)
    if len(parameters) > 5 or any(type(p) is not int or not 0 <= p <= 0xffffffff for p in parameters):
        raise ValueError('Invalid PTP parameters')
    if type(max_bytes) is not int or not 0 < max_bytes <= 16*1024*1024:
        raise ValueError('Invalid receive byte bound')
    if type(max_chunks) is not int or not 0 < max_chunks <= 4096:
        raise ValueError('Invalid receive chunk bound')
    # ImageCaptureCore completes the entire native data phase in one callback.
    if callable(getattr(type(adapter),'receive_atomic',None)):
        payload=adapter.receive_atomic(opcode,parameters,max_bytes=max_bytes)
        if not isinstance(payload,bytes) or len(payload)>max_bytes:
            raise RuntimeError('Invalid atomic receive payload')
        return payload
    start = adapter.begin(opcode, parameters)
    if not isinstance(start, ReadStart) or not isinstance(start.context, str) or not start.context:
        raise RuntimeError('Adapter returned no receive context')
    completed = False
    try:
        total = start.total_size
        if total is not None and (type(total) is not int or not 0 <= total <= max_bytes):
            raise RuntimeError('Invalid announced receive size')
        if type(start.optimal_size) is not int or start.optimal_size <= 0:
            raise RuntimeError('Invalid optimal receive size')
        chunk_size = min(start.optimal_size, 1048576, max_bytes)
        payload = bytearray()
        reads = 0
        while total is None or len(payload) < total:
            if reads >= max_chunks or len(payload) >= max_bytes:
                raise RuntimeError('Receive limit reached before end of data')
            requested = min(chunk_size, max_bytes-len(payload))
            if total is not None:
                requested = min(requested, total-len(payload))
            chunk = adapter.read(start.context, requested)
            reads += 1
            if not isinstance(chunk, ReadChunk) or not isinstance(chunk.buffer, (bytes, bytearray, memoryview)):
                raise RuntimeError('Invalid received byte buffer')
            capacity = chunk.buffer.nbytes if isinstance(chunk.buffer, memoryview) else len(chunk.buffer)
            if capacity > requested or type(chunk.actual) is not int or not 0 <= chunk.actual <= capacity:
                raise RuntimeError('Inconsistent actual received byte count')
            payload.extend(bytes(chunk.buffer)[:chunk.actual])
            if chunk.actual < requested:
                if total is not None and len(payload) != total:
                    raise RuntimeError('Short receive before announced length')
                break
        completed = True
        response = adapter.complete(start.context)
        if type(response) is not int or response != 0x2001:
            raise RuntimeError('Receive completion did not return PTP OK')
        return bytes(payload)
    finally:
        if not completed:
            try:
                adapter.complete(start.context)
            except Exception:
                pass
