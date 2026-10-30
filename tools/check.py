"""Check the distributable skill closure without running an agent or network request."""
import hashlib
import json
import re
from pathlib import Path
from catalog import ROOT, catalogs

SKILLS = ('oxidevm-sdk', 'oxidevm-starter', 'oxidevm-debugging')


def skill_files(root: Path = ROOT) -> dict[str, bytes]:
    result = {}
    for path in sorted((root / 'skills').rglob('*')):
        if path.is_symlink():
            raise ValueError('Skill resources must be regular files')
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if not re.fullmatch(r'skills/[a-z0-9-]+/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.(?:md|yaml)', name):
            raise ValueError('Unexpected skill resource path')
        data = path.read_bytes()
        if len(data) > 64 * 1024:
            raise ValueError('Skill resource exceeds 64 KiB')
        text = data.decode('utf-8')
        if any(value in text for value in ['/home/deploy/', '/home/lukasz/', 'PRIVATE KEY-----']):
            raise ValueError('Private material in skill resource')
        result[name] = data
    if set(path.name for path in (root / 'skills').iterdir()) != set(SKILLS):
        raise ValueError('Unexpected skill inventory')
    for name in SKILLS:
        text = result[f'skills/{name}/SKILL.md'].decode()
        if not text.startswith(f'---\nname: {name}\ndescription: ') or '\nlicense: Apache-2.0\n---\n' not in text:
            raise ValueError('Missing skill identity, description or license')
        if f'skills/{name}/agents/openai.yaml' not in result:
            raise ValueError('Missing Codex presentation metadata')
    return result


def check(root: Path = ROOT) -> dict:
    plugin = json.loads((root / 'plugin.json').read_text())
    compatibility = json.loads((root / 'compatibility.json').read_text())
    if plugin['name'] != 'oxidevm' or not re.fullmatch(r'0\.[0-9]+\.[0-9]+', plugin['version']):
        raise ValueError('Invalid plugin identity')
    if compatibility['sdkVersion'] != plugin['version'] or compatibility['schemaVersion'] != 1:
        raise ValueError('Plugin and SDK release versions differ')
    for path, expected in catalogs(root).items():
        if json.loads((root / path).read_text()) != expected:
            raise ValueError(f'Generated host metadata drift: {path}')
    if not (root / 'CLAUDE.md').is_symlink() or (root / 'CLAUDE.md').readlink().as_posix() != 'AGENTS.md':
        raise ValueError('CLAUDE.md must point to AGENTS.md')
    files = skill_files(root)
    return {'version': plugin['version'], 'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
