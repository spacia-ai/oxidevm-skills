import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from catalog import ROOT, write_catalogs
from check import check, skill_files


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'plugin'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '.cache', '__pycache__'), symlinks=True)

    def tearDown(self):
        self.temporary.cleanup()

    def test_catalogs_and_resources_are_consistent(self):
        write_catalogs(self.root)
        first = check(self.root)
        write_catalogs(self.root)
        self.assertEqual(check(self.root), first)
        self.assertEqual(len(first['files']), 6)

    def test_host_version_drift_is_rejected(self):
        write_catalogs(self.root)
        path = self.root / '.claude-plugin/plugin.json'
        plugin = json.loads(path.read_text())
        plugin['version'] = '0.0.1'
        path.write_text(json.dumps(plugin))
        with self.assertRaisesRegex(ValueError, 'metadata drift'):
            check(self.root)

    def test_escaping_symlink_is_rejected(self):
        (self.root / 'skills/oxidevm-sdk/leak.md').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            skill_files(self.root)

    def test_unexpected_executable_is_rejected(self):
        (self.root / 'skills/oxidevm-sdk/install.sh').write_text('exit 0')
        with self.assertRaisesRegex(ValueError, 'Unexpected skill resource'):
            skill_files(self.root)


if __name__ == '__main__':
    unittest.main()
