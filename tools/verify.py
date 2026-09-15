"""Finite exact artifact inventory verification, including hidden files."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 800_000_000


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def inventory_for(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Artifact must be an ordinary directory')
    rows = []
    total = 0
    for base, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs:
            if (Path(base) / name).is_symlink():
                raise ValueError('Artifact directories cannot be links')
        for name in names:
            file = Path(base) / name
            info = file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('Artifact files cannot be links or special files')
            total += info.st_size
            if total > LIMIT or len(rows) >= 20000:
                raise ValueError('Artifact exceeds its finite budget')
            rows.append({'path': file.relative_to(directory).as_posix(), 'bytes': info.st_size, 'sha256': digest(file)})
    return sorted(rows, key=lambda row: row['path'])


def verify(directory, expected):
    seen = set()
    for row in expected:
        name = row['path']
        relative = PurePosixPath(name)
        if not name or relative.is_absolute() or '..' in relative.parts or '\\' in name or str(relative) != name or name in seen:
            raise ValueError('Unsafe/duplicate expected path')
        seen.add(name)
    rows = inventory_for(directory)
    if rows != sorted(expected, key=lambda row: row['path']):
        raise ValueError('Artifact has missing, extra or changed files')
    return {'status': 'PASS', 'files': len(rows), 'bytes': sum(row['bytes'] for row in rows)}


def locked_inputs():
    lock = json.loads((ROOT / 'source-lock.json').read_bytes())
    path = ROOT / 'expected-inventory.json'
    if digest(path) != lock['expectedInventorySha256']:
        raise ValueError('Expected inventory pin changed')
    inventory = json.loads(path.read_bytes())
    if len(inventory['files']) != lock['expectedFiles'] or sum(row['bytes'] for row in inventory['files']) != lock['expectedBytes'] or lock['budgetBytes'] != LIMIT:
        raise ValueError('Expected inventory size mismatch')
    return lock, inventory


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise ValueError('Usage: verify.py ARTIFACT')
    _, expected = locked_inputs()
    print(json.dumps(verify(Path(sys.argv[1]), expected['files'])))
