"""Qualify skills against the actual npm CLI archive; never infer a release from main."""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from catalog import ROOT, write_catalogs
from check import check, skill_files

REPOSITORY = 'spacia-ai/oxidevm-skills'


def inspect_archive(data: bytes, version: str, root: Path = ROOT) -> dict:
    if len(data) > 16 * 1024 * 1024 or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid archive bound or release version')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        members = tar.getmembers()
        if len(members) > 4096:
            raise ValueError('CLI archive has too many entries')

        def document(name):
            matches = [item for item in members if item.name == name]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 4 * 1024 * 1024:
                raise ValueError('Missing, duplicate or unbounded CLI document')
            stream = tar.extractfile(matches[0])
            if stream is None:
                raise ValueError('Missing CLI document bytes')
            result = json.loads(stream.read())
            if not isinstance(result, dict):
                raise ValueError('CLI document must be an object')
            return result

        package = document('package/package.json')
        if package.get('name') != '@oxidevm/cli' or package.get('version') != version or package.get('dependencies', {}).get('@oxidevm/sdk') != version:
            raise ValueError('CLI and SDK version must match the selected release')
        template = document('package/dist/starter.json')
    if 'AGENT_SKILLS.json' not in template:
        raise ValueError('Published CLI has no bundled agent skills yet')
    pin = json.loads(template['AGENT_SKILLS.json'])
    if not isinstance(pin, dict) or pin.get('schemaVersion') != 1 or pin.get('sdkVersion') != version:
        raise ValueError('Bundled skills have the wrong SDK version')
    if pin.get('repository') != 'https://github.com/' + REPOSITORY or not re.fullmatch(r'[a-f0-9]{40}', pin.get('revision', '')):
        raise ValueError('Bundled skills have an unexpected source')
    resources = skill_files(root)
    expected = {name.removeprefix('skills/'): hashlib.sha256(content).hexdigest() for name, content in resources.items()}
    entries = pin.get('files')
    if not isinstance(entries, list) or len(entries) != len(expected) or any(not isinstance(item, dict) or set(item) != {'path', 'sha256'} for item in entries):
        raise ValueError('Bundled skill inventory differs from the canonical source')
    if len({item['path'] for item in entries}) != len(entries) or {item['path']: item['sha256'] for item in entries} != expected:
        raise ValueError('Bundled skill hashes differ from the canonical source')
    for path, content in resources.items():
        for host in ['.agents', '.claude']:
            if template.get(host + '/' + path) != content.decode():
                raise ValueError('Bundled client skill contents differ')
    return pin


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected npm download redirect')


def fetch(path: str, limit: int) -> bytes:
    if not path.startswith('https://registry.npmjs.org/'):
        raise ValueError('Only the public npm registry is a release input')
    with urllib.request.build_opener(NoRedirect).open(path, timeout=90) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('npm response exceeds its bound')
    return data


def public_archive(selected: str) -> tuple[str, bytes]:
    if selected != 'latest' and not re.fullmatch(r'\d+\.\d+\.\d+', selected):
        raise ValueError('Invalid SDK release version')
    sdk = json.loads(fetch('https://registry.npmjs.org/@oxidevm%2fsdk/' + selected, 1024 * 1024))
    version = sdk['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Only stable public SDK versions can synchronize skills')
    cli = json.loads(fetch('https://registry.npmjs.org/@oxidevm%2fcli/' + version, 1024 * 1024))
    integrity = cli['dist']['integrity']
    if not isinstance(integrity, str) or not integrity.startswith('sha512-'):
        raise ValueError('CLI archive requires npm SHA-512 integrity')
    data = fetch(cli['dist']['tarball'], 16 * 1024 * 1024)
    if hashlib.sha512(data).digest() != base64.b64decode(integrity[7:], validate=True):
        raise ValueError('CLI archive integrity mismatch')
    return version, data


def qualify(selected: str, root: Path = ROOT) -> dict:
    version, data = public_archive(selected)
    pin = inspect_archive(data, version, root)
    return {'schemaVersion': 1, 'minimumSDKVersion': '0.0.3', 'sdkVersion': version, 'status': 'qualified',
            'cliArchiveSHA256': hashlib.sha256(data).hexdigest(), 'skillsRevision': pin['revision']}


