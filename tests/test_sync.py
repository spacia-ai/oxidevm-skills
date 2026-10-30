import hashlib
import io
import json
import sys
import tarfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check import skill_files
from sync_sdk import inspect_archive, require_publishing_job, build_bundle, public_archive
from sync_pr import prepare_review_branch


def archive(version='0.0.4', tamper=False):
    resources = skill_files()
    files = {name.removeprefix('skills/'): hashlib.sha256(data).hexdigest() for name, data in resources.items()}
    pin = {'schemaVersion': 1, 'repository': 'https://github.com/spacia-ai/oxidevm-skills', 'revision': 'a' * 40,
           'skillsVersion': version, 'sdkVersion': version, 'files': [{'path': name, 'sha256': sha} for name, sha in files.items()]}
    template = {'AGENT_SKILLS.json': json.dumps(pin)}
    for name, data in resources.items():
        for host in ['.agents', '.claude']:
            template[host + '/' + name] = data.decode()
    if tamper:
        template['.claude/skills/oxidevm-sdk/SKILL.md'] += '\nchanged'
    entries = {'package/package.json': json.dumps({'name': '@oxidevm/cli', 'version': version, 'dependencies': {'@oxidevm/sdk': version}}),
               'package/dist/starter.json': json.dumps(template)}
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as tar:
        for name, content in entries.items():
            data = content.encode(); info = tarfile.TarInfo(name); info.size = len(data); tar.addfile(info, io.BytesIO(data))
    return output.getvalue()


class SyncTests(unittest.TestCase):
    def test_actual_archive_binds_both_clients_and_sdk_version(self):
        self.assertEqual(inspect_archive(archive(), '0.0.4')['sdkVersion'], '0.0.4')

    def test_changed_client_copy_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'contents'):
            inspect_archive(archive(tamper=True), '0.0.4')

    def test_wrong_release_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'version'):
            inspect_archive(archive(), '0.0.5')

    def test_bundle_bytes_are_reproducible(self):
        first = build_bundle().read_bytes()
        self.assertEqual(first, build_bundle().read_bytes())

    def test_registry_integrity_mismatch_is_rejected(self):
        metadata = json.dumps({'version': '0.0.4', 'dist': {'integrity': 'sha512-' + 'A' * 88, 'tarball': 'https://registry.npmjs.org/cli.tgz'}}).encode()
        with patch('sync_sdk.fetch', side_effect=[metadata, metadata, b'corrupt']):
            with self.assertRaisesRegex(ValueError, 'integrity'):
                public_archive('0.0.4')

    def test_sync_refuses_instruction_changes(self):
        with patch('sync_pr.subprocess.check_output', return_value='skills/oxidevm-sdk/SKILL.md\n'):
            with self.assertRaisesRegex(ValueError, 'cannot change'):
                prepare_review_branch()

    def test_publication_requires_the_protected_main_job(self):
        with self.assertRaisesRegex(ValueError, 'protected'):
            require_publishing_job({})
        with self.assertRaisesRegex(ValueError, 'protected'):
            require_publishing_job({'GITHUB_ACTIONS': 'true', 'GITHUB_WORKFLOW_REF': 'spacia-ai/oxidevm-skills/.github/workflows/sync-sdk.yml@refs/heads/feature'})


if __name__ == '__main__':
    unittest.main()
