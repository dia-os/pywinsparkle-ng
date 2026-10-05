"""Restore the pinned official DLL; never silently upgrade the native dependency."""
import hashlib
import argparse
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--official', action='store_true',
                    help='Replace the bundled custom DLL with the unmodified official DLL')
if not parser.parse_args().official:
    parser.error('Pass --official to explicitly replace the patched DLL with the official DLL')

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
(destination / 'native-build.json').unlink(missing_ok=True)
print('Restored verified Windows x64 DLL')
