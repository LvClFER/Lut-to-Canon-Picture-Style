import unittest
from camera_install.mtp_read_reference import ReadStart, ReadChunk, receive


class Fake:
    def __init__(self, total, chunks, response=0x2001, optimal=4):
        self.start = ReadStart('owned-context', total, optimal)
        self.chunks = iter(chunks)
        self.response = response
        self.calls = []

    def begin(self, opcode, parameters):
        self.calls.append(('begin', opcode, parameters))
        return self.start

    def read(self, context, requested):
        self.calls.append(('read', context, requested))
        item = next(self.chunks)
        if isinstance(item, Exception):
            raise item
        return item

    def complete(self, context):
        self.calls.append(('complete', context))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ReceiveTests(unittest.TestCase):
    def completions(self, adapter):
        return sum(call[0] == 'complete' for call in adapter.calls)

    def test_known_length_and_empty_response(self):
        adapter = Fake(6, [ReadChunk(b'abcd', 4), ReadChunk(b'ef', 2)])
        self.assertEqual(receive(adapter, 0x9116), b'abcdef')
        self.assertEqual(self.completions(adapter), 1)
        self.assertEqual(receive(Fake(0, []), 0x9116), b'')

    def test_unknown_length_uses_actual_not_padded_capacity(self):
        adapter = Fake(None, [ReadChunk(b'abcd', 4), ReadChunk(b'eXYZ', 1)])
        self.assertEqual(receive(adapter, 0x9116), b'abcde')
        self.assertEqual(self.completions(adapter), 1)

    def test_failures_clean_up_once_without_promoting_success(self):
        for chunk in (ReadChunk(b'ab', 2), ReadChunk(b'abcde', 5),
                      ReadChunk(b'abcd', 5), ReadChunk(b'abcd', True),
                      ReadChunk(4, 4), RuntimeError('read failed')):
            adapter = Fake(4, [chunk])
            with self.subTest(chunk=chunk), self.assertRaises(RuntimeError):
                receive(adapter, 0x9116)
            self.assertEqual(self.completions(adapter), 1)

    def test_failed_completion_does_not_return_data_or_retry(self):
        for response in (0x2002, '8193', RuntimeError('completion failed')):
            adapter = Fake(4, [ReadChunk(b'abcd', 4)], response)
            with self.assertRaises(RuntimeError):
                receive(adapter, 0x9116)
            self.assertEqual(self.completions(adapter), 1)

    def test_unknown_size_bound_is_not_success(self):
        adapter = Fake(None, [ReadChunk(b'abcd', 4)])
        with self.assertRaises(RuntimeError):
            receive(adapter, 0x9116, max_bytes=4)
        self.assertEqual(self.completions(adapter), 1)
        adapter = Fake(None, [ReadChunk(b'abcd', 4)])
        with self.assertRaises(RuntimeError):
            receive(adapter, 0x9116, max_chunks=1)
        self.assertEqual(self.completions(adapter), 1)

    def test_invalid_start_and_arguments(self):
        for total in (True, -1, 1048577):
            adapter = Fake(total, [])
            with self.assertRaises(RuntimeError):
                receive(adapter, 0x9116)
            self.assertEqual(self.completions(adapter), 1)
        for opcode in (True, -1, 65536):
            adapter = Fake(0, [])
            with self.assertRaises(ValueError):
                receive(adapter, opcode)
            self.assertEqual(adapter.calls, [])