def require_publishing_job(environment: dict) -> None:
    if environment.get('GITHUB_ACTIONS') != 'true' or environment.get('GITHUB_WORKFLOW_REF') != REPOSITORY + '/.github/workflows/sync-sdk.yml@refs/heads/main' or environment.get('SKILLS_RELEASE_APPROVED') != 'true':
        raise ValueError('Publication requires the protected main publishing job')


def build_bundle(root: Path = ROOT) -> Path:
    check(root)
    version = json.loads((root / 'plugin.json').read_text())['version']
    destination = root / 'dist'; destination.mkdir(exist_ok=True)
    archive = destination / f'oxidevm-skills-{version}.zip'
    names = ['plugin.json', 'compatibility.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json', 'LICENSE', 'NOTICE', *skill_files(root)]
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name in sorted(names):
            info = zipfile.ZipInfo('oxidevm/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, (root / name).read_bytes())
    (destination / 'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    return archive


def gh(arguments: list[str], payload=None):
    result = subprocess.run(['gh', *arguments], input=None if payload is None else json.dumps(payload), capture_output=True, text=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def prepare(selected: str) -> dict:
    evidence = qualify(selected)
    plugin = json.loads((ROOT / 'plugin.json').read_text()); plugin['version'] = evidence['sdkVersion']
    (ROOT / 'plugin.json').write_text(json.dumps(plugin, indent=2) + '\n')
    (ROOT / 'compatibility.json').write_text(json.dumps(evidence, indent=2) + '\n')
    write_catalogs(); check()
    return evidence


def publish() -> None:
    require_publishing_job(dict(os.environ))
    evidence = json.loads((ROOT / 'compatibility.json').read_text())
    if qualify(evidence['sdkVersion']) != evidence or evidence['status'] != 'qualified':
        raise ValueError('Published SDK no longer matches the reviewed skill inputs')
    latest = json.loads(fetch('https://registry.npmjs.org/@oxidevm%2fsdk/latest', 1024 * 1024))
    if latest['version'] != evidence['sdkVersion']:
        raise ValueError('An older skill version cannot replace latest')
    archive = build_bundle(); tag = 'v' + evidence['sdkVersion']
    result = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPOSITORY, '--json', 'isDraft'], capture_output=True, text=True)
    if result.returncode == 0:
        # Compare downloaded bytes before resuming or retaining an existing release.
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            for file in [archive, ROOT / 'dist/SHA256SUMS']:
                downloaded = subprocess.run(['gh', 'release', 'download', tag, '--repo', REPOSITORY, '--pattern', file.name, '--dir', temporary], capture_output=True, text=True)
                if downloaded.returncode == 0:
                    if (Path(temporary) / file.name).read_bytes() != file.read_bytes():
                        raise ValueError('Existing published skill assets are immutable')
                elif not json.loads(result.stdout)['isDraft']:
                    raise ValueError('Published skill release has missing assets')
                else:
                    subprocess.run(['gh', 'release', 'upload', tag, str(file), '--repo', REPOSITORY], check=True)
    else:
        # A transport or authorization failure must not be interpreted as an absent release.
        releases = gh(['api', f'repos/{REPOSITORY}/releases?per_page=100'])
        if any(release['tag_name'] == tag for release in releases):
            raise ValueError('Existing release could not be inspected')
        subprocess.run(['gh', 'release', 'create', tag, str(archive), str(ROOT / 'dist/SHA256SUMS'), '--repo', REPOSITORY, '--target', os.environ['GITHUB_SHA'], '--draft', '--title', f'OxideVM skills {evidence["sdkVersion"]}', '--notes', f'Skills verified against the published OxideVM SDK and CLI {evidence["sdkVersion"]}.'], check=True)
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false', '--latest'], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='latest')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--bundle', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    if args.publish:
        publish()
    elif args.bundle:
        print(build_bundle())
    else:
        print(json.dumps(prepare(args.version) if args.prepare else qualify(args.version), indent=2))
