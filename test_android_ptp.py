import struct
import unittest

from camera_install.android_ptp import JavaBulk, Transactions
from camera_install.ptp_wire import Container
from camera_install.wpd_data_phase_reference import PtpCommandError


class Bulk:
    def __init__(self, chunks=()):
        self.chunks, self.writes = list(chunks), []

    def read(self, size, timeout):
        assert 0 < size <= 16384 and 0 < timeout <= 45000
        return self.chunks.pop(0) if self.chunks else b''

    def write(self, packet, timeout):
        self.writes.append(packet)
        return len(packet)


def response(code=0x2001, transaction=1):
    return Container(3, code, transaction).encode()


class AndroidPtpTests(unittest.TestCase):
    def test_java_byte_bridge_preserves_unsigned_data(self):
        class JavaConnection:
            def readHex(self, size, timeout):
                return '0080ff'
            def writeHex(self, value, timeout):
                self.written = value
                return len(value) // 2
        connection = JavaConnection()
        bridge = JavaBulk(connection)
        self.assertEqual(bridge.read(3, 100), b'\0\x80\xff')
        self.assertEqual(bridge.write(b'\0\x80\xff', 100), 3)
        self.assertEqual(connection.written, '0080ff')

    def test_fragmented_data_and_response(self):
        packet = Container(2, 0x9116, 1, b'abcd').encode() + response()
        bulk = Bulk([packet[:7], packet[7:18], packet[18:]])
        owner = Transactions(bulk)
        self.assertEqual(owner.receive_atomic(0x9116, (), max_bytes=4), b'abcd')
        self.assertEqual(bulk.writes, [Container(1, 0x9116, 1).encode()])

    def test_one_outgoing_data_phase(self):
        bulk = Bulk([response()])
        owner = Transactions(bulk, allow_control=True, allow_write=True)
        self.assertEqual(owner.transfer_atomic(0x9110, (2,), b'abc'), 0x2001)
        self.assertEqual(bulk.writes[1], Container(2, 0x9110, 1, b'abc').encode())

    def test_timeout_invalidates_without_retry(self):
        bulk = Bulk()
        owner = Transactions(bulk)
        with self.assertRaises(OSError):
            owner.receive_atomic(0x1001, (), max_bytes=1024)
        with self.assertRaises(RuntimeError):
            owner.receive_atomic(0x1001, (), max_bytes=1024)
        self.assertEqual(len(bulk.writes), 1)

    def test_short_write_invalidates_without_retry(self):
        bulk = Bulk()
        bulk.write = lambda packet, timeout: len(packet) - 1
        owner = Transactions(bulk)
        with self.assertRaises(OSError):
            owner.receive_atomic(0x1001, (), max_bytes=1024)
        self.assertTrue(owner.unusable)

    def test_rejects_oversized_header_before_payload(self):
        bulk = Bulk([struct.pack('<IHHI', 10000, 2, 0x1001, 1)])
        owner = Transactions(bulk)
        with self.assertRaises(ValueError):
            owner.receive_atomic(0x1001, (), max_bytes=10)
        self.assertTrue(owner.unusable)

    def test_wrong_transaction_or_duplicate_data_invalidates(self):
        for packet in (response(transaction=2),
                       Container(2, 0x1001, 1, b'a').encode() * 2 + response()):
            owner = Transactions(Bulk([packet]))
            with self.assertRaises(ValueError):
                owner.receive_atomic(0x1001, (), max_bytes=10)
            self.assertTrue(owner.unusable)

    def test_camera_error_is_not_success(self):
        owner = Transactions(Bulk([response(0x2019)]))
        with self.assertRaises(PtpCommandError):
            owner.receive_atomic(0x1001, (), max_bytes=10)
        self.assertFalse(owner.unusable)

    def test_permissions_and_bad_arguments_do_not_write(self):
        bulk = Bulk()
        owner = Transactions(bulk)
        for action in (lambda: owner.execute(0x1002),
                       lambda: owner.transfer_atomic(0x9110, (), b'x'),
                       lambda: owner.receive_atomic(0x1001, (True,), max_bytes=10)):
            with self.assertRaises((PermissionError, ValueError)):
                action()
        self.assertEqual(bulk.writes, [])


if __name__ == '__main__':
    unittest.main()
