"""WPD property-map adapter with injected sender; no COM/device access.

Keys are (category GUID, property ID). A real sender must marshal these into
IPortableDeviceValues and preserve UI8 sizes / UI4 collections correctly.
This module deliberately supplies no real sender or registration entry point.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass

COMMON = 'f0422a9c-5dc8-4440-b5bd-5df28835658a'
MTP = '4d545058-1a2e-4106-a357-771e0819fc56'
Key = tuple[str, int]


@dataclass(frozen=True)
class Completion:
    response_code: int
    parameters: tuple[int, ...]


def decode_completion(result: Mapping[Key, object]) -> Completion:
    """Decode MTP1003/1004, bounding the response collection to five UI4s."""
    response = result.get((MTP, 1003))
    if type(response) is not int or not 0 <= response <= 0xffff:
        raise RuntimeError('Missing or invalid final PTP response')
    parameters = result.get((MTP, 1004))
    if not isinstance(parameters, (tuple, list)) or len(parameters) > 5:
        raise RuntimeError('Missing or oversized PTP response parameter collection')
    if any(type(p) is not int or not 0 <= p <= 0xffffffff for p in parameters):
        raise RuntimeError('Invalid PTP response parameter type')
    return Completion(response, tuple(parameters))


class PropertyMapAdapter:
    def __init__(self, sender: Callable[[Mapping[Key, object]], Mapping[Key, object]]):
        self._sender = sender
        self.last_completion: Completion | None = None

    def _command(self, command: int, values: dict[int, object]) -> Mapping[Key, object]:
        request = {(COMMON, 1001): MTP, (COMMON, 1002): command}
        request.update({(MTP, pid): value for pid, value in values.items()})
        result = self._sender(request)
        error = result.get((COMMON, 1003))
        if type(error) is not int or not 0 <= error <= 0xffffffff:
            raise RuntimeError('Missing or invalid WPD command HRESULT')
        if error & 0x80000000:
            raise RuntimeError(f'WPD command failed: 0x{error:08X}')
        return result

    def begin(self, opcode: int, parameters: tuple[int, ...], size: int) -> str:
        self.last_completion = None
        result = self._command(14, {1001: opcode, 1002: tuple(parameters), 1007: size})
        context = result.get((MTP, 1006))
        if not isinstance(context, str) or not context:
            raise RuntimeError('Missing WPD transfer context')
        return context

    def write(self, context: str, chunk: bytes) -> int:
        result = self._command(16, {1006: context, 1010: len(chunk), 1012: bytes(chunk)})
        count = result.get((MTP, 1011))
        if type(count) is not int or not 0 <= count <= 0xffffffff:
            raise RuntimeError('Missing or invalid WPD written-byte count')
        return count

    def complete(self, context: str) -> int:
        self.last_completion = None
        result = self._command(17, {1006: context})
        completion = decode_completion(result)
        self.last_completion = completion
        return completion.response_code


class ReadPropertyMapAdapter(PropertyMapAdapter):
    """Injected WPD13/15/17 receive maps; no COM or device implementation.

    Chunk sizing bounds optional driver1013 by an explicit controller policy.
    Returned1012 is buffer capacity; required actual count is property1009.
    Never substitute supplied buffers or asynchronous capacity for actual data.
    """
    def __init__(self, sender, *, chunk_size=65536):
        if type(chunk_size) is not int or not 0 < chunk_size <= 1048576:
            raise ValueError('Invalid receive chunk policy')
        super().__init__(sender)
        self._chunk_size = chunk_size

    def begin(self, opcode: int, parameters: tuple[int, ...]):
        from .mtp_read_reference import ReadStart
        self.last_completion = None
        result = self._command(13, {1001: opcode, 1002: tuple(parameters)})
        context = result.get((MTP, 1006))
        if not isinstance(context, str) or not context:
            raise RuntimeError('Missing WPD receive context')
        total = result.get((MTP, 1007))
        optimal = result.get((MTP, 1013), self._chunk_size)
        if (type(total) is not int or not 0 <= total <= 0xffffffffffffffff
                or type(optimal) is not int or not 0 < optimal <= 0xffffffff):
            # Begin succeeded and has a context: close once, never hide error.
            try:
                self.complete(context)
            except Exception:
                pass
            raise RuntimeError('Missing or invalid WPD receive size/chunk fields')
        # Documented WPD unknown-size sentinel; controller requires short EOF.
        return ReadStart(context, None if total == 0xffffffff else total,
                         min(optimal, self._chunk_size))

    def read(self, context: str, requested: int):
        from .mtp_read_reference import ReadChunk
        if not isinstance(context, str) or not context:
            raise ValueError('Require receive context')
        if type(requested) is not int or not 0 < requested <= 1048576:
            raise ValueError('Invalid bounded receive request')
        result = self._command(15, {1006: context, 1008: requested, 1012: bytes(requested)})
        value = result.get((MTP, 1012))
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise RuntimeError('Missing actual WPD receive buffer')
        size = value.nbytes if isinstance(value, memoryview) else len(value)
        if size > requested:
            raise RuntimeError('WPD receive buffer exceeds request')
        actual = result.get((MTP, 1009))
        if type(actual) is not int or not 0 <= actual <= size:
            raise RuntimeError('Missing or inconsistent WPD bytes-read count')
        return ReadChunk(bytes(value), actual)


class PtpCommandError(RuntimeError):
    def __init__(self, opcode, response_code):
        self.opcode, self.response_code = opcode, response_code
        super().__init__(f'Command 0x{opcode:04X} returned PTP 0x{response_code:04X}; expected 0x2001')


class CommandPropertyMapAdapter(PropertyMapAdapter):
    """Injected WPD command12, with no data phase or real device sender.

    This is not session setup or registration authorization. Native upper
    layers have busy retry behavior; this reference deliberately never retries.
    """
    def execute(self, opcode: int, parameters: tuple[int, ...] = ()) -> Completion:
        self.last_completion = None
        if type(opcode) is not int or not 0 <= opcode <= 0xffff:
            raise ValueError('Invalid command opcode')
        if type(parameters) is not tuple or len(parameters) > 5 or any(
                type(p) is not int or not 0 <= p <= 0xffffffff for p in parameters):
            raise ValueError('Require bounded immutable PTP parameters')
        result = self._command(12, {1001: opcode, 1002: parameters})
        completion = decode_completion(result)
        self.last_completion = completion
        if completion.response_code != 0x2001:
            raise PtpCommandError(opcode, completion.response_code)
        return completion
