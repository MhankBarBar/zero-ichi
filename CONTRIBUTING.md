# Contributing

Zero Ichi moves fast. Good contributions keep it stable while making it easier
to operate, extend, and debug.

This guide is for people sending code, docs, or workflow changes.

## Before You Start

- Open an issue first for bigger changes, behavior changes, or new features.
- Keep one pull request focused on one problem.
- If a change affects commands, config, or user-facing text, update docs and
  locales in same PR.

## Local Setup

```bash
git clone https://github.com/MhankBarBar/zero-ichi
cd zero-ichi
uv sync
cp .env.example .env
```

Run bot:

```bash
uv run zero-ichi
```

Interactive first-run setup:

```bash
uv run zero-ichi setup
```

Docs dev server:

```bash
cd docs
bun install
bun run docs:dev
```

## Branching

- Branch from `dev`.
- Use short branch names that say what changed.
- Examples:
  - `fix/addskill-bom`
  - `feat/privacy-controls`
  - `docs/mobile-table-overflow`

## Project Rules

### Commands

- Add commands under `src/commands/<category>/`.
- Follow `Command` base class pattern already used in repo.
- Respect existing permission flags: `owner_only`, `admin_only`,
  `group_only`, `private_only`.
- Reuse shared helpers before adding new mini-frameworks.

### Config Changes

If you add or change runtime config:

1. Update `DEFAULT_CONFIG` in `src/core/runtime_config.py`
2. Update `config.schema.json`
3. Preserve merge/backfill behavior for existing user config
4. Add or update command/docs examples if users need to touch it

### User-Facing Text

If command output changes:

1. Add/update `src/locales/en.json`
2. Add/update `src/locales/id.json`
3. Keep keys parallel across both files

### Docs

Update docs when you change:

- command behavior
- config shape
- workflow/release process
- setup flow
- moderation behavior

Main docs live in `docs/`.

## Validation

Minimum before opening PR:

```bash
uv run ruff format .
uv run ruff check .
```

Run tests relevant to your change.

If you are preparing a merge-ready branch, run full suite too:

```bash
uv run pytest -q
```

Docs changes should also build:

```bash
cd docs
bun run docs:build
```

## Tests Policy

Repo currently ignores `tests/` in Git.

- Keep exploratory tests local.
- If you need permanent test coverage in-repo, discuss it in issue/PR first so
  policy stays deliberate instead of accidental.

## Pull Request Expectations

Good PRs include:

- clear title
- short summary of problem
- short summary of fix
- validation steps you ran
- screenshots or terminal output when UI/docs behavior changed

Bad PRs usually have one of these problems:

- mix refactor and feature work with no separation
- update code but not docs/locales/schema
- add duplicate helper instead of extending shared one
- change behavior without explaining why

## Commit Messages

Use Conventional Commits.

Examples:

```text
fix(ai): handle BOM in skill markdown
feat(config): add rollback history
docs(commands): clarify addskill usage
refactor(core): share prefixed id generator
```

## Release PR Automation

Repo has release PR workflow for `dev -> master`.

- Push to `dev` triggers release PR workflow automatically.
- Job uses `release-pr` environment.
- To require approval before PR creation, configure required reviewers in
  GitHub Settings -> Environments -> `release-pr`.

That gives automatic trigger with explicit approval gate.

## What Usually Needs Extra Care

- command permission logic
- runtime config persistence and schema validation
- WhatsApp message parsing, especially quoted/media messages
- AI flows that edit messages after async work
- docs tables/layout on mobile
- GitHub workflows that can create PRs, push branches, or deploy pages

## Reporting Problems

Open issue with:

- exact command or workflow involved
- steps to reproduce
- expected result
- actual result
- logs, screenshots, or copied error text

Short, concrete reports get fixed faster.
