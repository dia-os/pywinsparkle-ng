import ctypes
import gc
import unittest
from pywinsparkle import pywinsparkle as ws

class FakeFunction:
    def __call__(self, *args):
        self.args = args
        return 1

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.old = ws._dll
        ws._dll = type('FakeDLL', (), {})()
        for name in ws._SIGNATURES:
            setattr(ws._dll, name, FakeFunction())
    def tearDown(self):
        ws._dll = self.old
    def test_strings_and_legacy_language(self):
        ws.win_sparkle_set_registry_path('Software\\Örnek')
        self.assertEqual(ws._dll.win_sparkle_set_registry_path.args, ('Software\\Örnek'.encode(),))
        ws.win_sparkle_set_lang(1055)
        self.assertEqual(ws._dll.win_sparkle_set_langid.args, (1055,))
        self.assertEqual(ws.win_sparkle_set_eddsa_public_key('abc'), 1)
    def test_callback_result_and_lifetime(self):
        ws.win_sparkle_set_can_shutdown_callback(lambda: True)
        cb = ws._dll.win_sparkle_set_can_shutdown_callback.args[0]
        gc.collect()
        self.assertEqual(cb(), 1)
        ws.win_sparkle_set_can_shutdown_callback(lambda: False)
        self.assertIn(cb, ws._callbacks)
        self.assertEqual(ws._dll.win_sparkle_set_can_shutdown_callback.args[0](), 0)
    def test_callback_exception_denies_shutdown(self):
        def fail(): raise RuntimeError('test')
        ws.win_sparkle_set_can_shutdown_callback(fail)
        with self.assertLogs(ws.__name__, level='ERROR'):
            self.assertEqual(ws._dll.win_sparkle_set_can_shutdown_callback.args[0](), 0)
    def test_unregister_and_installer(self):
        ws.win_sparkle_set_error_callback(None)
        self.assertFalse(ws._dll.win_sparkle_set_error_callback.args[0])
        paths = []
        ws.win_sparkle_set_user_run_installer_callback(lambda path: paths.append(path) or 1)
        self.assertEqual(ws._dll.win_sparkle_set_user_run_installer_callback.args[0]('C:\\setup.exe'), 1)
        self.assertEqual(paths, ['C:\\setup.exe'])
    def test_integer_abi(self):
        self.assertEqual(ws._SIGNATURES['win_sparkle_get_update_check_interval'][0], ctypes.c_int)
        self.assertEqual(ws._SIGNATURES['win_sparkle_get_last_check_time'][0], ctypes.c_int64)

if __name__ == '__main__': unittest.main()
