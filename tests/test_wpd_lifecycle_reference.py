import unittest
from camera_install.wpd_lifecycle_reference import close_registered_device


class LifecycleTests(unittest.TestCase):
    def fake(self, fail=None):
        calls=[]
        class Device:
            def close(self):
                calls.append('close')
                return 0x80004005 if fail=='close' else 0
            def release(self):
                calls.append('release')
                if fail=='release': raise RuntimeError('release')
        class Table:
            def get(self,cookie):
                calls.append(('get',cookie))
                if fail=='get': raise RuntimeError('get')
                return Device()
            def revoke(self,cookie):
                calls.append(('revoke',cookie))
                if fail=='revoke': raise RuntimeError('revoke')
                return 0
        return Table(),calls

    def test_success_order(self):
        table,calls=self.fake()
        self.assertIsNone(close_registered_device(table,7))
        self.assertEqual(calls,[('get',7),'close',('revoke',7),'release'])

    def test_all_failures_attempt_remaining_cleanup_once(self):
        for failure in ('get','close','revoke','release'):
            table,calls=self.fake(failure)
            with self.assertRaises(RuntimeError):
                close_registered_device(table,7)
            expected=[('get',7),('revoke',7)] if failure=='get' else [('get',7),'close',('revoke',7),'release']
            self.assertEqual(calls,expected)

    def test_preflight_rejects_invalid_cookie(self):
        for cookie in (0,-1,True,0x100000000,'7'):
            table,calls=self.fake()
            with self.assertRaises(ValueError):
                close_registered_device(table,cookie)
            self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
