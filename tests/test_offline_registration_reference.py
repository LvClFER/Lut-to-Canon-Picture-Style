import struct
import unittest
import subprocess
import sys
from unittest.mock import patch
from camera_install.cipher_stream_reference import decode
from camera_install.offline_registration_reference import prepare


class OfflineRegistrationTests(unittest.TestCase):
    keys = (bytes(512), bytes(513))

    @classmethod
    def source(cls, sample=0):
        records = [(0x1009, 3, struct.pack('>H', 0x84)),
                   (0x1002, 2, b'Synthetic'.ljust(32, b'\0')),
                   (0x100c, 3, bytes(2))]
        records += [(i, 4, struct.pack('>I', 2 if i in (0x1034, 0x1035) else 0))
                    for i in range(0x1030, 0x1036)]
        dense = struct.pack('>3H', 12, 3, 33) + struct.pack('>H', sample) * (33**3 * 3)
        records += [(0x1070, 3, dense), (0x1071, 3, dense)]
        body = b''.join(struct.pack('>HHI', i, kind, len(data)) + data
                        for i, kind, data in records)
        body += struct.pack('>HHII', 0xfffe, 4, 4, sum(body) & 0xffffffff)
        body += struct.pack('>HHI', 0xffff, 0xffff, 0)
        return bytes.fromhex('0000300050535000') + struct.pack('>I', len(body)) + decode(body, cls.keys, 12)

    def test_real_constructors_link_source_to_send_and_readback(self):
        raw = self.source()
        for route, selector, size in (('compact16752-cache', 0, 16752),):
            job = prepare(raw, self.keys, route=route, handler_selector=0x23,
                          supported_operations=(0x9189, 0x9192), internal_selector=selector)
            self.assertEqual(len(job.carrier), size)
            self.assertEqual(job.send.slot, 3)
            self.assertTrue(job.verify_content(job.send.data))
            with self.assertRaises(ValueError):
                job.verify_content(job.send.data[:-1] + bytes([job.send.data[-1] ^ 1]))

    def test_no_implicit_route_or_selector(self):
        for route, selector in (('automatic', None), ('normal-full33', 0),
                                ('compact16752-cache', None)):
            with self.assertRaises(ValueError):
                prepare(self.source(), self.keys, route=route,
                        handler_selector=0x21, supported_operations=(),
                        internal_selector=selector)

    def test_dense17_is_explicit_offline_and_preserves_its_transport_plan(self):
        carrier=struct.pack('<II',1,83036)+bytes(32)+bytes(83036)
        with patch('camera_install.offline_registration_reference.build_accepted_modern17',return_value=carrier) as compile:
            job=prepare(self.source(),self.keys,route='modern83076-dense',
                normalized_descriptor=bytes(14796),handler_selector=0x23,supported_operations=(0x9192,))
        self.assertEqual(len(job.carrier),83076)
        self.assertEqual(job.send.slot,3)
        self.assertEqual(job.send.opcode,0x9192)
        self.assertTrue(job.verify_content(job.send.data))
        self.assertTrue(compile.call_args.kwargs['extended'])
        for options in (dict(normalized_descriptor=None),dict(internal_selector=0x80000421)):
            args=dict(route='modern83076-dense',normalized_descriptor=bytes(14796),
                handler_selector=0x23,supported_operations=())
            args.update(options)
            with self.subTest(options=options),patch('camera_install.offline_registration_reference.build_accepted_modern17') as compile:
                with self.assertRaises(ValueError):prepare(self.source(),self.keys,**args)
                compile.assert_not_called()
        from camera_install.pf3_source_reference import read_source_fields,write_source_fields
        fields=dict(read_source_fields(self.source(),self.keys))
        fields[0x1009]=(3,b'\x81\x00')
        with patch('camera_install.offline_registration_reference.build_accepted_modern17') as compile:
            with self.assertRaisesRegex(ValueError,'requires Neutral'):
                prepare(write_source_fields(fields,self.keys),self.keys,route='modern83076-dense',
                    normalized_descriptor=bytes(14796),handler_selector=0x23,supported_operations=())
            compile.assert_not_called()

    def test_dense_lut_changes_compiled_blocks_not_just_metadata(self):
        jobs = [prepare(self.source(value), self.keys,
                        route='compact16752-cache', internal_selector=0,
                        handler_selector=0x21, supported_operations=(0x9192,))
                for value in (0, 4095)]
        self.assertEqual(jobs[0].carrier[:368], jobs[1].carrier[:368])
        for index in range(4):
            start = 368 + index * 4096
            self.assertNotEqual(jobs[0].carrier[start:start+4096],
                                jobs[1].carrier[start:start+4096])

    def test_integrated_path_does_not_import_native_lab_tools(self):
        # Fresh interpreter: already imported test modules cannot mask a leak.
        script = '''
import builtins
original = builtins.__import__
forbidden = {'camera_install.compiler_regression',
             'camera_install.virtual_compatibility', 'frida'}
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    package = (globals or {}).get('__package__', '')
    resolved = package + '.' + name if level else name
    if resolved in forbidden:
        raise RuntimeError('Native lab dependency: ' + resolved)
    return original(name, globals, locals, fromlist, level)
builtins.__import__ = guarded
from tests.test_offline_registration_reference import OfflineRegistrationTests
OfflineRegistrationTests().test_real_constructors_link_source_to_send_and_readback()
'''
        result = subprocess.run([sys.executable, '-c', script], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
