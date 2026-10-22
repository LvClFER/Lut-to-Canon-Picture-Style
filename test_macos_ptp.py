import unittest
from unittest.mock import Mock,patch
from camera_install import macos_ptp as ptp


class NativePtpTests(unittest.TestCase):
    def test_native_profile_uses_live_deviceinfo_and_retains_shared_adapters(self):
        from test_ptp_device_info_reference import dataset
        from camera_install.connection_profile import load
        owner=ptp.Transactions(object())
        with patch.object(ptp,'exchange',return_value=(ptp.Completion(0x2001,()),dataset())) as send:
            profile=load(owner)
        self.assertEqual(profile.operations,(0x9127,0x9189))
        self.assertEqual(profile.device_info.operations,(0x1001,0x9127,0x9189))
        self.assertIs(profile.commands,owner);self.assertIs(profile.reader,owner);self.assertIs(profile.writer,owner)
        self.assertEqual(send.call_args.args[1:4],(0x1001,(),1))

    def test_shared_controllers_use_atomic_native_transactions_in_order(self):
        from camera_install.mtp_read_reference import receive
        from camera_install.mtp_write_reference import transfer
        owner=ptp.Transactions(object(),allow_control=True,allow_write=True)
        with patch.object(ptp,'exchange',side_effect=[(ptp.Completion(0x2001,()),b''),
                (ptp.Completion(0x2001,()),b'events'),(ptp.Completion(0x2001,()),b'')]) as send:
            owner.execute(0x9114,(1,))
            self.assertEqual(receive(owner,0x9116),b'events')
            self.assertEqual(transfer(owner,0x9110,(),b'style'),0x2001)
            self.assertEqual([call.args[3] for call in send.call_args_list],[1,2,3])
            self.assertEqual(send.call_args.kwargs['out_data'],b'style')

    def test_timeout_disables_further_transactions_without_retry(self):
        owner=ptp.Transactions(object(),allow_control=True)
        with patch.object(ptp,'exchange',side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):owner.execute(0x9114,(1,))
            with self.assertRaises(RuntimeError):owner.execute(0x9114,(0,))
            send.assert_called_once()

    def test_ptp_error_allows_explicit_cleanup_with_next_transaction(self):
        owner=ptp.Transactions(object(),allow_control=True)
        with patch.object(ptp,'exchange',side_effect=[ptp.PtpCommandError(0x9114,0x2019),
                (ptp.Completion(0x2001,()),b'')]) as send:
            with self.assertRaises(ptp.PtpCommandError):owner.execute(0x9114,(1,))
            owner.execute(0x9114,(0,))
            self.assertEqual([call.args[3] for call in send.call_args_list],[1,2])

    def test_readonly_owner_refuses_control_and_write_before_native_io(self):
        owner=ptp.Transactions(object())
        with patch.object(ptp,'exchange') as send:
            with self.assertRaises(PermissionError):owner.execute(0x9114,(1,))
            with self.assertRaises(PermissionError):owner.transfer_atomic(0x9110,(),b'style')
            send.assert_not_called()

    def test_selected_connection_closes_session_before_releasing_browser_and_invalidates_owner(self):
        from contextlib import contextmanager
        from camera_install import macos_discovery
        order=[];camera=object()
        @contextmanager
        def selected(fingerprint):
            order.append('discover')
            try:yield camera
            finally:order.append('release')
        @contextmanager
        def session(device,**kwargs):
            self.assertIs(device,camera);order.append('open')
            try:yield camera
            finally:order.append('close')
        with patch.object(macos_discovery,'selected_camera',side_effect=selected), \
                patch.object(ptp,'authorized_session',side_effect=session):
            with ptp.open_selected('0123456789abcdef',allow_session=True) as owner:
                self.assertFalse(owner.unusable)
            self.assertTrue(owner.unusable)
        self.assertEqual(order,['discover','open','close','release'])

    def test_command_bytes_and_response_transaction_are_exact(self):
        command=ptp.encode_command(0x9127,(0xd172,),7)
        self.assertEqual(command.hex(),'10000000010027910700000072d10000')
        response=bytes.fromhex('10000000030001200700000078563412')
        self.assertEqual(ptp.decode_response(response,7),ptp.Completion(0x2001,(0x12345678,)))
        for malformed in (response[:-1],response+b'x',command,response+response,
                ptp.Container(3,0x2001,8).encode()):
            with self.subTest(raw=malformed.hex()),self.assertRaises(ValueError):ptp.decode_response(malformed,7)

    def test_exchange_keeps_out_data_unframed_and_rejects_ptp_failure(self):
        camera=object();out=b'owned payload'
        for code in (0x2001,0x2019):
            reply=ptp.NativeReply(ptp.Container(3,code,7).encode(),b'incoming')
            with self.subTest(code=code),patch.object(ptp,'send',return_value=reply) as send:
                if code==0x2001:
                    completion,data=ptp.exchange(camera,0x9110,(),7,out_data=out)
                    self.assertEqual((completion.response_code,data),(0x2001,b'incoming'))
                else:
                    with self.assertRaises(ptp.PtpCommandError):ptp.exchange(camera,0x9110,(),7,out_data=out)
                send.assert_called_once()
                self.assertIs(send.call_args.kwargs['out_data'],out)

    def test_session_opens_once_and_closes_after_success_or_failure(self):
        for failure in (False,True):
            camera=Mock();camera.hasOpenSession.return_value=False
            def opened(options,done):camera.hasOpenSession.return_value=True;done(None)
            def closed(options,done):camera.hasOpenSession.return_value=False;done(None)
            camera.requestOpenSessionWithOptions_completion_.side_effect=opened
            camera.requestCloseSessionWithOptions_completion_.side_effect=closed
            with self.subTest(failure=failure),patch.object(ptp.sys,'platform','darwin'), \
                    patch.dict('sys.modules',{'Foundation':Mock()}):
                try:
                    with ptp.authorized_session(camera,allow_session=True):
                        self.assertTrue(camera.hasOpenSession())
                        if failure:raise ValueError('body failed')
                except ValueError:
                    if not failure:raise
            camera.requestOpenSessionWithOptions_completion_.assert_called_once()
            camera.requestCloseSessionWithOptions_completion_.assert_called_once()

    def test_session_refuses_missing_authorization_and_preexisting_session(self):
        camera=Mock();camera.hasOpenSession.return_value=True
        with patch.object(ptp.sys,'platform','darwin'):
            for allowed in (False,True):
                with self.assertRaises((ValueError,RuntimeError)):
                    with ptp.authorized_session(camera,allow_session=allowed):self.fail('entered')
        camera.requestOpenSessionWithOptions_completion_.assert_not_called()
        camera.requestCloseSessionWithOptions_completion_.assert_not_called()

    def test_session_open_timeout_does_not_issue_overlapping_close(self):
        camera=Mock();camera.hasOpenSession.return_value=False
        with patch.object(ptp.sys,'platform','darwin'),patch.dict('sys.modules',{'Foundation':Mock()}), \
                patch.object(ptp.time,'monotonic',side_effect=[0,6]):
            with self.assertRaises(TimeoutError):
                with ptp.authorized_session(camera,allow_session=True):self.fail('entered')
        camera.requestOpenSessionWithOptions_completion_.assert_called_once()
        camera.requestCloseSessionWithOptions_completion_.assert_not_called()

    def test_cleanup_failure_preserves_the_original_error(self):
        camera=Mock();camera.hasOpenSession.return_value=False
        def opened(options,done):camera.hasOpenSession.return_value=True;done(None)
        camera.requestOpenSessionWithOptions_completion_.side_effect=opened
        camera.requestCloseSessionWithOptions_completion_.side_effect=lambda options,done:done(object())
        original=ValueError('original operation failed')
        with patch.object(ptp.sys,'platform','darwin'),patch.dict('sys.modules',{'Foundation':Mock()}):
            with self.assertRaises(ValueError) as result:
                with ptp.authorized_session(camera,allow_session=True):raise original
        self.assertIs(result.exception,original)
        self.assertFalse(original.connection_cleanup_completed)
        camera.requestCloseSessionWithOptions_completion_.assert_called_once()

    def test_wrapped_transaction_timeout_does_not_issue_overlapping_close(self):
        for explicit in (False,True):
            camera=Mock();camera.hasOpenSession.return_value=False
            def opened(options,done):camera.hasOpenSession.return_value=True;done(None)
            camera.requestOpenSessionWithOptions_completion_.side_effect=opened
            with self.subTest(explicit=explicit),patch.object(ptp.sys,'platform','darwin'),patch.dict('sys.modules',{'Foundation':Mock()}):
                with self.assertRaisesRegex(RuntimeError,'cleanup incomplete'):
                    with ptp.authorized_session(camera,allow_session=True):
                        try:raise TimeoutError('PTP request pending')
                        except TimeoutError as error:
                            if explicit:raise RuntimeError('cleanup incomplete') from error
                            raise RuntimeError('cleanup incomplete')
            camera.requestOpenSessionWithOptions_completion_.assert_called_once()
            camera.requestCloseSessionWithOptions_completion_.assert_not_called()

    def test_success_error_and_timeout_never_retry(self):
        for mode in ('success','error','timeout','oversize'):
            with self.subTest(mode=mode):
                camera=Mock();camera.hasOpenSession.return_value=True;camera.capabilities.return_value=['ptp']
                callbacks=[]
                def send(command,data,callback):
                    callbacks.append(callback)
                    if mode!='timeout':callback(bytes(33 if mode=='oversize' else 12),bytes(8),
                        object() if mode=='error' else None)
                camera.requestSendPTPCommand_outData_completion_.side_effect=send
                with patch.object(ptp.sys,'platform','darwin'), \
                        patch.dict('sys.modules',{'Foundation':Mock(),'ImageCaptureCore':Mock(ICCameraDeviceCanAcceptPTPCommands='ptp')}), \
                        patch.object(ptp.time,'monotonic',side_effect=[0,6]):
                    if mode=='success':
                        reply=ptp.send(camera,bytes(12));self.assertEqual(len(reply.data),8)
                    else:
                        expected=TimeoutError if mode=='timeout' else ValueError if mode=='oversize' else RuntimeError
                        with self.assertRaises(expected):ptp.send(camera,bytes(12))
                camera.requestSendPTPCommand_outData_completion_.assert_called_once()
                callbacks[0](bytes(12),b'late',None)

    def test_closed_session_and_missing_capability_send_nothing(self):
        for opened,capabilities in ((False,['ptp']),(True,[])):
            camera=Mock();camera.hasOpenSession.return_value=opened;camera.capabilities.return_value=capabilities
            with patch.object(ptp.sys,'platform','darwin'), \
                    patch.dict('sys.modules',{'Foundation':Mock(),'ImageCaptureCore':Mock(ICCameraDeviceCanAcceptPTPCommands='ptp')}):
                with self.assertRaises(RuntimeError):ptp.send(camera,bytes(12))
            camera.requestSendPTPCommand_outData_completion_.assert_not_called()

    def test_invalid_callback_buffers_fail_immediately_and_do_not_escape_callback(self):
        for response,data in ((None,b''),(bytes(12),None),('a'*12,b''),(12,b''),(bytes(12),[])):
            camera=Mock();camera.hasOpenSession.return_value=True;camera.capabilities.return_value=['ptp']
            camera.requestSendPTPCommand_outData_completion_.side_effect=lambda command,out,done:done(response,data,None)
            with self.subTest(response=type(response),data=type(data)), \
                    patch.object(ptp.sys,'platform','darwin'), \
                    patch.dict('sys.modules',{'Foundation':Mock(),'ImageCaptureCore':Mock(ICCameraDeviceCanAcceptPTPCommands='ptp')}), \
                    patch.object(ptp.time,'monotonic',side_effect=[0]) as clock:
                with self.assertRaises(ValueError):ptp.send(camera,bytes(12))
                clock.assert_called_once()
            camera.requestSendPTPCommand_outData_completion_.assert_called_once()

    @unittest.skipUnless(ptp.sys.platform=='darwin','Native framework metadata requires macOS')
    def test_installed_pyobjc_exposes_completion_api_without_opening_devices(self):
        import ImageCaptureCore as capture
        metadata=capture.ICCameraDevice.requestSendPTPCommand_outData_completion_.__metadata__()
        self.assertIn('callable',metadata['arguments'][4])
        self.assertIsInstance(capture.ICCameraDeviceCanAcceptPTPCommands,str)


if __name__=='__main__':unittest.main()
