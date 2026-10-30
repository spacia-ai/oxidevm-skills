# OxideVM skills repository

This public repository owns the canonical OxideVM agent skills. Keep instructions focused on public SDK APIs and the generated starter. Never copy private engine instructions, source, credentials, host paths or release records here.

Keep skill bodies under `skills/`. SDK starter copies are generated from an immutable commit and checked by file hashes. Do not maintain a second handwritten copy. Read the project's installed SDK version and declarations before choosing APIs.

Use Apache-2.0 for first-party instructions and tooling. Preserve LICENSE and NOTICE. Skills do not grant an engine license or authorize publishing, deploying, installing global tools or changing unrelated user settings.

Run `python3 -m unittest discover -s tests` and `python3 tools/check.py` before review.
Keep `CLAUDE.md` as a relative symlink to `AGENTS.md`. Use descriptive branches.

CI, SDK synchronization, and publication run through separate private maintainer
infrastructure. Do not add workflows, publication scripts, credentials, internal
reports, or persistent self-hosted runners to this public repository. Keep local
verification and reproducible packaging tools available. Require owner approval
for releases. Never replace published tags or release assets. Owner commits and
merges use lukasz@spacia.ai.
