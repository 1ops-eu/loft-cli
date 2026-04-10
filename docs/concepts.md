# Concepts

This page explains the key ideas behind loft-cli: the Layer 1 model, the spec pipeline, the agent architecture, and the safety guarantees.

---

## Layer 1: Infrastructure Compiler

loft-cli is **Layer 1**. It makes VMs ready and usable:

- Bootstrap and harden fresh servers
- Install services (PostgreSQL, Nginx, Docker)
- Deploy containers and Compose stacks
- Manage configuration files
- Detect drift and reconcile state
- Verify the server matches the spec

**loft-cli does not do Layer 2.** Application-level orchestration — configuring SaaS products, importing workflows, seeding databases with business data, wiring services together via API calls — belongs in a separate orchestration layer.

The boundary: if the outcome depends only on OS/infrastructure state, it's loft-cli. If it depends on application runtime state, it's not.

---

## The Pipeline

Every loft-cli operation flows through the same six-phase pipeline:

```
YAML Spec
  └─ Parse       ← registry lookup: kind → model class
       └─ Validate   ← kind-specific semantic checks
            └─ Normalize  ← resolve paths, keys, secrets
                 └─ Plan       ← generate ordered list of Steps
                      ├─ Docs       ← render Markdown runbook
                      ├─ Diff       ← compare plan vs. runtime state
                      └─ Apply      ← execute steps via agent
```

**Plan is the single source of truth.** Both `docs` and `apply` are generated from the same `Plan` object. What you review in `loft-cli plan` is exactly what `loft-cli apply` executes.

### Phase 1: Parse

Reads the YAML file, resolves `${VAR}` references via the environment + `.env` files, and hydrates a typed Pydantic model (e.g. `BootstrapSpec`). Unresolved variables in strict mode are fatal — you get the exact field path.

### Phase 2: Validate

Kind-specific semantic validation: SSH port in valid range, WireGuard config complete, containers require Docker enabled, password auth disable requires at least one pubkey. Returns errors (fatal) and warnings (informational).

### Phase 3: Normalize

Resolves everything the planner needs: relative paths, SSH key file contents, WireGuard key derivation, database secrets from env, local filesystem paths. After normalization, plan generation is pure and deterministic — no further I/O.

### Phase 4: Plan

Generates an ordered list of `Step` objects. Each step carries:

| Field | Purpose |
|---|---|
| `scope` | `REMOTE` (SSH), `LOCAL` (this machine), or `VERIFY` |
| `kind` | Dispatch key — `ssh_command`, `gate`, `local_file_write`, etc. |
| `command` | Shell command string |
| `depends_on` | Step indices that must succeed first |
| `gate` | If `true`, failure aborts the entire plan |

The planner embeds file contents directly into steps so the Plan is fully self-contained and reproducible.

### Phase 5: Execute (via Agent)

Since v0.3, all execution goes through the `loft-cli-agent` binary on the target server:

1. Client connects via SSH, uploads the agent binary + serialized plan
2. Client invokes `loft-cli-agent apply` on the server
3. Agent executes all steps locally (no SSH round-trips per command)
4. Client retrieves the result

This means SSH restarts during bootstrap are a non-event — the agent continues operating locally.

### Phase 6: Record

After execution: inventory is updated (SQLite with full historization), a run log is written to `~/.loft-cli/runs/`, and the SSH session is closed.

---

## The Registry System

loft-cli uses seven open registries to dispatch by spec kind. This means new kinds and step types can be added by external addons without modifying core source files.

| Registry | Maps |
|---|---|
| `SPEC_REGISTRY` | `kind` → Pydantic model class |
| `PLANNER_REGISTRY` | `kind` → plan-builder function |
| `NORMALIZER_REGISTRY` | `kind` → normalizer function |
| `VALIDATOR_REGISTRY` | `kind` → validator function |
| `STEP_HANDLER_REGISTRY` | `step.kind` → executor handler |
| `HOOKS_REGISTRY` | `kind` → lifecycle hooks |
| `RESOLVER_REGISTRY` | `prefix` → value resolver |

External addons register via Python `entry_points`:

```toml
# addon's pyproject.toml
[project.entry-points."loft_cli.addons"]
my_addon = "my_addon:register"
```

---

## SSH Lockout Prevention

The most important safety property of the bootstrap plan: **steps that would lock you out of your server never execute unless the admin login gate passes first.**

```
Step 10: [GATE] verify_admin_login_on_new_port
Step 11: disable_root_login         (depends_on: [10])
Step 12: disable_password_auth      (depends_on: [10])
```

If the gate fails, steps 11 and 12 are skipped. You keep root access and the server remains reachable.

There are three gates in a full bootstrap with WireGuard:

1. **Gate 1** — verify admin login with key auth before changing the SSH port
2. **Gate 2** — verify admin login on the new port before disabling root/password auth
3. **Gate 3** (WireGuard only) — verify SSH connectivity through the VPN tunnel before deleting the open SSH rule

---

## Idempotency and Drift Detection

loft-cli is designed to be safe to re-run at any time:

- **Hash-based change detection** — the agent compares the hash of desired state against recorded runtime state. Unchanged resources are skipped.
- **`loft-cli doctor`** — compares the desired spec against actual server state and reports drift without making changes.
- **`loft-cli reconcile`** — re-applies only the resources that have drifted.

---

## Policy Engine

The policy engine controls which plan steps execute automatically, which require explicit approval, and which are denied. It is **inert by default** — no `policy.yaml` means no restrictions.

```yaml
# /etc/loft-cli/policy.yaml on the server
version: "1"
default_action: auto_apply

rules:
  - name: deny-root-commands
    match_id: "run_as_root_*"
    action: deny

  - name: approve-schema-migrations
    match_tags: [schema_migration]
    action: require_approval
```

Approval tokens are HMAC-SHA256 signed, time-limited, and scoped to a specific server. Generate one with `loft-cli rotate-secret --generate-approval-token`.

---

## Multi-Document Specs

A single YAML file can contain multiple specs separated by `---`. All documents are processed in order using the same env files:

```yaml
kind: postgres_ensure
# ... database declarations
---
kind: compose_project
# ... Compose stack
```

This lets you describe a complete application deployment in a single file.

---

## Three-Package Monorepo

The codebase is split into three independent packages:

| Package | Purpose |
|---|---|
| `loft-cli-core` | Shared models, spec schemas, registry infrastructure, policy engine |
| `loft-cli` | Client CLI, compiler pipeline, transports, local state |
| `loft-cli-agent` | Server-side executor, state management, mutation locking |

Import boundaries are strict: the agent may not import from the client; the client may not import from the agent. Both import from core.

The agent binary is minimal — it contains only `loft-cli-core` and `loft-cli-agent` code (no Fabric, no sqlcipher, no paramiko). This keeps the binary small and the attack surface on servers minimal.
