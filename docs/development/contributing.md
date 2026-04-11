# Contributing

Canonical guide lives in root repo:

- [`CONTRIBUTING.md`](https://github.com/MhankBarBar/zero-ichi/blob/master/CONTRIBUTING.md)

Use that file as source of truth. This page stays short on purpose so docs and
repo guide do not drift.

## Short Version

1. Branch from `dev`
2. Keep PR focused on one change
3. Update docs/locales/schema when behavior changes
4. Run validation before PR:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest -q
```

Docs changes should also build:

```bash
cd docs
bun run docs:build
```

## Release PR Automation

- Push to `dev` triggers release PR workflow automatically
- Workflow uses `release-pr` environment
- Add required reviewers on that environment if you want approval before PR
  creation

## Before Opening PR

- explain problem
- explain fix
- list checks you ran
- include screenshots when UI/docs changed

For command, config, workflow, and architecture rules, read root
`CONTRIBUTING.md`.
