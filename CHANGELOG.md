# Changelog

All notable changes to loft-cli are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
loft-cli uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.11.0] - 2026-03-15

### Features

- **multi-host**: Sequential apply across selected hosts (`fleet_apply`)
- **multi-host**: Aggregated drift detection across host groups (`fleet_doctor`)
- **multi-host**: Inventory selectors (`role=worker`, `env=staging`, etc.)
- **ci**: Restored green build across all workflows after v0.10 integration

---

## [0.10.0] - 2025-12-01

### Features

- **multi-host**: Multi-host inventory with attribute selectors
- **multi-host**: `kind: fleet_apply` — sequential apply across selected hosts
- **multi-host**: `kind: fleet_doctor` — aggregated drift validation across a fleet

---

## [0.9.0] - 2025-09-15

### Features

- **blueprints**: `kind: blueprint` — reusable composition primitives
- **blueprints**: Include semantics (local and repo-relative)
- **blueprints**: Parameterization with defaults

---

## [0.8.0] - 2025-07-01

### Features

- **catalog**: Catalog registry (8th open registry) with `CatalogEntry`, `StepTemplate`, `OutputTemplate` models
- **catalog**: `loft-cli catalog list|show|export` CLI commands
- **catalog**: Condition DSL for step templates (field presence, equality, boolean)
- **catalog**: Service output declarations (connection params, paths, URLs) per kind
- **catalog**: Addon-registrable catalog entries
- **schema**: Pydantic `Field(description=...)` enrichment on all ~70 spec schema fields

---

## [0.7.0] - 2025-05-01

### Features

- **compose**: `post_deploy` steps on `compose_project`: `shell`, `container_exec`, `http_request`
- **compose**: `project.files` — plain file uploads with per-entry `mode` and `owner`
- **compose**: Compose rebuild detection / `rebuild: true`
- **bootstrap**: `firewall.allow_ports` — declarative additional port openings
- **package**: `kind: package` — declarative apt/apk package installation
- **cli**: `loft-cli logs <host> <service>` — stream container logs without SSH

---

## [0.6.4] - 2025-02-15

### Bug Fixes

- **agent**: Restore idempotency on `ensure_goss_dir` for test 14
- **agent**: Fix chown in `ensure_goss_dir` to preserve snapshot integrity

---

## [0.6.3] - 2025-01-20

### Features

- **wireguard**: SSH-over-tunnel safety gate — verifies SSH through VPN before locking SSH to tunnel-only
- **wireguard**: `loft-cli tunnel up|down|status` — first-class WireGuard tunnel management
- **wireguard**: Per-host client-side interface naming (`wg-{host}`) — multiple tunnels coexist
- **wireguard**: SSH config uses VPN IP when WireGuard is active
- **cli**: `loft-cli remove <host>` — clean lifecycle endpoint for decommissioned machines

---

## [0.6.2] - 2024-12-01

### Bug Fixes

- **bootstrap**: Fix SSH socket detection on Ubuntu 24.04+ (socket-activated sshd)
- **goss**: Cross-distro SSH enabled check via command fallback chain

---

## [0.6.1] - 2024-11-15

### Bug Fixes

- **postgres**: Fix `postgres_ensure` idempotency on re-apply when extensions already exist
- **agent**: Improve mutation lock release on apply failure

---

## [0.6.0] - 2024-11-01

### Features

- **kinds**: `kind: systemd_unit` — host-native systemd services with optional logrotate
- **kinds**: `kind: systemd_timer` — scheduled execution via systemd timers
- **kinds**: `kind: backup_job` — backup operations with retention and scheduling
- **kinds**: `kind: http_check` — GET-only HTTP readiness probe with retry/backoff
- **kinds**: `kind: postgres_ensure` — ensure PostgreSQL users, databases, extensions, grants
- **cli**: `loft-cli rotate-secret` — secret rotation as a day-2 operation

---

## [0.5.1] - 2024-09-15

### Bug Fixes

- **policy**: Fix HMAC token validation for approval tokens with non-ASCII step IDs
- **stack**: Fix topological sort stability with large resource graphs

---

## [0.5.0] - 2024-09-01

### Features

- **reconcile**: `loft-cli doctor` — detect drift between desired and actual state
- **reconcile**: `loft-cli reconcile` — re-apply only drifted resources
- **policy**: Policy engine: `policy.yaml` with `auto_apply`, `require_approval`, `deny` actions
- **policy**: HMAC-SHA256 approval tokens with configurable TTL
- **kinds**: `kind: stack` — group related resources into a deployable application boundary
- **kinds**: Stack-aware dependency-ordered execution (topological sort with circular dep detection)
- **env**: Overlay / env-file layering — repeatable `--env-file` with explicit precedence
- **registry**: Addon registry + discovery via `entry_points` (7 open registries)
- **monorepo**: Three-package monorepo split: `loft-cli-core`, `loft-cli`, `loft-cli-agent`

---

## [0.3.0] - 2024-06-01

### Features

- **agent**: `loft-cli-agent` binary — server-side executor with local plan execution
- **agent**: Transport protocol abstraction (`AgentTransport`, `FabricTransport`)
- **agent**: Server-side state tracking (`runtime-state.json`)
- **agent**: Mutation locking via `fcntl.flock`
- **kinds**: `kind: file_template` — render managed configuration files from Jinja2 templates
- **kinds**: `kind: compose_project` — manage Docker Compose projects

---

## [0.2.0] - 2024-04-01

### Features

- **tests**: Smoke test suite (45 parametrized tests across 15 example specs)
- **ci**: Linux ARM64 binary support
- **ci**: macOS Intel + Apple Silicon split
- **ci**: PyPI publish workflow
- **ci**: `ruff` + `black` CI enforcement
- **schema**: Pydantic `extra='forbid'` on all spec models
- **kinds**: Nginx service kind — native Nginx support under `kind: service`

---

## [0.1.0] - 2024-02-01

### Features

- **bootstrap**: Bootstrap spec — harden fresh Debian/Ubuntu servers
- **service**: PostgreSQL, Docker, container service kinds
- **inventory**: Local SQLite inventory with full historization
- **safety**: SSH lockout prevention gate
- **safety**: Goss server verification after bootstrap
- **cli**: Four-step workflow: `validate`, `plan`, `docs`, `apply`
- **distribution**: `pip install loft-cli` via PyPI
- **distribution**: Standalone binaries for Linux (amd64/arm64) and macOS
- **distribution**: Docker image (`ghcr.io/1ops-eu/loft-cli`)
