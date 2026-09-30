# pywinsparkle-ng — Windows x64 fork kit

Targets native Windows AMD64, Python 3.10+, WinSparkle 0.9.4. The Python import remains `from pywinsparkle import pywinsparkle`. Distribution name is `pywinsparkle-ng`; uninstall original `pywinsparkle` before installing this package because both own the same import directory.

This is a prepared replacement tree, not a published GitHub fork. Fork https://github.com/dyer234/pywinsparkle, create a branch, replace its wrapper and packaging with this tree, delete old x86 DLLs/BuildScripts, and commit. Keep this README and upstream license notices. Optional renaming of the GitHub repository does not change imports.

## Install and build

```powershell
py -m pip uninstall pywinsparkle
py -m pip install .
py -m pip install build
py -m build
```

The wheel is `py3-none-win_amd64`, not a universal wheel or CPython-specific extension. It includes only the x64 DLL and its notices. The sdist contains the same DLL.

## Use

```python
from pywinsparkle import pywinsparkle as ws

ws.win_sparkle_set_app_details('My Company', 'My App', '1.0.0')
ws.win_sparkle_set_appcast_url('https://example.com/appcast.xml')
if not ws.win_sparkle_set_eddsa_public_key('YOUR_BASE64_PUBLIC_KEY'):
    raise ValueError('Invalid EdDSA key')
# Register shutdown callbacks appropriate to your GUI before init.
ws.win_sparkle_init()
# From a menu action:
ws.win_sparkle_check_update_with_ui()
# During application shutdown, while Python is still alive:
# ws.win_sparkle_cleanup()
```

Call configuration functions before initialization; follow the bundled official header for lifecycle semantics. Call cleanup before interpreter shutdown. All callbacks may execute on native worker threads: dispatch GUI work to the GUI main thread (e.g. queued Qt signals), and use `reactor.callFromThread` for Twisted work. `can_shutdown` must return an immediate boolean/integer, not a Deferred or asynchronous GUI result. Callback exceptions are logged; integer callbacks return 0 on failure. Passing `None` unregisters a callback. References to retired callback trampolines are retained for the process lifetime to protect callbacks already in flight; avoid continuously re-registering them.

## API changes and fixes

Thirty upstream functions are bound with explicit argument and return types. Existing public function names remain. Numeric `win_sparkle_set_lang(1055)` maps to `win_sparkle_set_langid`; new callers can use `win_sparkle_set_lang('tr')`. Registry path is UTF-8 bytes, application details/build version remain wide strings. C `int` is 32-bit; Windows x64 `time_t` is 64-bit. EdDSA and DSA key setters return an integer validation result. Shutdown permission callback returns `int`; installer callback receives a wide path and returns `int`. Added HTTP headers, skipped/postponed/dismissed callbacks, and custom installer callback. All no-argument functions use empty `argtypes`.

The optional `win_sparkle_set_config_methods` struct API is deliberately not exposed in this first version. All other functions in the supplied 0.9.4 header are covered. WinSparkle 0.9.4 retains deprecated DSA support: existing installed 0.6 clients still need a DSA-signed bridge update. Keep DSA signatures in the appcast while old clients must be supported, add EdDSA signatures for new clients, and migrate the embedded public key. EdDSA signatures and Windows Authenticode serve different purposes.

## Nuitka

The loader uses an absolute package-relative DLL path and does not depend on the current directory or `sys._MEIPASS`. Ensure the native DLL is packaged at `pywinsparkle/libs/x64/WinSparkle.dll` relative to the compiled package location. Do not treat the DLL as an ordinary data file. Automatic DLL discovery must be verified for your Nuitka version; if needed, use a Nuitka user package configuration DLL rule:

```yaml
- module-name: 'pywinsparkle'
  dlls:
    - from_filenames:
        relative_path: 'libs/x64'
        prefixes: ['WinSparkle']
```

Pass that YAML via `--user-package-configuration-file=your-config.yml`. Check the compilation report and run the frozen application on a clean Windows machine, including onefile mode if used. The snippet is a proposed integration rule; a Nuitka build was not run here.

## Dependency maintenance

`tools/winsparkle.json` pins version, URL and SHA-256 of the extracted DLL. `vendor_winsparkle.py` restores only the official x64 DLL after digest verification. The scheduled workflow reports upstream version changes; it deliberately does not publish or silently upgrade binaries. To upgrade, review the new header, archive layout, licenses and release notes; update the manifest with a independently reviewed DLL digest, vendor the dependency, update bindings, and run Windows CI before tagging a release. Build workflow uploads wheel/sdist artifacts; it does not publish to PyPI.

## Verification and limits

Local tests use a fake native library for conversion, callback return values, lifetime, exception handling and unregistration. Windows CI additionally installs the wheel away from the source tree and loads the actual DLL, validating every bound export. Full signed-appcast download/install testing and clean-machine GUI/Nuitka tests are still required on Windows. This kit has not been run on Windows in the preparation environment.

Original wrapper source: https://github.com/dyer234/pywinsparkle
Native dependency: https://github.com/vslavik/winsparkle/releases/tag/v0.9.4
