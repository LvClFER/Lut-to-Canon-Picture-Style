"""Integrated real marshalling/controller code; fake COM, no device access."""
import ctypes
import struct
import unittest
from contextlib import ExitStack, nullcontext
from unittest.mock import patch, Mock
from camera_install.offline_registration_reference import prepare
from camera_install.wpd_command_sender import DataPhaseSender, CommandSender
from camera_install.wpd_data_phase_reference import PropertyMapAdapter, ReadPropertyMapAdapter, CommandPropertyMapAdapter
from camera_install.remote_session_reference import RemoteEventSession
from camera_install.event_mode_plan_reference import plan_event_modes
from camera_install.mtp_write_reference import transfer
from camera_install.mtp_read_reference import receive
import test_offline_registration_reference as source_fixture


class OfflineWpdIntegrationTests(unittest.TestCase):
    def exercise(self, *, partial_write=False, with_session=False):
        job = prepare(source_fixture.OfflineRegistrationTests.source(),
                      source_fixture.OfflineRegistrationTests.keys,
                      route='compact16752-cache', internal_selector=0,
                      handler_selector=0x22, supported_operations=(0x9192, 0x9189))
        current = {}
        incoming = {'body': job.send.data}
        calls, transmitted = [], bytearray()
        def new(ole32, command, *, opcode=None, args=(), context=None):
            current.clear()
            current.update(command=command, opcode=opcode, arguments=args, context=context)
            return ctypes.c_void_p(2)
        def set_number(params, key, value):
            current[key.pid] = value
        def set_buffer(params, key, value):
            current[key.pid] = value
        def method(pointer, index, *types):
            if index == 4:
                def send(device, flags, params, results):
                    results._obj.value = 3
                    calls.append(dict(current))
                    if current['command'] == 16:
                        transmitted.extend(current[1012])
                    if current['command'] == 13:
                        incoming['body'] = (struct.pack('<II', 8, 0)
                            if current['opcode'] == 0x9116 else job.send.data)
                    return 0
                return send
            if index == 20:
                def hresult(results, key, value):
                    value._obj.value = 0
                    return 0
                return hresult
            raise AssertionError(index)
        def get_number(results, key):
            if key.pid == 1011:
                return current[1010] - (1 if partial_write else 0)
            return {1003: 0x2001, 1013: 65536, 1009: len(incoming['body'])}[key.pid]
        prefix = 'camera_install.wpd_command_sender.'
        with ExitStack() as stack:
            for name, kwargs in (
                    ('api._new_mtp_params', {'side_effect': new}),
                    ('api._set_unsigned', {'side_effect': set_number}),
                    ('api._set_unsigned_large', {'side_effect': set_number}),
                    ('api._set_buffer', {'side_effect': set_buffer}),
                    ('api._method', {'side_effect': method}),
                    ('api._release', {}),
                    ('api._get_unsigned', {'side_effect': get_number}),
                    ('api._get_unsigned_large', {'side_effect': lambda *args: len(incoming['body'])}),
                    ('api._get_string', {'return_value': 'fake-context'}),
                    ('api._get_buffer', {'side_effect': lambda *args, **kwargs: incoming['body']}),
                    ('_response_parameters', {'return_value': ()})):
                stack.enter_context(patch(prefix + name, **kwargs))
            sender = DataPhaseSender(Mock(), ctypes.c_void_p(1), allow_write=True)
            writer = PropertyMapAdapter(sender)
            reader = ReadPropertyMapAdapter(sender)
            if partial_write:
                with self.assertRaisesRegex(RuntimeError, 'acknowledge'):
                    transfer(writer, job.send.opcode, job.send.parameters,
                             job.send.data, chunk_size=4096)
                self.assertEqual([call['command'] for call in calls], [14, 16, 17])
                return
            commands = CommandPropertyMapAdapter(CommandSender(Mock(), ctypes.c_void_p(1)))
            session = RemoteEventSession(commands, reader, plan_event_modes(1,
                helper_predicate=True, registry_option_enabled=False)) if with_session else nullcontext()
            with session:
                self.assertEqual(transfer(writer, job.send.opcode, job.send.parameters,
                                          job.send.data, chunk_size=4096), 0x2001)
                self.assertEqual(bytes(transmitted), job.send.data)
                readback = receive(reader, 0x9189, (job.send.slot,))
                self.assertTrue(job.verify_content(readback))
        if with_session:
            self.assertEqual([(c['opcode'], c['arguments']) for c in calls[:2]],
                             [(0x9114, (1,)), (0x9115, (1,))])
            self.assertEqual([c['command'] for c in calls[:5]], [12, 12, 13, 15, 17])
            self.assertEqual([(c['opcode'], c['arguments']) for c in calls[-2:]],
                             [(0x9115, (0,)), (0x9114, (0,))])
            calls = calls[5:-2]
        self.assertEqual([call['command'] for call in calls],
                         [14, 16, 16, 16, 16, 16, 17, 13, 15, 17])
        self.assertEqual(calls[0]['arguments'], (2, len(job.send.data)))
        self.assertEqual(calls[0][1007], len(job.send.data))
        self.assertEqual(calls[-3]['opcode'], 0x9189)
        self.assertEqual(calls[-3]['arguments'], (2,))

    def test_compiler_to_wpd_write_and_readback(self):
        self.exercise()

    def test_partial_write_completes_once_without_retry_or_readback(self):
        self.exercise(partial_write=True)

    def test_remote_event_lifecycle_wraps_compiler_transport_roundtrip(self):
        self.exercise(with_session=True)
