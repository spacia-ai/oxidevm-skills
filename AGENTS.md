# OxideVM skills repository

This public repository owns the canonical OxideVM agent skills. Keep instructions focused on public SDK APIs and the generated starter. Never copy private engine instructions, source, credentials, host paths or release records here.

Keep skill bodies under `skills/`. SDK starter copies are generated from an immutable commit and checked by file hashes. Do not maintain a second handwritten copy. Read the project's installed SDK version and declarations before choosing APIs.

Use Apache-2.0 for first-party instructions and tooling. Preserve LICENSE and NOTICE. Skills do not grant an engine license or authorize publishing, deploying, installing global tools or changing unrelated user settings.

Run `python3 -m unittest discover -s tests` and `python3 tools/check.py` before review. Ordinary CI uses self-hosted runners. Publication uses a protected GitHub-hosted job and stays disabled until owner approval. Never replace published tags or release assets.

Keep `CLAUDE.md` as a relative symlink to `AGENTS.md`. Use descriptive branches without agent or provider prefixes.
