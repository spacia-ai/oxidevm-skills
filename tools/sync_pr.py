"""Open a metadata-only SDK synchronization PR without force-pushing a branch."""
import base64
import json
import subprocess
from catalog import ROOT, catalogs
from sync_sdk import REPOSITORY, gh


def open_pull_request() -> None:
    allowed = {'plugin.json', 'compatibility.json', *catalogs()}
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).splitlines()
    if not set(changed) <= allowed:
        raise ValueError('SDK synchronization cannot change skill instructions or workflow code')
    if not changed:
        print('Skills already match the published SDK.'); return
    version = json.loads((ROOT / 'compatibility.json').read_text())['sdkVersion']
    branch = 'release/sdk-' + version
    main = gh(['api', f'repos/{REPOSITORY}/git/ref/heads/main'])['object']['sha']
    base = gh(['api', f'repos/{REPOSITORY}/git/commits/{main}'])['tree']['sha']
    tree = []
    for name in sorted(changed):
        blob = gh(['api', f'repos/{REPOSITORY}/git/blobs', '--input', '-'], {'encoding': 'base64', 'content': base64.b64encode((ROOT / name).read_bytes()).decode()})
        tree.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    candidate = gh(['api', f'repos/{REPOSITORY}/git/trees', '--input', '-'], {'base_tree': base, 'tree': tree})
    refs = gh(['api', f'repos/{REPOSITORY}/git/matching-refs/heads/{branch}'])
    exact = [ref for ref in refs if ref['ref'] == 'refs/heads/' + branch]
    if exact:
        previous = gh(['api', f'repos/{REPOSITORY}/git/commits/{exact[0]["object"]["sha"]}'])
        if previous['tree']['sha'] != candidate['sha']:
            raise ValueError('Existing synchronization branch changed; review it instead of force-pushing')
    else:
        commit = gh(['api', f'repos/{REPOSITORY}/git/commits', '--input', '-'], {'message': f'Sync skills with SDK {version}', 'tree': candidate['sha'], 'parents': [main]})
        gh(['api', f'repos/{REPOSITORY}/git/refs', '--input', '-'], {'ref': 'refs/heads/' + branch, 'sha': commit['sha']})
    existing = gh(['api', f'repos/{REPOSITORY}/pulls?state=open&head=spacia-ai:{branch}&base=main'])
    if not existing:
        gh(['api', f'repos/{REPOSITORY}/pulls', '--input', '-'], {'title': f'Sync OxideVM skills with SDK {version}', 'head': branch, 'base': 'main', 'body': f'Verified both clients’ bundled skill files against the actual published SDK/CLI {version} archive and npm integrity. This updates version metadata only. Publishing still requires the protected release job.'})
    print('Prepared reviewed synchronization branch ' + branch)


if __name__ == '__main__':
    open_pull_request()
