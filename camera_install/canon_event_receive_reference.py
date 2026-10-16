"""Bounded GetEvent continuation drain through an injected receive adapter.

No device discovery, session setup, registration writes or cache access.
Transport-completed batches do NOT establish fresh registration state: a
camera may return retained events. This module never authorizes installation.
"""
from dataclasses import dataclass
from .canon_events import PropertyEvent, decode_event_batch
from .mtp_read_reference import receive


@dataclass(frozen=True)
class CompletedEvents:
    properties: tuple[PropertyEvent, ...]
    batch_count: int
    received_bytes: int


def drain(adapter, parameters=(), *, max_batches=32, max_bytes=1048576):
    if type(max_batches) is not int or not 0 < max_batches <= 256:
        raise ValueError('Invalid event batch bound')
    if type(max_bytes) is not int or not 0 < max_bytes <= 16*1048576:
        raise ValueError('Invalid aggregate event byte bound')
    parameters=tuple(parameters)
    properties=[]
    received=0
    for index in range(max_batches):
        remaining=max_bytes-received
        if remaining <= 0:
            raise RuntimeError('Aggregate event limit reached during continuation')
        # receive exposes bytes only after successful PTP completion.
        data=receive(adapter,0x9116,parameters,max_bytes=remaining)
        received+=len(data)
        batch=decode_event_batch(data,max_value_bytes=max_bytes)
        properties.extend(batch.properties)
        if not batch.continuation:
            return CompletedEvents(tuple(properties),index+1,received)
    raise RuntimeError('Event continuation exceeded the batch bound')
