"""Preserve one original GitHub Release ZIP as an immutable canonical archive."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from verify import ROOT, digest, locked_inputs, verify


def run(args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.out.absolute()
    lock, inventory = locked_inputs()
    git = ['git', '-C', str(source)]
    if run([*git, 'rev-parse', 'HEAD']) != lock['toolingCommit'] or run([*git, 'status', '--porcelain', '--untracked-files=no']):
        raise ValueError('Tooling must equal the clean reviewed source commit')
    if run([*git, 'rev-parse', lock['version']]) != lock['tagObject'] or run([*git, 'rev-parse', lock['version'] + '^{commit}']) != lock['sourceRevision']:
        raise ValueError('Original release tag/source identity changed')
    extractor = source / lock['extractorPath']
    if digest(extractor) != lock['extractorSha256']:
        raise ValueError('Reviewed extractor bytes changed')
    metadata = ROOT / 'metadata' / lock['version']
    for name, expected in lock['metadata'].items():
        if digest(metadata / name) != expected:
            raise ValueError('Original metadata bytes changed: ' + name)
    record = json.loads((metadata / 'release.json').read_bytes())
    if record['version'] != lock['version'] or record['sourceRevision'] != lock['sourceRevision'] or record['distributionSha256'] != lock['distributionSha256']:
        raise ValueError('Original release identity changed')
    # A fresh CI workspace owns every output. Existing artifacts are never replaced.
    output.mkdir(parents=True, exist_ok=False)
    artifact = output / 'artifact'
    release = artifact / 'releases' / lock['version']
    release.mkdir(parents=True)
    subprocess.run([sys.executable, str(extractor), '--metadata', str(metadata), '--output', str(release / 'site'), '--receipt', str(output / 'zip-receipt.json')], check=True)
    shutil.copyfile(metadata / 'release.json', release / 'release.json')
    shutil.copyfile(ROOT / 'index.html', artifact / 'index.html')
    (artifact / '.nojekyll').write_bytes(b'')
    result = verify(artifact, inventory['files'])
    result.update({'archiveId': lock['archiveId'], 'version': lock['version'], 'sourceRevision': lock['sourceRevision'], 'tagObject': lock['tagObject'], 'toolingCommit': lock['toolingCommit'], 'archiveCommit': run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']), 'archiveTree': run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD^{tree}']), 'expectedInventorySha256': lock['expectedInventorySha256'], 'originalZipExtraction': json.loads((output / 'zip-receipt.json').read_bytes()), 'noHistoricalBuilds': True})
    with (output / 'receipt.json').open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    shutil.copyfile(ROOT / 'expected-inventory.json', output / 'expected-inventory.json')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
