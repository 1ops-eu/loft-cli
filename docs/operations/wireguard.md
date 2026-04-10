# WireGuard Tunnel

loft-cli has first-class support for WireGuard VPN tunnels. When enabled in a bootstrap spec, the server is configured to accept SSH only over the VPN — making the server unreachable from the public internet after bootstrap.

---

## Prerequisites

The `tunnel` commands and the WireGuard safety gate during `apply` run `wg-quick` and `ip` via `sudo` on your **local** machine. You need:

1. **`wireguard-tools`** installed locally

    ```bash
    # Ubuntu/Debian
    sudo apt install wireguard-tools

    # macOS
    brew install wireguard-tools
    ```

2. **Passwordless `sudo`** for the WireGuard commands

    ```bash
    # Create /etc/sudoers.d/wireguard-loft-cli:
    %sudo ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick, /usr/sbin/ip

    # Validate the syntax:
    sudo visudo -f /etc/sudoers.d/wireguard-loft-cli
    ```

    Without passwordless sudo, the subprocess will hang waiting for a password prompt and time out after 30 seconds.

---

## Enabling WireGuard in Bootstrap

Add a `wireguard` block to your bootstrap spec:

```yaml
wireguard:
  enabled: true
  interface: wg0
  address: 10.10.0.1/24           # Server's VPN IP
  private_key_file: .secrets/wg.key  # Path to the server's WireGuard private key
  endpoint: vpn.example.com:51820 # Public endpoint of the WireGuard server
  peer_address: 10.10.0.2/32      # Client's VPN IP
  persistent_keepalive: 25
```

**Generating a WireGuard private key:**

```bash
mkdir -p .secrets
wg genkey > .secrets/wg.key
chmod 600 .secrets/wg.key
```

---

## What Happens During Bootstrap

When `wireguard.enabled: true`, the bootstrap plan includes:

1. Generates a client key pair (stored locally in `~/.wg/loft-cli/<host>/`)
2. Installs WireGuard on the server
3. Configures the server's WireGuard interface with the provided keys and peer
4. Starts the WireGuard interface
5. Adds a UFW rule allowing SSH only from the WireGuard peer address
6. **Tunnel safety gate** — brings up the WireGuard tunnel locally, verifies SSH through the VPN IP
7. If the gate passes: deletes the open SSH rule (SSH is now VPN-only)
8. If the gate fails: tears down the tunnel, keeps the open SSH rule (server still accessible via public IP)
9. Writes the SSH config entry using the **VPN IP** as `HostName`

---

## Daily Use

### Bring Up the Tunnel

```bash
loft-cli tunnel up prod-1
```

Creates a `wg-prod-1` interface on your local machine using the key material from `~/.wg/loft-cli/prod-1/`.

### SSH Through the Tunnel

```bash
ssh prod-1
```

The SSH config entry uses the VPN IP (e.g. `10.10.0.2`) as `HostName`, so `ssh prod-1` automatically routes through the tunnel.

### Check Tunnel Status

```bash
loft-cli tunnel status
```

Lists all managed hosts and whether their WireGuard tunnel is currently active.

### Tear Down the Tunnel

```bash
loft-cli tunnel down prod-1
```

Removes the `wg-prod-1` interface. The server's WireGuard interface remains active — SSH is still VPN-only.

---

## Per-Host Interface Naming

Each host gets its own local WireGuard interface: `wg-<host>`. This means you can have multiple tunnels active simultaneously without conflict:

```bash
loft-cli tunnel up prod-1      # creates wg-prod-1
loft-cli tunnel up staging-1   # creates wg-staging-1
loft-cli tunnel status         # shows both active
```

---

## Key Material Storage

WireGuard key material is stored locally at `~/.wg/loft-cli/<host>/`:

```
~/.wg/loft-cli/prod-1/
  client.conf          ← WireGuard client config (wg-quick format)
  client_private.key   ← Client private key
  client_public.key    ← Client public key
  metadata.json        ← Interface name, VPN IPs, endpoint
```

These files are generated once during bootstrap and reused on every `tunnel up`.

---

## Decommissioning

When removing a host, the WireGuard key material and tunnel state are cleaned up automatically:

```bash
loft-cli remove prod-1
```

This removes the SSH config entry, WireGuard keys, and inventory record. It does not touch the server itself.
