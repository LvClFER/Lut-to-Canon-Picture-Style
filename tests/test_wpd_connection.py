import ctypes
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch
from camera_install.wpd_connection import WpdConnection


class WpdConnectionTests(unittest.TestCase):
    def test_control_access_does_not_enable_style_data_writes(self):
        from camera_install.wpd_data_phase_reference import COMMON, MTP
        with ExitStack() as stack:
            com, _, setters, _ = self.environment(stack)
            with WpdConnection('fake-device', allow_control=True, com_factory=lambda: com) as connection:
                self.assertEqual(setters.call_args.args[2], 0xc0000000)
                with self.assertRaisesRegex(ValueError, 'writes are disabled'):
                    connection.data({(COMMON, 1001): MTP, (COMMON, 1002): 14,
                        (MTP, 1001): 0x9192, (MTP, 1002): (), (MTP, 1007): 4})
        with self.assertRaises(ValueError):
            WpdConnection('fake-device', allow_control=1)

    def environment(self, stack, *, init=0, opening=0, closing=0):
        com = Mock()
        com.CoInitializeEx.return_value = init
        log = []
        com.CoUninitialize.side_effect = lambda: log.append('uninitialize')
        def method(pointer, index, *types):
            if index == 3:
                return lambda *args: (log.append('open') or opening)
            if index == 8:
                return lambda *args: (log.append('close') or closing)
            raise AssertionError(index)
        prefix = 'camera_install.wpd_connection.api.'
        stack.enter_context(patch(prefix + '_create_instance',
                                 side_effect=[ctypes.c_void_p(1), ctypes.c_void_p(2)]))
        stack.enter_context(patch(prefix + '_method', side_effect=method))
        stack.enter_context(patch(prefix + '_release', side_effect=lambda p: log.append(('release', p.value))))
        setters = stack.enter_context(patch(prefix + '_set_unsigned'))
        name = stack.enter_context(patch(prefix + '_set_string'))
        return com, log, setters, name

    def test_inert_construction_open_close_and_stale_sender_rejection(self):
        with ExitStack() as stack:
            com, log, setters, name = self.environment(stack)
            factory = Mock(return_value=com)
            connection = WpdConnection('fake-device', com_factory=factory)
            factory.assert_not_called()
            with connection:
                sender = connection.commands
                self.assertEqual(log, ['open', ('release', 2)])
                self.assertEqual(name.call_args.args[2], 'Style Studio')
                self.assertEqual(setters.call_args.args[2], 0x80000000)
            self.assertEqual(log, ['open', ('release', 2), 'close', ('release', 1), 'uninitialize'])
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                sender({})
            with self.assertRaisesRegex(RuntimeError, 'single-use'):
                connection.__enter__()

    def test_open_failure_cleans_and_changed_apartment_is_not_borrowed(self):
        for init, opening in ((0, 0x80070005), (0x80010106, 0)):
            with ExitStack() as stack:
                com, log, _, _ = self.environment(stack, init=init, opening=opening)
                with self.assertRaises(OSError):
                    WpdConnection('fake-device', com_factory=lambda: com).__enter__()
                if init:
                    self.assertEqual(log, [])
                    com.CoUninitialize.assert_not_called()
                else:
                    self.assertEqual(log, ['open', ('release', 2), 'close', ('release', 1), 'uninitialize'])

    def test_close_failure_still_releases_and_balances_s_false(self):
        with ExitStack() as stack:
            com, log, setters, _ = self.environment(stack, init=1, closing=0x80004005)
            with self.assertRaisesRegex(RuntimeError, 'cleanup'):
                with WpdConnection('fake-device', allow_write=True, com_factory=lambda: com):
                    self.assertEqual(setters.call_args.args[2], 0xc0000000)
            self.assertEqual(log[-2:], [('release', 1), 'uninitialize'])

    def test_bad_device_identifiers_fail_without_factory_calls(self):
        factory = Mock()
        for value in (None, '', 'fake\0device', 'x' * 32769):
            with self.assertRaises(ValueError):
                WpdConnection(value, com_factory=factory)
        factory.assert_not_called()

    def test_body_failure_retains_actual_connection_cleanup_status(self):
        for closing in (0,0x80004005):
            with self.subTest(closing=closing), ExitStack() as stack:
                com,log,_,_=self.environment(stack,closing=closing)
                with self.assertRaisesRegex(ValueError,'compiler') as error:
                    with WpdConnection('fake-device',com_factory=lambda:com):
                        raise ValueError('compiler')
                self.assertIs(error.exception.connection_cleanup_completed,not closing)
                self.assertEqual(log[-1],'uninitialize')
