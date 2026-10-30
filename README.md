# OxideVM skills

Skills for building browser applications with the [OxideVM SDK](https://oxidevm.dev/docs/) in Codex and Claude Code.

The upcoming SDK/CLI 0.0.4 starter includes these project skills automatically.
The published 0.0.3 starter does not include them. A versioned plugin release
is not available yet.

## New projects

After the starter release, open its generated folder in Codex or Claude Code.
Try:

> Add a revenue chart from the DataFrame result. Keep Python running in Linux.

The project includes SDK integration, starter and debugging skills. They read
your installed SDK version before choosing APIs. No plugin install or separate
skills download is needed for a generated starter.

## Other projects

With current Codex:

```sh
codex plugin marketplace add spacia-ai/oxidevm-skills
codex plugin add oxidevm@oxidevm
```

With Claude Code 2.1.292 or newer:

```sh
claude plugin install oxidevm --marketplace spacia-ai/oxidevm-skills
```

Older Claude Code can use `/plugin marketplace add spacia-ai/oxidevm-skills`
and `/plugin install oxidevm@oxidevm` inside its session. The marketplace and
plugin are both named `oxidevm`.

Codex desktop and local/SSH Claude Code desktop sessions can read the generated
project skills. For Claude Chat or Cowork, use the plugin ZIP from a versioned
GitHub release and the custom-plugin upload option in **Customize → Plugins**.
Uploaded copies need explicit replacement when you update. An agent needs
access to your project; opening the browser demo alone does not grant it.

## Updates

For Codex, run `codex plugin marketplace upgrade oxidevm`, then
`codex plugin add oxidevm@oxidevm`. For Claude Code, run
`claude plugin update oxidevm@oxidevm`. Third-party Claude marketplace
auto-updates are off by default. Enable them under **Marketplaces → OxideVM**
in `/plugin` if you want them. Follow the client's reload message.

Project copies stay matched to their SDK. A newer global plugin checks the
installed SDK declarations; it does not upgrade packages or rewrite files.
The plugin contains no hooks, MCP server, background service or credentials.

## Maintaining releases

Edit canonical instructions under `skills/`, then run:

```sh
python3 tools/catalog.py
python3 -m unittest discover -s tests
python3 tools/check.py
python3 tools/sync_sdk.py --bundle
```

Host manifests are generated from `plugin.json`. SDK maintainers import an
immutable public source commit and hash-check it during every CLI build.
The synchronization workflow verifies the actual npm CLI archive, npm
integrity, matching SDK dependency, and both clients' bundled skill contents.
It prepares a metadata-only release branch and review link, and refuses changed
skill bodies or branch drift. The organization requires a person to open the
PR. After review and merge, a protected GitHub-hosted job publishes the immutable
ZIP. Ordinary checks use a self-hosted runner.

`SDK_SKILLS_SYNC_ENABLED` is disabled during preparation. Enabling it and
approving the protected `public-release` job are separate owner actions. No
npm token or cross-repository write token is required. Published tags and
assets are never replaced. This process tracks released SDK versions, not
unreleased source changes.

For a local packaging preview, run `python3 tools/sync_sdk.py --bundle`.
Its output in `dist/` is not a published release. Publication runs only from
the protected workflow; the local tool rejects an unapproved invocation.

SDK, CLI and skill instructions use Apache-2.0. The OxideVM engine and guest programs retain their separate licenses.
