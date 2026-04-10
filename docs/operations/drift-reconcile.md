# Drift Detection and Reconciliation

After initial apply, servers can drift from their declared spec — packages updated manually, config files changed, services stopped, containers removed. loft-cli provides tools to detect and correct this drift.

---

## How Drift Works

After every successful apply, the agent records the **desired state** to `/var/lib/loft-cli/desired/desired-state.json` on the server. This file contains a hash for each applied resource.

Drift occurs when the **actual state** on the server no longer matches the recorded desired state — for example, when a config file is manually edited or a service is stopped.

---

## Detecting Drift

```bash
loft-cli doctor <spec.yaml> [--env-file PATH]...
```

`doctor` compares the desired plan against the runtime state and reports per-resource drift status. It does not make any changes.

**Example output:**

```
✓  postgres      up-to-date
✗  nginx         drifted  (config file changed)
✓  app-container up-to-date
✗  backup-job    missing  (timer not found)
```

A drift report is also saved to the server at `/var/lib/loft-cli/doctor-result.json`.

---

## Previewing Changes

Before reconciling, use `diff` to see exactly what would change:

```bash
loft-cli diff <spec.yaml> [--env-file PATH]...
```

This shows each step classified as:
- **Unchanged** — matches desired state, will be skipped
- **Changed** — content has changed, will be re-applied
- **Added** — new resource not yet applied
- **Always-run** — runs every time regardless (e.g. health checks)

---

## Reconciling Drift

```bash
loft-cli reconcile <spec.yaml> [--env-file PATH]...
```

`reconcile` runs `doctor` internally and then re-applies only the resources that have drifted. Resources that match their desired state are skipped.

This is equivalent to `loft-cli apply` but scoped to only drifted resources — it will not re-apply everything.

---

## Recommended Workflow

```bash
# 1. Check what's drifted
loft-cli doctor servers/prod-1/services.yaml --env-file servers/prod-1/.env

# 2. Preview what reconcile would do
loft-cli diff servers/prod-1/services.yaml --env-file servers/prod-1/.env

# 3. Apply only the drift
loft-cli reconcile servers/prod-1/services.yaml --env-file servers/prod-1/.env
```

---

## Safe Re-Apply

`loft-cli apply` is always safe to re-run. Hash-based change detection ensures unchanged resources are skipped. If you're not sure whether to use `reconcile` or `apply`, use `apply` — the result is the same.

```bash
# These are equivalent if nothing has changed:
loft-cli apply servers/prod-1/services.yaml --env-file servers/prod-1/.env
loft-cli reconcile servers/prod-1/services.yaml --env-file servers/prod-1/.env
```

The difference is performance: `reconcile` only applies the delta; `apply` processes all steps but skips unchanged ones.
