# Bootstrap Allow Ports Example

Demonstrates `firewall.allow_ports` — declarative UFW port rules added during
bootstrap (v0.7 feature #286).

## What it does

1. Bootstraps the server (admin user, SSH hardening, UFW)
2. Opens port 80/tcp (HTTP), 443/tcp (HTTPS), and 51820/udp (WireGuard) via
   `firewall.allow_ports`

## Usage

```bash
loft-cli validate examples/bootstrap-allow-ports/bootstrap-allow-ports.yaml
loft-cli plan    examples/bootstrap-allow-ports/bootstrap-allow-ports.yaml
loft-cli apply   examples/bootstrap-allow-ports/bootstrap-allow-ports.yaml
```

## Notes

- `ssh_only: false` is required when declaring `allow_ports` (otherwise UFW
  would block everything except SSH by default anyway)
- `proto: any` omits the `/proto` suffix from the ufw rule (e.g. `ufw allow 8080`)
- The planner emits one UFW allow step per declared rule, ordered after the
  default SSH allow rule
