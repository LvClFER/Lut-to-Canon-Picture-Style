"""Integrated real marshalling/controller code; fake COM, no device access."""
import ctypes
import struct
import tempfile
import unittest
from pathlib import Path
from contextlib import ExitStack, nullcontext
from unittest.mock import patch, Mock
from camera_install.offline_registration_reference import prepare
from camera_install.wpd_command_sender import DataPhaseSender, CommandSender
from camera_install.wpd_data_phase_reference import PropertyMapAdapter, ReadPropertyMapAdapter, CommandPropertyMapAdapter
from camera_install.remote_session_reference import RemoteEventSession
from camera_install.event_mode_plan_reference import plan_event_modes
from camera_install.mtp_write_reference import transfer
from camera_install.mtp_read_reference import receive
from camera_install.registration_sequence_reference import plan_registration, execute_and_compare
from camera_install.identity_pf3_bootstrap_reference import recover_identity_calibration, recover_known_fields_calibration
import test_offline_registration_reference as source_fixture
import test_identity_pf3_bootstrap_reference as identity_fixture


class OfflineWpdIntegrationTests(unittest.TestCase):
    def exercise(self, *, partial_write=False, with_session=False, with_registration=False,
                 source=None, keys=None, property_route=False, route='compact16752-cache'):
        if keys is None:
            keys = source_fixture.OfflineRegistrationTests.keys
            if with_registration:
                calibration = identity_fixture.IdentityBootstrapTests.wrap(
                    [(0x1070, 3, identity_fixture.IdentityBootstrapTests.identity())], keys)
                keys = recover_identity_calibration(calibration)
        operations = ((0x1001, 0x9110, 0x9114, 0x9115, 0x9116, 0x911b, 0x911c, 0x9127)
                      if property_route else (0x9192, 0x9189))
        job = prepare(source_fixture.OfflineRegistrationTests.source() if source is None else source,
                      keys,
                      route=route, internal_selector=0x80000433,
                      normalized_descriptor=bytes(14796) if route=='compact16752-dense-pixel' else None,
                      handler_selector=0x22, supported_operations=operations)
        normalized = job.send.data[8:] if job.send.opcode == 0x9110 else job.send.data
        current = {}
        control = bytes(range(32))
        requested = []
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
                    if current['command'] == 12 and current['opcode'] == 0x9127:
                        requested.append(current['arguments'][0])
                    if current['command'] == 16:
                        transmitted.extend(current[1012])
                    if current['command'] == 13:
                        if current['opcode'] == 0x9116 and with_registration:
                            code = 0xd171 if requested else 0xd164
                            value = normalized if requested else struct.pack('<III', 44, 1, 0x42) + control
                            incoming['body'] = struct.pack('<III', len(value)+12, 0xc189, code) + value + struct.pack('<II', 8, 0)
                        else:
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
                if with_registration:
                    state = session.observed_inputs.slots[0]
                    sequence = plan_registration(job.carrier, state.control, state.handler_selector,
                        operations, observed_marker=state.marker, selected_cache_value=state.selector)
                    self.assertTrue(execute_and_compare(sequence, writer, commands, session.request_slot_style,
                                                        allow_write=True))
                    self.assertEqual(bytes(transmitted), job.send.data + sequence.state.data)
                else:
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
        if with_registration:
            self.assertEqual([c['command'] for c in calls], [12,14,16,17,14,16,17,12,12,13,15,17])
            self.assertEqual((calls[0]['opcode'], calls[0]['arguments']), (0x911b, (1,)))
            self.assertEqual(calls[1]['opcode'], job.send.opcode)
            self.assertEqual(calls[4]['opcode'], 0x9110)
            self.assertEqual((calls[7]['opcode'], calls[7]['arguments']), (0x911c, ()))
            self.assertEqual(requested, [0xd171])
            return
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

    def test_identity_bootstrap_compiler_state_registration_and_requested_event_comparison(self):
        self.exercise(with_session=True, with_registration=True)

    def test_editor_bundle_self_bootstrap_compiler_and_rp_property_route_with_fake_com(self):
        import canon_engine as engine
        from project_state import ProjectDocument, load_project
        keys = identity_fixture.IdentityBootstrapTests.keys(516)
        with tempfile.TemporaryDirectory() as directory, \
                patch('canon_engine.EdsCFParse', side_effect=AssertionError('Canon forbidden')):
            root = Path(directory)
            base = root / 'base.pf3'
            engine._write_independent_pf3(base, engine._generated_pf3_fields('Neutral'), keys)
            with patch('canon_engine.runtime_cache_dir', return_value=root / 'empty-cache'):
                lut = root / 'look.cube'
                lut.write_text('LUT_3D_SIZE 2\n' + '\n'.join(f'{1-r} {1-g} {1-b}'
                    for b in (0, 1) for g in (0, 1) for r in (0, 1)), encoding='utf-8')
                cube = engine.parse_lut_file(lut)
                controls = dict(contrast=1, saturation=-1, color_tone=2)
                bundle = root / 'editable.canonstyleproject'
                project = ProjectDocument(name='Editable', edit=dict(base_name='Neutral',
                    basePictureStyle='Neutral', base_path=str(base),
                    luts=[dict(id='look', path=str(lut), enabled=True, opacity=1)], **controls))
                engine.export_style_project(None, base, bundle,
                    [dict(cube=cube, enabled=True, opacity=1)], controls, 'Editable', project)
            base.unlink()
            lut.unlink()
            document = load_project(bundle, extraction_root=root / 'opened')
            self.assertTrue(Path(document.edit['luts'][0]['path']).is_file())
            raw = Path(document.renderedPf3).read_bytes()
            recovered = recover_known_fields_calibration(raw, engine._generated_calibration_fields())
            for route in ('compact16752-cache','compact16752-dense-pixel'):
                with self.subTest(route=route):
                    self.exercise(with_session=True, with_registration=True, source=raw,
                                  keys=recovered, property_route=True,route=route)
