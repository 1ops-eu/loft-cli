# kind: bootstrap

> Hardens a fresh Debian or Ubuntu server into a production-ready node with SSH key auth, a custom port, UFW firewall, and optional WireGuard VPN.

This is the entry point for every loft-cli-managed server. It must be applied before any `service`, `compose_project`, or other spec kinds.

---

## What It Does

1. Detects the OS and installs base packages
2. Creates an admin user with SSH key authentication
3. Configures a custom SSH port
4. **Gate 1** — verifies admin login with key auth before proceeding
5. Changes the SSH port in `sshd_config`
6. Opens the new port in UFW
7. **Gate 2** — verifies admin login on the new port before disabling root access
8. Disables root login and password authentication
9. Finalizes the firewall
10. Sets up WireGuard (if enabled)
11. **Gate 3** (WireGuard) — verifies SSH through the tunnel before locking SSH to VPN-only
12. Runs Goss server verification
13. Writes local SSH config entry and inventory record

!!! info "Safety Gates"
    The bootstrap plan contains three safety gates. Steps that would lock you out of the server **never execute** unless the preceding gate passes. If a gate fails, the plan aborts and you keep root access.

---

## Full Example

```yaml
kind: bootstrap

meta:
  name: production-node-bootstrap
  description: Harden a fresh Ubuntu node for production self-hosting

host:
  name: prod-node-1
  address: 203.0.113.10
  os_family: debian

login:
  user: root
  private_key: ~/.ssh/id_ed25519
  port: 22

admin_user:
  name: deploy
  groups:
    - sudo
  pubkeys:
    - ~/.ssh/id_ed25519.pub

ssh:
  port: 2222
  disable_root_login: true
  disable_password_auth: true

firewall:
  provider: ufw
  ssh_only: true

wireguard:
  enabled: true
  interface: wg0
  address: 10.10.0.1/24
  private_key_file: .secrets/wg.key
  endpoint: vpn.example.com:51820
  peer_address: 10.10.0.2/32
  persistent_keepalive: 25

local:
  ssh_config:
    enabled: true
    host_alias: prod-node-1
  inventory:
    enabled: true
    db_path: ~/.loft-cli/inventory.db
```

---

## Schema

### `meta`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique name for this bootstrap resource |
| `description` | string | No | Human-readable description |

### `host`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Host alias used in SSH config and inventory |
| `address` | string | Yes | IP address or hostname of the target server |
| `os_family` | string | Yes | `debian` (covers Debian and Ubuntu) |

### `login`

| Field | Type | Required | Description |
|---|---|---|---|
| `user` | string | Yes | Initial SSH user (typically `root`) |
| `private_key` | string | Yes | Path to the SSH private key |
| `port` | int | No | SSH port to connect on (default: 22) |

### `admin_user`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Username for the new admin account |
| `groups` | list[string] | No | Additional groups (include `sudo` for sudo access) |
| `pubkeys` | list[string] | Yes | Paths to SSH public key files. At least one required when `disable_password_auth: true`. |

### `ssh`

| Field | Type | Required | Description |
|---|---|---|---|
| `port` | int | No | New SSH port (default: 22) |
| `disable_root_login` | bool | No | Disable root SSH login (default: false) |
| `disable_password_auth` | bool | No | Disable password authentication (default: false). Requires at least one pubkey. |

### `firewall`

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | string | No | Firewall provider — `ufw` (default) |
| `ssh_only` | bool | No | Enable firewall allowing only the configured SSH port (default: false) |
| `allow_ports` | list[int] | No | Additional ports to open in the firewall |

### `wireguard`

| Field | Type | Required | Description |
|---|---|---|---|
| `enabled` | bool | No | Enable WireGuard VPN configuration (default: false) |
| `interface` | string | Yes (if enabled) | WireGuard interface name on the server (e.g. `wg0`) |
| `address` | string | Yes (if enabled) | Server's WireGuard IP in CIDR notation (e.g. `10.10.0.1/24`) |
| `private_key_file` | string | Yes (if enabled) | Path to the server's WireGuard private key file |
| `endpoint` | string | Yes (if enabled) | Public endpoint for the WireGuard server (`host:port`) |
| `peer_address` | string | Yes (if enabled) | Client peer's IP in CIDR notation (e.g. `10.10.0.2/32`) |
| `persistent_keepalive` | int | No | Keepalive interval in seconds (default: 25) |

### `local`

| Field | Type | Required | Description |
|---|---|---|---|
| `ssh_config.enabled` | bool | No | Write a `~/.ssh/conf.d/` entry (default: false) |
| `ssh_config.host_alias` | string | No | Alias for the SSH config entry (defaults to `host.name`) |
| `ssh_config.config_path` | string | No | Path to the SSH config file (default: `~/.ssh/config`) |
| `inventory.enabled` | bool | No | Record in local inventory (default: false) |
| `inventory.db_path` | string | No | Path to the inventory database (default: `~/.loft-cli/inventory.db`) |

---

## After Bootstrap

Once bootstrap completes, you can SSH to the server using the alias:

```bash
ssh prod-node-1
```

The SSH config entry uses the VPN IP as `HostName` when WireGuard is enabled. For WireGuard-enabled hosts, you need to bring up the tunnel first:

```bash
loft-cli tunnel up prod-node-1
ssh prod-node-1
```

See [WireGuard Tunnel](../operations/wireguard.md) for the full tunnel workflow.
