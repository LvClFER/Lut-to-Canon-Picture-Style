"""USB-host PTP over an explicitly owned Android bulk connection.

The Java bridge supplies read(size, timeout_ms), write(bytes, timeout_ms).
Construction does not discover, claim, open or write to a camera.
"""
import math
import struct
import threading
import time

from .ptp_wire import Container, Decoder, MAX_CONTAINER_BYTES
from .wpd_data_phase_reference import Completion, PtpCommandError


class JavaBulk:
    """Avoid signed Java byte-array ambiguity at the Chaquopy boundary."""
    def __init__(self, connection):
        self.connection = connection

    def read(self, size, timeout):
        return bytes.fromhex(str(self.connection.readHex(size, timeout)))

    def write(self, payload, timeout):
        return int(self.connection.writeHex(payload.hex(), timeout))


class Transactions:
    def __init__(self, bulk, *, allow_control=False, allow_write=False, timeout=5.0):
        if type(allow_control) is not bool or type(allow_write) is not bool or (allow_write and not allow_control):
            raise ValueError('Require explicit control/write policy')
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 45:
            raise ValueError('Invalid USB transaction timeout')
        self.bulk = bulk
        self.allow_control, self.allow_write = allow_control, allow_write
        self.timeout = timeout
        self.next_transaction = 1
        self.owner = threading.get_ident()
        self.unusable = False
        self.active = False

    def _exchange(self, opcode, parameters, *, out_data=None, max_bytes=1048576):
        if self.unusable or self.active or threading.get_ident() != self.owner:
            raise RuntimeError('USB transaction owner is unavailable')
        if type(opcode) is not int or not 0 <= opcode <= 0xffff:
            raise ValueError('Invalid PTP operation')
        if type(parameters) is not tuple or len(parameters) > 5 or any(
                type(p) is not int or not 0 <= p <= 0xffffffff for p in parameters):
            raise ValueError('Invalid PTP parameters')
        if type(max_bytes) is not int or not 0 <= max_bytes <= MAX_CONTAINER_BYTES - 12:
            raise ValueError('Invalid receive bound')
        if out_data is not None and (not isinstance(out_data, bytes) or not 0 < len(out_data) <= 1048576):
            raise ValueError('Invalid outgoing data')
        transaction = self.next_transaction
        command = Container(1, opcode, transaction, struct.pack('<' + 'I' * len(parameters), *parameters)).encode()
        self.next_transaction += 1
        self.active = True
        deadline = time.monotonic() + self.timeout

        def remaining():
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError('USB transaction timed out; close the connection')
            return max(1, math.ceil(left * 1000))

        def write(packet):
            # Never replay a short write: the device may already have consumed it.
            for offset in range(0, len(packet), 16384):
                chunk = packet[offset:offset + 16384]
                if self.bulk.write(chunk, remaining()) != len(chunk):
                    raise OSError('USB did not acknowledge the exact byte count')

        try:
            write(command)
            if out_data is not None:
                write(Container(2, opcode, transaction, out_data).encode())
            decoder = Decoder()
            data = None
            for _ in range(2048):
                chunk = bytes(self.bulk.read(16384, remaining()))
                remaining()
                if not chunk or len(chunk) > 16384:
                    raise OSError('USB read failed or returned an invalid size')
                items = decoder.feed(chunk)
                # Reject an oversized data phase as soon as its header arrives.
                if len(decoder.buffer) >= 12:
                    size, kind, _, _ = struct.unpack_from('<IHHI', decoder.buffer)
                    if kind == 2 and size - 12 > max_bytes:
                        raise ValueError('USB data exceeds the requested bound')
                for index, item in enumerate(items):
                    if item.transaction != transaction:
                        raise ValueError('USB transaction identifier does not match')
                    if item.kind == 2:
                        if out_data is not None or data is not None or item.code != opcode or len(item.payload) > max_bytes:
                            raise ValueError('Unexpected USB data phase')
                        data = item.payload
                    elif item.kind == 3:
                        if index != len(items) - 1:
                            raise ValueError('Unexpected containers after PTP response')
                        decoder.finish()
                        completion = Completion(item.code, tuple(p[0] for p in struct.iter_unpack('<I', item.payload)))
                        if completion.response_code != 0x2001:
                            raise PtpCommandError(opcode, completion.response_code)
                        return completion, data or b''
                    else:
                        raise ValueError('Unexpected container on the USB bulk endpoint')
            raise TimeoutError('USB read count exceeded; close the connection')
        except PtpCommandError:
            raise
        except BaseException:
            self.unusable = True
            raise
        finally:
            self.active = False

    def execute(self, opcode, parameters=()):
        if not self.allow_control:
            raise PermissionError('USB control is not authorized')
        completion, _ = self._exchange(opcode, parameters, max_bytes=0)
        return completion

    def receive_atomic(self, opcode, parameters, *, max_bytes):
        return self._exchange(opcode, parameters, max_bytes=max_bytes)[1]

    def transfer_atomic(self, opcode, parameters, payload):
        if not self.allow_write:
            raise PermissionError('USB writing is not authorized')
        return self._exchange(opcode, parameters, out_data=payload, max_bytes=0)[0].response_code

    def native_profile(self):
        from .connection_profile import Profile
        from .ptp_device_info_reference import decode
        info = decode(self.receive_atomic(0x1001, (), max_bytes=1048576))
        return Profile(self, self, self, tuple(c for c in info.operations if c >= 0x9000), info)
