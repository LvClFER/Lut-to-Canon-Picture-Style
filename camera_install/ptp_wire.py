"""Platform-neutral USB PTP framing only; no device access or registration.

USB bulk framing is not the payload format of Apple's PTP command API.
Adapters must explicitly convert their platform's representation.
"""
from dataclasses import dataclass
import struct

HEADER = struct.Struct("<IHHI")
MAX_CONTAINER_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class Container:
    kind: int
    code: int
    transaction: int
    payload: bytes = b""

    def encode(self) -> bytes:
        if self.kind not in (1, 2, 3, 4):
            raise ValueError("Unknown PTP container type")
        if not 0 <= self.code <= 0xffff or not 0 <= self.transaction <= 0xffffffff:
            raise ValueError("PTP integer outside wire range")
        payload = bytes(self.payload)
        if self.kind != 2:
            limit = 3 if self.kind == 4 else 5
            if len(payload) % 4 or len(payload) > limit * 4:
                raise ValueError("Invalid PTP parameter list")
        size = HEADER.size + len(payload)
        if size > MAX_CONTAINER_BYTES:
            raise ValueError("PTP container exceeds bound")
        return HEADER.pack(size, self.kind, self.code, self.transaction) + payload


class Decoder:
    """Incremental bounded decoder for fragmented/coalesced USB reads."""

    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[Container]:
        if len(self.buffer) + len(data) > MAX_CONTAINER_BYTES:
            raise ValueError("PTP receive buffer exceeds bound")
        self.buffer.extend(data)
        output = []
        while len(self.buffer) >= HEADER.size:
            size, kind, code, transaction = HEADER.unpack_from(self.buffer)
            if not HEADER.size <= size <= MAX_CONTAINER_BYTES:
                self.buffer.clear()
                raise ValueError("Invalid PTP container length")
            if len(self.buffer) < size:
                break
            item = Container(kind, code, transaction, bytes(self.buffer[HEADER.size:size]))
            try:
                item.encode()  # Validate parameter geometry and type before consuming.
            except ValueError:
                self.buffer.clear()
                raise
            del self.buffer[:size]
            output.append(item)
        return output

    def finish(self):
        if self.buffer:
            raise ValueError("Truncated PTP stream")
