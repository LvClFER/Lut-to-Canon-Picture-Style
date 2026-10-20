import json
import struct
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from camera_install.independent_session_diagnostic import inspect_open_connection, _run_isolated, _worker_command
from camera_install.wpd_data_phase_reference import COMMON, MTP, PtpCommandError


class SessionDiagnosticTests(unittest.TestCase):
    def test_mac_worker_routes_fingerprint_to_native_session_without_wpd(self):
        from contextlib import contextmanager
        from camera_install import independent_session_diagnostic as diagnostic
        native=object()
        @contextmanager
        def opened(*args,**kwargs):
            self.assertEqual(args,('0123456789abcdef',))
            self.assertEqual(kwargs,dict(allow_session=True,allow_control=True))
            yield native
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'report.json'
            arguments=['diagnostic','--session-worker','--device-fingerprint','0123456789abcdef',
                '--allow-temporary-session','--output',str(output)]
            with patch.object(diagnostic.sys,'platform','darwin'),patch('sys.argv',arguments), \
                    patch.object(diagnostic,'WpdConnection') as wpd, \
                    patch('camera_install.macos_ptp.open_selected',side_effect=opened), \
                    patch.object(diagnostic,'inspect_open_connection',return_value={}) as inspect:
                diagnostic.main()
                wpd.assert_not_called();self.assertIs(inspect.call_args.args[0],native)
            report=json.loads(output.read_text())
            self.assertTrue(report['deviceOpenAttempted']);self.assertTrue(report['connectionCleanupCompleted'])

    def test_family_block_reports_reason_and_actual_cleanup_without_device_identity(self):
        from camera_install.independent_session_diagnostic import main
        from camera_install.family_registration_reference import FamilyCompatibilityError
        for cleaned in (True,False):
            with self.subTest(cleaned=cleaned), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);output=root/'report.json'
                error=FamilyCompatibilityError('Modern17 requires a modern live descriptor')
                error.temporary_modes_cleanup_completed=cleaned
                error.connection_cleanup_completed=True
                arguments=['diagnostic','--session-worker','--device-id','PRIVATE_ID',
                    '--allow-temporary-session','--request-descriptor','--request-slot','3',
                    '--preflight-style','owned.pf3','--experimental-register',
                    '--baseline-backup',str(root/'slot.bin'),'--output',str(output)]
                with patch('sys.argv',arguments), \
                     patch('camera_install.rp_preflight_reference.load_preflight_source',return_value=('source','keys')), \
                     patch('camera_install.independent_session_diagnostic.WpdConnection'), \
                     patch('camera_install.independent_registration_reference.register_open_connection',side_effect=error):
                    with self.assertRaises(FamilyCompatibilityError):main()
                report=json.loads(output.read_text())
                self.assertTrue(report['failed'])
                self.assertFalse(report['styleRegistrationAttempted'])
                self.assertEqual(report['blockedReason'],str(error))
                self.assertIs(report['temporaryModesCleanupCompleted'],cleaned)
                self.assertIs(report['connectionCleanupCompleted'],True)
                self.assertNotIn('PRIVATE',json.dumps(report))

    def test_other_observed_family_candidate_never_gains_rp_state_or_write_permission(self):
        connection,calls=self.connection(codes=(0x9110,0x9114,0x9115,0x9116,0x9127))
        with patch('camera_install.independent_session_diagnostic.receive',return_value=b'info'), \
             patch('camera_install.independent_session_diagnostic.decode_device_info',return_value=SimpleNamespace(operations=())), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_descriptor',return_value=b'descriptor'), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_slot_style',return_value=b'style'), \
             patch('camera_install.family_registration_reference.prepare_family_registration',
                return_value=(SimpleNamespace(route='modern83076-dense'),
                    dict(compilerProfileMatched=True,liveRegistrationEnabled=True))), \
             patch('camera_install.family_registration_reference.prepare_family_sequence',
                   side_effect=ValueError('Live slot state is not validated')):
            report=inspect_open_connection(connection,request_descriptor=True,request_slot=3,
                                           preflight_source=(b'source',None))
        candidate=report['compilerPreflight']
        self.assertTrue(candidate['compilerProfileMatched'])
        self.assertFalse(candidate['sequencePlanValidated'])
        self.assertFalse(candidate['writeAuthorized'])
        self.assertFalse(candidate['liveRegistrationEnabled'])
        self.assertIn('not validated',candidate['sequenceBlockedReason'])
        self.assertFalse(any(call[0]=='data' and call[1] in (14,16) for call in calls))

    def test_control_mismatch_report_explains_block_without_exposing_state(self):
        from camera_install.independent_session_diagnostic import main
        from camera_install.rp_preflight_reference import SlotControlMismatch
        mismatch=SlotControlMismatch((dict(control='Contrast',slotValue=-2,candidateValue=1),))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'report.json'
            arguments=['diagnostic','--session-worker','--device-id','PRIVATE_ID',
                '--allow-temporary-session','--request-descriptor','--request-slot','3',
                '--preflight-style','owned.pf3','--experimental-register',
                '--baseline-backup',str(root/'slot.bin'),'--output',str(output)]
            with patch('sys.argv',arguments), \
                 patch('camera_install.rp_preflight_reference.load_preflight_source',return_value=('source','keys')), \
                 patch('camera_install.independent_session_diagnostic.WpdConnection'), \
                 patch('camera_install.independent_registration_reference.register_open_connection',side_effect=mismatch):
                with self.assertRaises(SlotControlMismatch):main()
            report=json.loads(output.read_text())
            self.assertFalse(report['styleRegistrationAttempted'])
            self.assertEqual(report['controlDifferences'][0]['slotValue'],-2)
            self.assertIn('no style',report['blockedReason'])
            self.assertNotIn('PRIVATE',json.dumps(report))

    def test_registration_flag_and_backup_are_forwarded_only_when_explicit(self):
        args=self.arguments()
        self.assertNotIn('--experimental-register',_worker_command(args,Path('report.json')))
        args.experimental_register=True
        args.baseline_backup=Path('slot3.bin')
        args.preflight_style=Path('owned.pf3')
        command=_worker_command(args,Path('report.json'))
        self.assertEqual(command[-3:],['--experimental-register','--baseline-backup','slot3.bin'])
        self.assertNotIn('--update-known-basic-controls',command)
        args.update_known_basic_controls=True
        self.assertEqual(_worker_command(args,Path('report.json'))[-1],'--update-known-basic-controls')

    def test_supervisor_distinguishes_registration_from_read_only_completion(self):
        script='''
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps(dict(styleRegistrationAttempted=True,
    temporaryModesCleanupCompleted=True, connectionCleanupCompleted=True,
    baselineStyleBackupSaved=True, requestedSlotContentMatched=True,
    physicalAcceptanceEstablished=False, visualConfirmationRequired=True)))
'''
        prefix='camera_install.independent_session_diagnostic.'
        with patch(prefix+'_worker_command',side_effect=lambda args,output:
                   [sys.executable,'-S','-c',script,str(output)]):
            report,code=_run_isolated(self.arguments())
            self.assertNotEqual(code,0)
            self.assertFalse(report['styleRegistrationAttempted'])
            args=self.arguments();args.experimental_register=True
            report,code=_run_isolated(args)
        self.assertEqual(code,0)
        self.assertTrue(report['styleRegistrationAttempted'])
        self.assertFalse(report['cameraContentUnconfirmed'])
        self.assertFalse(report['physicalAcceptanceEstablished'])

    def test_supervisor_requires_basic_state_confirmation_when_update_is_explicit(self):
        base=dict(styleRegistrationAttempted=True,temporaryModesCleanupCompleted=True,
            connectionCleanupCompleted=True,baselineStyleBackupSaved=True,
            requestedSlotContentMatched=True,physicalAcceptanceEstablished=False,
            visualConfirmationRequired=True,knownBasicControlUpdateEnabled=True,
            knownBasicControlChanges=[dict(control='Contrast',slotValue=0,candidateValue=1)])
        args=self.arguments();args.experimental_register=True;args.update_known_basic_controls=True
        for matched in (None,False,True):
            result=dict(base,requestedSlotStateMatched=matched)
            script='from pathlib import Path;import sys;Path(sys.argv[1]).write_text('+repr(json.dumps(result))+')'
            with self.subTest(matched=matched),patch(
                    'camera_install.independent_session_diagnostic._worker_command',
                    side_effect=lambda args,output:[sys.executable,'-S','-c',script,str(output)]):
                report,code=_run_isolated(args)
            self.assertEqual(code==0,matched is True)
            self.assertEqual(report['cameraContentUnconfirmed'],matched is not True)

    def test_registration_timeout_does_not_claim_no_write_or_retry(self):
        args=self.arguments();args.experimental_register=True
        child=Mock(pid=123)
        child.wait.side_effect=[subprocess.TimeoutExpired('injected',1),-9]
        child.poll.side_effect=[None,-9,-9]
        prefix='camera_install.independent_session_diagnostic.'
        with patch(prefix+'subprocess.Popen',return_value=child), \
             patch(prefix+'_worker_command',return_value=['injected']):
            report,code=_run_isolated(args)
        self.assertEqual(code,124)
        self.assertIsNone(report['styleRegistrationAttempted'])
        self.assertTrue(report['cameraContentUnconfirmed'])
        self.assertTrue(report['recoveryRequired'])
        self.assertFalse(report['automaticRetry'])
        child.kill.assert_called_once()

    def test_experimental_worker_dispatch_requires_scope_and_write_enabled_connection(self):
        from camera_install.independent_session_diagnostic import main
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'report.json';backup=root/'slot3.bin'
            arguments=['diagnostic','--session-worker','--device-id','injected',
                '--allow-temporary-session','--request-descriptor','--request-slot','3',
                '--preflight-style','owned.pf3','--experimental-register',
                '--baseline-backup',str(backup),'--output',str(output)]
            with patch('sys.argv',arguments), \
                 patch('camera_install.rp_preflight_reference.load_preflight_source',return_value=('source','keys')), \
                 patch('camera_install.independent_session_diagnostic.WpdConnection') as opening, \
                 patch('camera_install.independent_registration_reference.register_open_connection',
                       return_value=dict(styleRegistrationAttempted=True)) as install:
                main()
            opening.assert_called_once_with('injected',allow_control=True,allow_write=True)
            self.assertTrue(install.call_args.kwargs['allow_experimental_write'])
            self.assertEqual(install.call_args.kwargs['slot'],3)
            self.assertEqual(install.call_args.kwargs['backup_path'],backup)
            self.assertTrue(json.loads(output.read_text())['connectionCleanupCompleted'])

    def test_bad_preflight_source_stops_before_discovery_or_device_open(self):
        from camera_install.independent_session_diagnostic import main
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'report.json'
            with patch('sys.argv', ['diagnostic', '--session-worker', '--device-fingerprint',
                       '0123456789abcdef', '--allow-temporary-session', '--request-descriptor',
                       '--request-slot', '3', '--preflight-style', 'owned.pf3', '--output', str(output)]), \
                 patch('camera_install.rp_preflight_reference.load_preflight_source',
                       side_effect=ValueError('PRIVATE_SOURCE_DETAIL')), \
                 patch('camera_install.independent_session_diagnostic.resolve_fingerprint') as discovery, \
                 patch('camera_install.independent_session_diagnostic.WpdConnection') as opening:
                with self.assertRaises(ValueError):
                    main()
                discovery.assert_not_called()
                opening.assert_not_called()
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertTrue(report['failed'])
            self.assertFalse(report['deviceOpenAttempted'])
            self.assertFalse(report['styleRegistrationAttempted'])
            self.assertNotIn('PRIVATE_SOURCE_DETAIL', json.dumps(report))

    def test_rejected_compiler_profile_retains_cleanup_and_never_authorizes_writing(self):
        connection, calls = self.connection(codes=(0x9110,0x9114,0x9115,0x9116,0x9127))
        with patch('camera_install.independent_session_diagnostic.receive', return_value=b'info'), \
             patch('camera_install.independent_session_diagnostic.decode_device_info',
                   return_value=SimpleNamespace(operations=(0x9110,))), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_descriptor',
                   return_value=b'descriptor'), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_slot_style',
                   return_value=b'style'), \
             patch('camera_install.family_registration_reference.prepare_family_registration',
                   side_effect=ValueError('Unverified compiler profile')):
            report = inspect_open_connection(connection, request_descriptor=True, request_slot=1,
                                             preflight_source=(b'source', None))
        self.assertTrue(report['temporaryModesCleanupCompleted'])
        self.assertFalse(report['compilerPreflight']['compilerProfileMatched'])
        self.assertFalse(report['compilerPreflight']['writeAuthorized'])
        self.assertFalse(report['styleRegistrationAttempted'])
        self.assertEqual(calls[-2:], [('command',0x9115,(0,)), ('command',0x9114,(0,))])
        self.assertFalse(any(call[0]=='data' and call[1] in (14,16) for call in calls))

    def test_compiler_preflight_runs_after_remote_cleanup_and_never_writes_data(self):
        connection,calls=self.connection(codes=(0x9110,0x9114,0x9115,0x9116,0x9127,0x911b,0x911c))
        def compile(*args,**kwargs):
            self.assertEqual(calls[-2:],[('command',0x9115,(0,)),('command',0x9114,(0,))])
            return None,dict(compilerProfileMatched=True,stateFreshnessEstablished=False)
        with patch('camera_install.independent_session_diagnostic.receive',return_value=b'info'), \
             patch('camera_install.independent_session_diagnostic.decode_device_info',return_value=SimpleNamespace(operations=(0x9110,))), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_descriptor',return_value=b'descriptor'), \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_slot_style',return_value=b'style'), \
             patch('camera_install.family_registration_reference.prepare_family_registration',side_effect=compile), \
             patch('camera_install.family_registration_reference.prepare_family_sequence',
                   return_value=SimpleNamespace(state=SimpleNamespace(data=bytes(52),property_code=0xd163))) as sequence:
            report=inspect_open_connection(connection,request_descriptor=True,request_slot=1,
                                          preflight_source=(b'source',('private','keys')))
        self.assertTrue(report['compilerPreflight']['compilerProfileMatched'])
        sequence.assert_called_once()
        self.assertTrue(report['compilerPreflight']['sequencePlanValidated'])
        self.assertTrue(report['compilerPreflight']['selectedSlotStateObserved'])
        self.assertFalse(report['compilerPreflight']['writeAuthorized'])
        self.assertFalse(report['styleRegistrationAttempted'])
        self.assertFalse(any(call[0]=='data' and call[1] in (14,16) for call in calls))
        self.assertNotIn('private',json.dumps(report))

    def test_preflight_worker_keeps_local_dependencies_and_explicit_selection(self):
        args=self.arguments();args.request_descriptor=True;args.request_slot=3
        args.preflight_style=Path('owned.canonstyleproject')
        command=_worker_command(args,Path('report.json'))
        self.assertNotIn('-S',command)
        self.assertEqual(command[-2:],['--preflight-style','owned.canonstyleproject'])
        self.assertIn('--request-descriptor',command)
        self.assertIn('--allow-temporary-session',command)

    def test_preflight_missing_read_scope_fails_before_capabilities_or_open(self):
        connection,calls=self.connection()
        with self.assertRaises(ValueError):inspect_open_connection(connection,preflight_source=(b'source',None))
        connection.capabilities.assert_not_called()
        self.assertEqual(calls,[])
        from camera_install.independent_session_diagnostic import main
        with patch('sys.argv',['diagnostic','--device-id','fake','--allow-temporary-session',
                              '--preflight-style','owned.pf3','--output','unused.json']), \
             patch('argparse.ArgumentParser.error',side_effect=ValueError('scope')), \
             patch('camera_install.independent_session_diagnostic.WpdConnection') as opening:
            with self.assertRaisesRegex(ValueError,'scope'):main()
            opening.assert_not_called()

    @staticmethod
    def arguments():
        return SimpleNamespace(device_id='PRIVATE_DEVICE_ID', device_fingerprint=None,
            request_descriptor=False, request_slot=None, test_ui_lock=False, timeout_seconds=1)

    def test_ui_lock_cycle_has_no_style_write_and_reads_selected_slot_on_both_sides(self):
        connection, calls = self.connection(codes=(0x9114, 0x9115, 0x9116, 0x9127, 0x911b, 0x911c))
        info = SimpleNamespace(operations=(0x1001, 0x9127, 0x911b, 0x911c))
        with patch('camera_install.independent_session_diagnostic.decode_device_info', return_value=info), \
                patch('camera_install.independent_session_diagnostic.receive', return_value=b'device-info'), \
                patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_slot_style',
                      return_value=b'normalized-synthetic-style') as read:
            report = inspect_open_connection(connection, request_slot=3, test_ui_lock=True)
        self.assertEqual([call[1:] for call in calls if call[0]=='command'],
                         [(0x9114, (1,)), (0x9115, (1,)), (0x911b, (1,)),
                          (0x911c, ()), (0x9115, (0,)), (0x9114, (0,))])
        self.assertEqual(read.call_count, 2)
        self.assertTrue(all(call.args==(0x23,) for call in read.call_args_list))
        self.assertTrue(report['uiLockCycleCompleted'])
        self.assertTrue(report['requestedSlotContentMatched'])
        self.assertFalse(report['styleRegistrationAttempted'])
        self.assertFalse(report['stateFreshnessEstablished'])

    def test_lock_failure_releases_once_and_retains_numeric_ptp_error(self):
        connection, calls = self.connection(codes=(0x9114, 0x9115, 0x9116, 0x911b, 0x911c))
        original = connection.commands.side_effect
        def command(request):
            result = original(request)
            if request[(MTP, 1001)]==0x911b:
                result[(MTP, 1003)] = 0x2019
            return result
        connection.commands.side_effect = command
        info = SimpleNamespace(operations=(0x911b, 0x911c))
        with patch('camera_install.independent_session_diagnostic.decode_device_info', return_value=info), \
                patch('camera_install.independent_session_diagnostic.receive', return_value=b'device-info'):
            with self.assertRaises(PtpCommandError) as raised:
                inspect_open_connection(connection, test_ui_lock=True)
        self.assertEqual((raised.exception.opcode, raised.exception.response_code), (0x911b, 0x2019))
        self.assertEqual([call[1] for call in calls if call[0]=='command'],
                         [0x9114, 0x9115, 0x911b, 0x911c, 0x9115, 0x9114])

    def test_ui_lock_requires_vendor_and_deviceinfo_support_before_remote_modes(self):
        connection, calls = self.connection()
        with self.assertRaisesRegex(RuntimeError, 'not advertised'):
            inspect_open_connection(connection, test_ui_lock=True)
        self.assertEqual(calls, [])
        connection, calls = self.connection(codes=(0x9114, 0x9115, 0x9116, 0x911b, 0x911c))
        with patch('camera_install.independent_session_diagnostic.receive', return_value=b'device-info'), \
                patch('camera_install.independent_session_diagnostic.decode_device_info',
                      return_value=SimpleNamespace(operations=())):
            with self.assertRaisesRegex(RuntimeError, 'DeviceInfo'):
                inspect_open_connection(connection, test_ui_lock=True)
        self.assertEqual(calls, [])

    def test_real_child_completes_without_exposing_stdout_or_device_id(self):
        script = '''
import json,sys
from pathlib import Path
print('PRIVATE_DRIVER_OUTPUT')
Path(sys.argv[1]).write_text(json.dumps(dict(styleRegistrationAttempted=False,
    temporaryModesCleanupCompleted=True, connectionCleanupCompleted=True)))
'''
        with patch('camera_install.independent_session_diagnostic._worker_command',
                   side_effect=lambda args, output: [sys.executable, '-S', '-c', script, str(output)]):
            report, code = _run_isolated(self.arguments())
        self.assertEqual(code, 0)
        self.assertFalse(report['failed'])
        self.assertFalse(report['recoveryRequired'])
        self.assertFalse(report['workerMayStillBeRunning'])
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_real_stuck_child_is_terminated_once_and_cleanup_stays_unconfirmed(self):
        real_popen, children = subprocess.Popen, []
        def spawn(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        prefix = 'camera_install.independent_session_diagnostic.'
        started = time.monotonic()
        with patch(prefix + '_worker_command', return_value=[sys.executable, '-S', '-c',
                   'import time; time.sleep(30)']), patch(prefix + 'subprocess.Popen', side_effect=spawn):
            report, code = _run_isolated(self.arguments())
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertLess(time.monotonic()-started, 6)
        self.assertEqual(code, 124)
        self.assertTrue(report['workerDeadlineExceeded'])
        self.assertTrue(report['recoveryRequired'])
        self.assertFalse(report['workerMayStillBeRunning'])
        self.assertIsNone(report['temporaryModesCleanupCompleted'])
        self.assertIsNone(report['connectionCleanupCompleted'])
        self.assertFalse(report['automaticRetry'])

    def test_shutdown_wait_is_bounded_even_if_termination_does_not_complete(self):
        child = Mock(pid=12345)
        child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('synthetic', 1)
        with patch('camera_install.independent_session_diagnostic.subprocess.Popen', return_value=child) as spawn:
            report, code = _run_isolated(self.arguments())
        self.assertEqual(code, 124)
        self.assertTrue(report['workerMayStillBeRunning'])
        self.assertIsNone(report['workerExitCode'])
        self.assertEqual([call.kwargs['timeout'] for call in child.wait.call_args_list], [1, 2])
        child.kill.assert_called_once()
        command = spawn.call_args.args[0]
        # The synthetic child never created a report, so this directory is empty.
        Path(command[command.index('--output')+1]).parent.rmdir()

    def test_frozen_worker_reuses_executable_and_preserves_only_selected_requests(self):
        args = self.arguments()
        args.device_id, args.device_fingerprint = None, '0123456789abcdef'
        args.request_descriptor, args.request_slot = True, 3
        with patch.object(sys, 'frozen', True, create=True):
            command = _worker_command(args, Path('report.json'))
        self.assertEqual(command[:2], [sys.executable, '--session-worker'])
        self.assertIn('--request-descriptor', command)
        self.assertEqual(command[-2:], ['--request-slot', '3'])
        self.assertNotIn('--device-id', command)

    def test_existing_report_prevents_child_launch_and_preserves_file(self):
        from camera_install.independent_session_diagnostic import main
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'report.json'
            output.write_text('original', encoding='utf-8')
            with patch('sys.argv', ['diagnostic', '--device-id', 'fake', '--output', str(output),
                                   '--allow-temporary-session']), \
                    patch('camera_install.independent_session_diagnostic.subprocess.Popen') as spawn:
                with self.assertRaises(FileExistsError):
                    main()
                spawn.assert_not_called()
            self.assertEqual(output.read_text(), 'original')

    def test_requested_slot_report_uses_device_info_and_excludes_payload(self):
        from test_ptp_device_info_reference import dataset
        connection, _ = self.connection(codes=(0x9114, 0x9115, 0x9116, 0x9127))
        style = struct.pack('<II', 1, 3) + b'abc'
        with patch('camera_install.independent_session_diagnostic.receive', return_value=dataset()) as read, \
             patch('camera_install.independent_session_diagnostic.RemoteEventSession.request_slot_style',
                   return_value=style) as requested:
            report = inspect_open_connection(connection, request_slot=1)
        self.assertEqual(read.call_args.args[1], 0x1001)
        requested.assert_called_once_with(0x21)
        self.assertEqual(report['slotStyleEventBytes'], 11)
        self.assertEqual(report['slotStyleEventValidity'], 1)
        self.assertIn('0x9189', report['deviceOperations'])
        self.assertFalse(report['stateFreshnessEstablished'])
        self.assertNotIn('private-serial', json.dumps(report))
        self.assertNotIn(style.hex(), json.dumps(report))

    def test_descriptor_request_requires_capability_before_remote_setup(self):
        connection, calls = self.connection()
        with self.assertRaisesRegex(RuntimeError, 'not advertised'):
            inspect_open_connection(connection, request_descriptor=True)
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            inspect_open_connection(connection, request_descriptor=1)

    def test_fingerprint_selection_never_guesses_or_opens_a_device(self):
        from camera_install.independent_session_diagnostic import resolve_fingerprint
        fingerprint = '0123456789abcdef'
        def discover(**kwargs):
            kwargs['_on_device']('PRIVATE_USB_ID', dict(canonCandidate=True, idFingerprint=fingerprint))
            return []
        with patch('camera_install.independent_session_diagnostic.enumerate_portable_devices', side_effect=discover), \
             patch('camera_install.independent_session_diagnostic.WpdConnection') as connection:
            self.assertEqual(resolve_fingerprint(fingerprint), 'PRIVATE_USB_ID')
            with self.assertRaises(RuntimeError):
                resolve_fingerprint('fedcba9876543210')
            connection.assert_not_called()
        with patch('camera_install.independent_session_diagnostic.enumerate_portable_devices') as discovery:
            for invalid in ('', 'A'*16, 'g'*16, None):
                with self.assertRaises(ValueError):
                    resolve_fingerprint(invalid)
            discovery.assert_not_called()

    def test_standalone_entry_help_without_site_packages_or_device_access(self):
        root = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, '-S', str(root / 'independent_camera_diagnostic.py'), '--help'],
            cwd=root, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--allow-temporary-session', result.stdout)
        self.assertIn('--device-id', result.stdout)

    def test_import_does_not_load_editor_or_native_compiler_dependencies(self):
        root = Path(__file__).resolve().parent
        script = """
import sys
import independent_camera_diagnostic
for name in sys.modules:
    assert name.split('.')[0] not in ('numpy', 'frida', 'PySide6'), name
    assert name not in ('camera_install.compiler_regression',
                        'camera_install.virtual_compatibility'), name
"""
        result = subprocess.run([sys.executable, '-S', '-c', script], cwd=root,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def connection(self, codes=(0x9114, 0x9115, 0x9116)):
        descriptor = b'PRIVATE_DESCRIPTOR_DO_NOT_EXPORT'
        values = ((0xd116, struct.pack('<I', 0x33040080)),
                  (0xd17f, struct.pack('<I', len(descriptor)+4)+descriptor),
                  (0xd163, struct.pack('<III', 44, 1, 0x41)+bytes(range(32))))
        body = b''.join(struct.pack('<III', len(value)+12, 0xc189, code)+value
                        for code, value in values) + struct.pack('<II', 8, 0)
        calls = []
        def command(request):
            calls.append(('command', request[(MTP, 1001)], request[(MTP, 1002)]))
            return {(COMMON, 1003): 0, (MTP, 1003): 0x2001, (MTP, 1004): ()}
        def data(request):
            stage = request[(COMMON, 1002)]
            calls.append(('data', stage))
            if stage == 13:
                self.assertEqual(request[(MTP, 1001)], 0x9116)
                return {(COMMON, 1003): 0, (MTP, 1006): 'fake', (MTP, 1007): len(body)}
            if stage == 15:
                return {(COMMON, 1003): 0, (MTP, 1012): body, (MTP, 1009): len(body)}
            self.assertEqual(stage, 17)
            return {(COMMON, 1003): 0, (MTP, 1003): 0x2001, (MTP, 1004): ()}
        connection = Mock()
        connection.commands.side_effect = command
        connection.data.side_effect = data
        connection.capabilities.return_value = {(COMMON, 1003): 0, (MTP, 1005): codes}
        return connection, calls

    def test_session_report_omits_state_and_descriptor_bytes(self):
        connection, calls = self.connection()
        report = inspect_open_connection(connection)
        self.assertEqual(report['cameraId'], '0x33040080')
        self.assertEqual(report['observedSlotHandlers'], ['0x21'])
        self.assertTrue(report['temporaryModesCleanupCompleted'])
        self.assertFalse(report['stateFreshnessEstablished'])
        self.assertFalse(report['styleRegistrationAttempted'])
        self.assertNotIn('PRIVATE_DESCRIPTOR', json.dumps(report))
        self.assertNotIn(bytes(range(32)).hex(), json.dumps(report))
        self.assertEqual(calls, [('command', 0x9114, (1,)),
                                ('command', 0x9115, (1,)),
                                ('data', 13), ('data', 15), ('data', 17),
                                ('command', 0x9115, (0,)), ('command', 0x9114, (0,))])

    def test_missing_capabilities_abort_before_mode_commands(self):
        for codes in ((), (0x9114, 0x9115), [0x9114, 0x9115, 0x9116]):
            connection, calls = self.connection(codes)
            with self.assertRaises(RuntimeError):
                inspect_open_connection(connection)
            self.assertEqual(calls, [])

    def test_cli_without_explicit_consent_never_constructs_connection(self):
        from camera_install.independent_session_diagnostic import main
        with patch('sys.argv', ['diagnostic', '--device-id', 'fake', '--output', 'unused.json']), \
             patch('camera_install.independent_session_diagnostic.WpdConnection') as connection, \
             patch('argparse.ArgumentParser.error', side_effect=ValueError('consent')):
            with self.assertRaisesRegex(ValueError, 'consent'):
                main()
            connection.assert_not_called()
