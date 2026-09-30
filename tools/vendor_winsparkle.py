"""Restore the pinned official DLL; never silently upgrade the native dependency."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'tools/winsparkle.json').read_text())
with urlopen(config['url'], timeout=120) as response:
    archive = ZipFile(io.BytesIO(response.read()))
prefix = f"WinSparkle-{config['version']}/"
dll = archive.read(prefix + 'x64/Release/WinSparkle.dll')
if hashlib.sha256(dll).hexdigest() != config['dll_sha256']:
    raise SystemExit('DLL digest mismatch: review upstream release before changing the pin')
destination = root / 'pywinsparkle/libs/x64'
destination.mkdir(parents=True, exist_ok=True)
(destination / 'WinSparkle.dll').write_bytes(dll)
for name in ('COPYING', 'COPYING.expat'):
    (destination / name).write_bytes(archive.read(prefix + name))
print('Restored verified Windows x64 DLL')
