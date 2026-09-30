"""WinSparkle 0.9.4 bindings for Windows AMD64, Python 3.10+."""
import ctypes
import logging
import platform
from pathlib import Path
import sys

VOID_CALLBACK = ctypes.CFUNCTYPE(None)
INT_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int)
INSTALLER_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_wchar_p)
_dll = None
# Retain every registered trampoline, including replaced callbacks that may be in flight.
_callbacks = []

def _load():
    global _dll
    if _dll is None:
        if sys.platform != "win32" or ctypes.sizeof(ctypes.c_void_p) != 8 or platform.machine().lower() not in ("amd64", "x86_64"):
            raise OSError("WinSparkle requires native Windows x64 Python")
        path = Path(__file__).resolve().parent / "libs" / "x64" / "WinSparkle.dll"
        if not path.is_file():
            raise FileNotFoundError(f"Missing WinSparkle DLL: {path}. Include the DLL at this package-relative path when freezing.")
        _dll = ctypes.CDLL(str(path))  # Upstream exports __cdecl.
        for name, (restype, argtypes) in _SIGNATURES.items():
            function = getattr(_dll, name)
            function.restype = restype
            function.argtypes = argtypes
    return _dll

def _make_function(name, argtypes):
    def call(*args):
        if len(args) != len(argtypes):
            raise TypeError(f"{name} expects {len(argtypes)} arguments")
        # Legacy pywinsparkle accepted a LANGID in set_lang().
        if name == "win_sparkle_set_lang" and isinstance(args[0], int):
            return win_sparkle_set_langid(args[0])
        converted = []
        for value, kind in zip(args, argtypes):
            if kind is ctypes.c_char_p:
                if isinstance(value, str): value = value.encode("utf-8")
                if not isinstance(value, bytes) or b"\0" in value:
                    raise ValueError("Expected str or bytes without embedded NUL")
            elif kind is ctypes.c_wchar_p:
                if not isinstance(value, str) or "\0" in value:
                    raise ValueError("Expected str without embedded NUL")
            elif kind in (VOID_CALLBACK, INT_CALLBACK, INSTALLER_CALLBACK):
                if value is None:
                    value = kind()
                else:
                    if not callable(value): raise TypeError("Expected callable or None")
                    def guarded(*cbargs, callback=value, returns_int=kind is not VOID_CALLBACK):
                        try:
                            result = callback(*cbargs)
                            return int(result) if returns_int else None
                        except BaseException:
                            logging.getLogger(__name__).exception("WinSparkle callback failed")
                            return 0 if returns_int else None
                    value = kind(guarded)
                _callbacks.append(value)
            converted.append(value)
        return getattr(_load(), name)(*converted)
    call.__name__ = name
    call.__doc__ = f"Call {name}; see bundled upstream header for semantics."
    return call

_SIGNATURES = {
    "win_sparkle_init": (None, []),
    "win_sparkle_cleanup": (None, []),
    "win_sparkle_set_lang": (None, [ctypes.c_char_p]),
    "win_sparkle_set_langid": (None, [ctypes.c_ushort]),
    "win_sparkle_set_appcast_url": (None, [ctypes.c_char_p]),
    "win_sparkle_set_dsa_pub_pem": (ctypes.c_int, [ctypes.c_char_p]),
    "win_sparkle_set_eddsa_public_key": (ctypes.c_int, [ctypes.c_char_p]),
    "win_sparkle_set_app_details": (None, [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p]),
    "win_sparkle_set_app_build_version": (None, [ctypes.c_wchar_p]),
    "win_sparkle_set_http_header": (None, [ctypes.c_char_p, ctypes.c_char_p]),
    "win_sparkle_clear_http_headers": (None, []),
    "win_sparkle_set_registry_path": (None, [ctypes.c_char_p]),
    "win_sparkle_set_automatic_check_for_updates": (None, [ctypes.c_int]),
    "win_sparkle_get_automatic_check_for_updates": (ctypes.c_int, []),
    "win_sparkle_set_update_check_interval": (None, [ctypes.c_int]),
    "win_sparkle_get_update_check_interval": (ctypes.c_int, []),
    "win_sparkle_get_last_check_time": (ctypes.c_int64, []),
    "win_sparkle_set_error_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_can_shutdown_callback": (None, [INT_CALLBACK]),
    "win_sparkle_set_shutdown_request_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_did_find_update_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_did_not_find_update_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_update_cancelled_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_update_skipped_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_update_postponed_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_update_dismissed_callback": (None, [VOID_CALLBACK]),
    "win_sparkle_set_user_run_installer_callback": (None, [INSTALLER_CALLBACK]),
    "win_sparkle_check_update_with_ui": (None, []),
    "win_sparkle_check_update_with_ui_and_install": (None, []),
    "win_sparkle_check_update_without_ui": (None, []),
}

for _name, (_, _types) in _SIGNATURES.items():
    globals()[_name] = _make_function(_name, _types)

__all__ = list(_SIGNATURES)
