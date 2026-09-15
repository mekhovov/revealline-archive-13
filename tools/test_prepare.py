"""Tiny local cohorts: no release downloads, game builds or network access."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from prepare import MIN_FREE_BYTES, prepare
from verify import LIMIT, ROOT, digest, locked_inputs, metadata_inventory, verify


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory), *args], stderr=subprocess.DEVNULL, text=True).strip()


def init(directory):
    directory.mkdir()
    git(directory, 'init', '-q')
    git(directory, 'config', 'user.name', 'Archive fixture')
    git(directory, 'config', 'user.email', 'fixture@example.invalid')


# Exercises the real orchestration/subprocess protocol, not ZIP integrity.
# The production workflow separately runs the pinned extractor's ZIP tests.
EXTRACTOR = '''import argparse, json, pathlib, subprocess
p=argparse.ArgumentParser()
for name in ('metadata','output','receipt'): p.add_argument('--'+name,required=True)
a=p.parse_args(); m=pathlib.Path(a.metadata); out=pathlib.Path(a.output)
r=json.loads((m/'release.json').read_bytes())
BEHAVIOR
out.mkdir(); (out/'body.txt').write_text(r['version'])
(out/'manifest.json').write_bytes((m/'manifest.json').read_bytes())
(out/'distribution.zip.sha256').write_bytes((m/'distribution.zip.sha256').read_bytes())
(out/'.xonix-build.json').write_text('{\\n  "tool": "xonix-game-cli",\\n  "formatVersion": 1\\n}\\n')
pathlib.Path(a.receipt).write_text(json.dumps(dict(version=r['version'],gameSourceRevision=r['sourceRevision'],distributionSha256=r['distributionSha256'],manifestSha256=r['manifestSha256'],crcAndHashesVerified=True)))
'''


class CohortTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.source = self.base / 'source'
        self.archive = self.base / 'archive'
        self.output = self.base / 'output'

    def fixture(self, behavior='pass'):
        init(self.source)
        (self.source / 'extractor.py').write_text(EXTRACTOR.replace('BEHAVIOR', behavior))
        git(self.source, 'add', '.')
        git(self.source, 'commit', '-qm', 'local fixture')
        revision = git(self.source, 'rev-parse', 'HEAD')
        init(self.archive)
        (self.archive / 'index.html').write_bytes(b'fixture index')
        releases = []
        for version in ('v0.1.0', 'v0.2.0'):
            git(self.source, 'tag', '-a', version, '-m', 'fixture')
            directory = self.archive / 'metadata' / version
            directory.mkdir(parents=True)
            manifest = {'version': version, 'sourceRevision': revision, 'totalBytes': len(version), 'files': [{'path': 'body.txt', 'bytes': len(version), 'sha256': sha(version.encode())}]}
            manifest_bytes = encoded(manifest)
            record = {'version': version, 'sourceRevision': revision, 'distributionSha256': sha(version.encode()), 'manifestSha256': sha(manifest_bytes)}
            (directory / 'release.json').write_bytes(encoded(record))
            (directory / 'manifest.json').write_bytes(manifest_bytes)
            (directory / 'distribution.zip.sha256').write_text(record['distributionSha256'] + '  distribution.zip\n')
            releases.append({**{key: record[key] for key in ('version', 'sourceRevision', 'distributionSha256')}, 'tagObject': git(self.source, 'rev-parse', 'refs/tags/' + version), 'metadata': {name: digest(directory / name) for name in ('release.json', 'manifest.json', 'distribution.zip.sha256')}})
        self.lock = {'format': 'revealline-archive-originals.v2', 'archiveId': 'fixture', 'toolingCommit': revision, 'extractorPath': 'extractor.py', 'extractorSha256': digest(self.source / 'extractor.py'), 'releases': releases, 'budgetBytes': LIMIT}
        rows = [row for release in releases for row in metadata_inventory(self.archive, release)]
        rows += [{'path': 'index.html', 'bytes': 13, 'sha256': sha(b'fixture index')}, {'path': '.nojekyll', 'bytes': 0, 'sha256': sha(b'')}]
        rows.sort(key=lambda row: row['path'])
        self.expected = {'base': 'https://example.invalid/', 'files': rows}
        (self.archive / 'expected-inventory.json').write_bytes(encoded(self.expected))
        self.lock.update(expectedInventorySha256=digest(self.archive / 'expected-inventory.json'), expectedFiles=len(rows), expectedBytes=sum(row['bytes'] for row in rows))
        self.write_lock()
        git(self.archive, 'add', '.')
        git(self.archive, 'commit', '-qm', 'local metadata fixture')

    def write_lock(self):
        (self.archive / 'source-lock.json').write_bytes(encoded(self.lock))

    def assemble(self):
        with patch('prepare.shutil.disk_usage', return_value=SimpleNamespace(free=MIN_FREE_BYTES)):
            return prepare(self.source, self.output, self.archive)

    def test_two_original_cohorts_and_independent_artifact_reread(self):
        self.fixture()
        result = self.assemble()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual([r['version'] for r in result['releases']], ['v0.1.0', 'v0.2.0'])
        self.assertEqual(result['files'], 12)
        self.assertEqual(verify(self.output / 'artifact', self.expected['files'])['bytes'], result['bytes'])
        for version in ('v0.1.0', 'v0.2.0'):
            self.assertEqual((self.output / 'artifact/releases' / version / 'release.json').read_bytes(), (self.archive / 'metadata' / version / 'release.json').read_bytes())
            self.assertTrue((self.output / ('zip-receipt-' + version + '.json')).is_file())

    def test_capacity_refuses_before_output_or_source_access(self):
        with patch('prepare.shutil.disk_usage', return_value=SimpleNamespace(free=MIN_FREE_BYTES - 1)):
            with self.assertRaisesRegex(ValueError, '3 GiB'):
                prepare(self.source, self.output, self.archive)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_overwritten(self):
        self.fixture()
        self.output.mkdir()
        sentinel = self.output / 'keep'
        sentinel.write_bytes(b'unchanged')
        with self.assertRaises(FileExistsError):
            self.assemble()
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b'unchanged')

    def test_bad_second_metadata_refuses_before_first_extraction(self):
        self.fixture()
        (self.archive / 'metadata/v0.2.0/release.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'metadata bytes changed'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_duplicate_version_and_cohort_inventory_omission_refuse(self):
        self.fixture()
        original = copy.deepcopy(self.lock)
        self.lock['releases'].append(copy.deepcopy(self.lock['releases'][0]))
        self.write_lock()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.assemble()
        self.lock = original
        self.lock['releases'].pop()
        self.write_lock()
        with self.assertRaisesRegex(ValueError, 'Canonical inventory'):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_manifest_source_disagreement_refuses_even_with_rehashed_pin(self):
        self.fixture()
        release = self.lock['releases'][1]
        manifest_path = self.archive / 'metadata/v0.2.0/manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['sourceRevision'] = '0' * 40
        manifest_path.write_bytes(encoded(manifest))
        release['metadata']['manifest.json'] = digest(manifest_path)
        with self.assertRaisesRegex(ValueError, 'manifest identity'):
            metadata_inventory(self.archive, release)

    def test_second_extraction_failure_cannot_emit_combined_success(self):
        self.fixture("if r['version']=='v0.2.0': raise ValueError('fixture second failure')")
        with self.assertRaises(subprocess.CalledProcessError):
            self.assemble()
        self.assertTrue((self.output / 'zip-receipt-v0.1.0.json').is_file())
        self.assertFalse((self.output / 'receipt.json').exists())

    def test_mismatched_extraction_receipt_cannot_emit_combined_success(self):
        self.fixture("r['distributionSha256']='0'*64")
        with self.assertRaisesRegex(ValueError, 'extraction receipt identity'):
            self.assemble()
        self.assertTrue((self.output / 'zip-receipt-v0.1.0.json').is_file())
        self.assertFalse((self.output / 'zip-receipt-v0.2.0.json').exists())
        self.assertFalse((self.output / 'receipt.json').exists())

    def test_tag_identity_changed_before_or_during_extraction_refuses(self):
        self.fixture("if r['version']=='v0.2.0': subprocess.run(['git','-C',str(pathlib.Path(__file__).parent),'tag','-d','v0.1.0'],check=True,stdout=subprocess.DEVNULL)")
        with self.assertRaises(subprocess.CalledProcessError):
            self.assemble()
        self.assertFalse((self.output / 'receipt.json').exists())
        self.output = self.base / 'next-output'
        with self.assertRaises(subprocess.CalledProcessError):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_changed_extracted_body_fails_full_inventory(self):
        self.fixture()
        result = self.assemble()
        body = self.output / 'artifact/releases/v0.2.0/site/body.txt'
        body.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'missing, extra or changed'):
            verify(self.output / 'artifact', self.expected['files'])
        self.assertTrue(result['noHistoricalBuilds'])


class CommittedMetadataTests(unittest.TestCase):
    def test_exact_combined_metadata_and_preserved_original_v054_pins(self):
        lock, inventory = locked_inputs(ROOT)
        self.assertEqual((lock['expectedFiles'], lock['expectedBytes']), (1302, 624421715))
        old = lock['releases'][0]
        self.assertEqual(old['version'], 'v0.54.0')
        self.assertEqual(old['metadata'], {'release.json': 'd487958dfe487643a4afd0b0e238aec7c4b521f469b62fe58d3e6f3122ddd24b', 'manifest.json': 'e691af45b84bdf01025089939d3238e3b8971edb489003b7102c73ef03a835f5', 'distribution.zip.sha256': 'bf8bb4ab070114cfd90748cd3d845f0be58ec24b538b4bba6abd02fcef1600c0'})
        rows = [row for row in inventory['files'] if row['path'].startswith('releases/v0.54.0/')]
        self.assertEqual((len(rows), sum(row['bytes'] for row in rows)), (650, 312209030))


if __name__ == '__main__':
    unittest.main()
