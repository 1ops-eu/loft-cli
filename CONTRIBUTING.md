# Contributing to loft-cli

Thank you for your interest in contributing to loft-cli. This document covers the local development setup, testing requirements, PR process, and commit conventions.

---

## Prerequisites

- **Python 3.11+**
- **make**
- **git**
- **wireguard-tools** (optional — only needed for tunnel-related tests against a live host)

---

## Local Development Setup

```bash
# Clone the repo
git clone https://github.com/1ops-eu/loft-cli.git
cd loft-cli

# Create a virtualenv and install all packages in editable mode plus dev deps
make dev

# Verify the install
loft-cli --help
loft-cli-agent --help
```

`make dev` installs all three packages (`loft-cli-core`, `loft-cli`, `loft-cli-agent`) in editable mode (`-e`) so local changes take effect immediately without reinstalling.

---

## Running Tests

```bash
# Unit and integration tests (no live host needed)
make test

# Tests requiring local sqlcipher3 (inventory/SQLite)
make test-local

# All tests (unit + integration + local)
make test-all
```

### Smoke Tests (no live host needed)

Smoke tests validate and plan all 48 example specs:

```bash
make smoke
```

This runs `loft-cli validate`, `loft-cli plan`, and `loft-cli docs` on every YAML in `examples/`. They run in CI on every push.

### Goss Integration Tests (requires a live Ubuntu server)

```bash
make test-goss HOST=<ip> PORT=<port> USER=<user>
```

These are optional and not run in CI by default.

---

## Code Quality

```bash
# Lint (ruff + black --check)
make lint

# Auto-format
make fmt
```

CI enforces `ruff` and `black` on every push and PR. Run `make fmt && make lint` before pushing.

---

## Commit Convention

loft-cli uses **Conventional Commits** for automated changelog generation. Commit messages must follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `chore` | Maintenance, dependency updates, tooling |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or updating tests |
| `ci` | CI/CD pipeline changes |

**Examples:**

```
feat(bootstrap): add allow_ports field to firewall block
fix(agent): prevent state file corruption on concurrent apply
docs: add WireGuard setup prerequisites to README
chore: bump mkdocs-material to 9.6
```

**Breaking changes:** Append `!` to the type or add a `BREAKING CHANGE:` footer:

```
feat!: remove deprecated client-mode transport

BREAKING CHANGE: The --mode client flag is removed. Use --mode agent.
```

---

## PR Process

1. **Branch from `main`** using `feature/<short-description>` naming:
   ```bash
   git checkout -b feature/add-allow-ports
   ```

2. **One concern per PR** — keep PRs focused. A bug fix should not include unrelated refactors.

3. **Before opening a PR:**
   ```bash
   make lint && make test && make smoke
   ```
   All three must pass. Fix any failures before pushing.

4. **For new spec kinds or fields** — the CLAUDE.md rules apply:
   - Read the relevant package README before changing anything
   - Update all affected READMEs
   - Add or update an example in `examples/`
   - Add tests

5. **PR title** — use Conventional Commits format: `feat: add allow_ports to bootstrap spec`

---

## Adding a New Spec Kind

New spec kinds follow the registry pattern. Here's the checklist:

1. **Define the Pydantic model** in `packages/core/loft_cli_core/specs/`
2. **Register it** in `packages/client/loft_cli/_builtins.py` (or an addon)
3. **Write the normalizer** — adds a normalizer function to the `NORMALIZER_REGISTRY`
4. **Write the validator** — adds a validator function to the `VALIDATOR_REGISTRY`
5. **Write the planner** — adds a planner function to the `PLANNER_REGISTRY`; generates `Step` objects
6. **Write the step handler(s)** — registers handler functions in `STEP_HANDLER_REGISTRY`
7. **Add KindHooks** if needed — inventory recording, SSH port fallback, key generation
8. **Create an example** in `examples/<kind-name>/` with a spec YAML and `README.md`
9. **Write tests** — spec schema validation, planner output, any edge cases
10. **Update READMEs** — relevant package READMEs and `CLAUDE.md`

---

## Spec Schema Stability Policy

From v1.0 onwards, loft-cli follows these rules for spec schema changes:

### What is stable

- All existing spec fields documented in the reference docs — adding a value that was valid before v1.0 must continue to work
- The `kind` field and top-level structure of every spec kind
- The CLI command names and their required arguments
- The local state paths (`~/.loft-cli/`, `~/.ssh/conf.d/loft-cli/`, `~/.wg/loft-cli/`)
- The agent's state file format (`runtime-state.json`, `desired-state.json`)

