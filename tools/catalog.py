"""Generate host metadata from the portable plugin identity."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def catalogs(root: Path = ROOT) -> dict[str, dict]:
    plugin = json.loads((root / 'plugin.json').read_text())
    identity = {key: plugin[key] for key in ['name', 'version', 'description']}
    return {
        '.codex-plugin/plugin.json': {**identity, 'skills': './skills/'},
        '.claude-plugin/plugin.json': {**identity, 'author': {'name': 'Spacia B.V.'}, 'homepage': 'https://oxidevm.dev/docs/'},
        '.agents/plugins/marketplace.json': {
            'name': 'oxidevm', 'interface': {'displayName': 'OxideVM'},
            'plugins': [{'name': 'oxidevm', 'source': {'source': 'local', 'path': './'},
                         'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}],
        },
        '.claude-plugin/marketplace.json': {
            'name': 'oxidevm', 'owner': {'name': 'Spacia B.V.'},
            'plugins': [{'name': 'oxidevm', 'description': plugin['description'], 'source': './'}],
        },
    }


def write_catalogs(root: Path = ROOT) -> None:
    for name, value in catalogs(root).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    write_catalogs()
