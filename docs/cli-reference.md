# CLI Reference

All loft-cli commands accept `--help` for usage details.

---

## Global Options

All commands that load specs support:

| Option | Description |
|---|---|
| `--env-file PATH` | Load `KEY=VALUE` pairs from a `.env` file. Repeatable — later files override earlier ones. Shell environment variables always take precedence. |
| `--passthrough` | Leave unresolved `${VAR}` references unchanged instead of erroring. Useful for generating docs or plans from specs with variables you don't want to resolve yet. |

---

## Core Workflow

### `loft-cli validate`

Check a spec file for errors without connecting to any server.

```bash
loft-cli validate <spec.yaml> [--env-file PATH]...
```

Runs the Parse → Validate phases. Reports errors (fatal) and warnings (informational) with exact field paths. Safe to run at any time.

---

### `loft-cli plan`

Generate and display the execution plan.

```bash
loft-cli plan <spec.yaml> [--env-file PATH]...
```

Runs through Parse → Validate → Normalize → Plan and prints the ordered list of steps. No connection to the server is made. What you see here is exactly what `apply` will execute.

---

### `loft-cli docs`

Generate a human-readable Markdown ops guide from the plan.

```bash
loft-cli docs <spec.yaml> [-o OUTPUT_FILE] [--mode guide|commands] [--env-file PATH]...
```

| Option | Description |
|---|---|
| `-o FILE` | Write output to a file (default: stdout) |
| `--mode guide` | Full narrative guide with context (default) |
| `--mode commands` | Commands-only cheatsheet |

The generated Markdown is suitable for a team wiki or runbook.

---

### `loft-cli diff`

Show what would change on the server compared to its current runtime state.

```bash
loft-cli diff <spec.yaml> [--env-file PATH]...
```

Compares the desired plan against the agent's recorded runtime state. Steps are classified as:
- **Added** — new resource not yet applied
- **Changed** — resource exists but content has changed
- **Unchanged** — resource matches desired state (will be skipped)
- **Always-run** — step runs regardless (e.g. health checks)

Requires the agent to be installed and reachable on the target host.

---

### `loft-cli apply`

Execute the plan on the target server.

```bash
loft-cli apply <spec.yaml> [--dry-run] [--mode auto|agent|client] [--approval-token TOKEN] [--env-file PATH]...
```

| Option | Description |
|---|---|
| `--dry-run` | Print the plan without executing |
| `--mode auto` | Auto-detect agent vs. legacy client mode (default) |
| `--mode agent` | Force agent mode |
| `--mode client` | Force legacy Fabric client mode (deprecated) |
| `--approval-token TOKEN` | Provide a policy approval token for `require_approval` steps |

Apply is idempotent — re-running skips resources that already match the desired state.

---

## Drift Management

### `loft-cli doctor`

Detect drift between the desired spec and the server's actual state.

```bash
loft-cli doctor <spec.yaml> [--env-file PATH]...
```

Reports per-resource drift status without making any changes. Use this to audit servers between planned applies.

---

### `loft-cli reconcile`

Re-apply only the resources that have drifted from the desired spec.

```bash
loft-cli reconcile <spec.yaml> [--env-file PATH]...
```

Runs `doctor` internally and then applies only the delta. Resources that match their desired state are skipped.

---

## Inventory

### `loft-cli inventory list`

List all servers in the local inventory.

```bash
loft-cli inventory list
```

---

### `loft-cli inventory show`

Show full details for a specific server.

```bash
loft-cli inventory show <server-id>
```

---

## WireGuard Tunnel

### `loft-cli tunnel up`

Bring up the WireGuard tunnel for a host.

```bash
loft-cli tunnel up <host>
```

Creates a `wg-<host>` interface locally using the key material stored under `~/.wg/loft-cli/<host>/`. Requires `wireguard-tools` and passwordless `sudo` for `wg-quick`.

---

### `loft-cli tunnel down`

Tear down the WireGuard tunnel for a host.

```bash
loft-cli tunnel down <host>
```

Removes the `wg-<host>` interface. The server's WireGuard interface remains active.

---

### `loft-cli tunnel status`

List all managed hosts with their WireGuard state.

```bash
loft-cli tunnel status
```

Shows which hosts have WireGuard configured and whether the local interface is currently active.

---

## Maintenance

### `loft-cli version`

Print the client version, and optionally the agent version on a remote host.

```bash
loft-cli version [--host HOST]
```

---

### `loft-cli update`

Self-update the client binary from GitHub Releases.

```bash
loft-cli update
```

Downloads and replaces the current binary. Requires the binary to be installed (not pip-installed).

---

### `loft-cli agent-update`

Update the `loft-cli-agent` binary on a remote host.

```bash
loft-cli agent-update <host>
```

Downloads the latest agent binary from GitHub Releases and replaces the installed agent on the server.

---

### `loft-cli rotate-secret`

Rotate a named secret and re-apply the spec.

```bash
loft-cli rotate-secret <spec.yaml> --secret NAME [--env-file PATH]...
```

Generates a new value for the named secret, updates the server, and records the rotation in the inventory.

---

### `loft-cli remove`

Remove all local state for a host (SSH config entry, WireGuard keys, inventory record).

```bash
loft-cli remove <host> [--force]
```

!!! warning
    This only removes **local** state. It does not decommission the server itself.

---

### `loft-cli inspect run`

Inspect the details of a past run.

```bash
loft-cli inspect run <run-id>
```

Reads from `~/.loft-cli/runs/<run-id>.json` and displays per-step timing, status, and output.

---

## WireGuard Client Prerequisites

The `tunnel` commands and the WireGuard safety gate during `apply` run `wg-quick` and `ip` via `sudo` on your local machine. This requires:

1. **`wireguard-tools`** installed locally
2. **Passwordless `sudo`** for `wg`, `wg-quick`, and `ip`

```bash
# Grant passwordless sudo for WireGuard commands only:
# Create /etc/sudoers.d/wireguard-loft-cli with:
%sudo ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick, /usr/sbin/ip

# Validate the syntax:
sudo visudo -f /etc/sudoers.d/wireguard-loft-cli
```

If WireGuard is not enabled in your spec, these prerequisites do not apply.