### What can change in a minor release (1.x.0)

- Adding new **optional** fields to existing spec kinds (with sensible defaults)
- Adding new spec kinds
- Adding new CLI commands or options
- Deprecating fields (with a `DeprecationWarning` and at least one minor release of overlap)

### What requires a major release (2.0.0)

- Removing or renaming existing spec fields
- Changing the meaning of an existing field
- Removing CLI commands or changing required arguments
- Breaking changes to the agent state file format
- Changing the local state directory structure

### Deprecation process

1. Mark the field as deprecated in the schema (`deprecated=True` in Pydantic `Field`)
2. Emit a `DeprecationWarning` when the field is used
3. Document the migration path in CHANGELOG.md
4. Remove in the next major release

### Agent/client version compatibility

The client and agent must have matching major versions. A v1.x client requires a v1.x agent. The client enforces this at connection time and exits with a clear error if the versions are incompatible.

---

## Release Process

Releases are triggered by Git tags. Only maintainers create releases.

### Step 1 — Verify the branch is ready

```bash
# All tests and smoke tests must pass before tagging
make lint && make test && make smoke
```

Fix any failures before continuing. Do not tag a broken branch.

### Step 2 — Update CHANGELOG.md

```bash
# Generate from Conventional Commits history (requires git-cliff)
make changelog
```

Review the output. Edit manually if any entry is unclear or miscategorised. The changelog entry for the new version should be at the top.

### Step 3 — Bump versions

Bump the version string in **all four** locations — they must be identical:

```
packages/core/pyproject.toml       ← loft-cli-core package version
packages/client/pyproject.toml     ← loft-cli package version
packages/agent/pyproject.toml      ← loft-cli-agent package version
pyproject.toml                     ← root (dev tooling / monorepo marker)
```

`packages/core/loft_cli_core/__init__.py` reads the version dynamically from the installed package metadata — no manual edit needed there.

Also update any version references in documentation:

```
README.md                          ← installation examples, badge, version table
docs/                              ← any version-pinned code blocks or references
```

### Step 4 — Update ROADMAP.md and CLAUDE.md

Mark completed items with `✅` in both files:

- In `ROADMAP.md`: tick off every item delivered in this release under the relevant version heading
- In `CLAUDE.md`: update the "Current Capabilities" table to reflect the new version and any newly completed features

### Step 5 — Commit

```bash
git add -A
git commit -m "chore(release): bump version to X.Y.Z"
```

### Step 6 — Tag and push

```bash
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

Pushing the tag triggers the release pipeline in GitHub Actions.

### Step 7 — What CI does automatically

Once the tag is pushed, GitHub Actions:

- Builds client binaries for Linux (amd64, arm64) and macOS (arm64)
- Builds agent binaries for Linux (amd64, arm64)
- Generates `checksums.txt` (SHA-256 of all binaries)
- Creates a GitHub Release with all assets attached
- Publishes all three packages (`loft-cli-core`, `loft-cli`, `loft-cli-agent`) to PyPI
- Builds and pushes the Docker image to `ghcr.io/1ops-eu/loft-cli`
- Publishes updated docs to GitHub Pages

### Step 8 — Post-release verification

After CI completes (~10 min), verify:

```bash
# PyPI publish
pip install --upgrade loft-cli && loft-cli version

# GitHub Release
gh release view vX.Y.Z

# Docker image
docker pull ghcr.io/1ops-eu/loft-cli:X.Y.Z && \
  docker run --rm ghcr.io/1ops-eu/loft-cli:X.Y.Z version

# Docs site — confirm new version appears at https://1ops-eu.github.io/loft-cli
```

### Summary checklist

```
[ ] make lint && make test && make smoke — all pass
[ ] CHANGELOG.md updated (make changelog + review)
[ ] Version bumped in all 4 pyproject.toml files
[ ] README.md / docs version references updated
[ ] ROADMAP.md — completed items ticked off
[ ] CLAUDE.md — capabilities table updated
[ ] Commit: chore(release): bump version to X.Y.Z
[ ] git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z
[ ] CI passes (binaries, PyPI, Docker, GitHub Pages)
[ ] Post-release: pip install, gh release view, docker pull, docs site
```
