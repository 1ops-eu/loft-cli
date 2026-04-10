# kind: systemd_unit

> Deploys and manages a host-native systemd service. Supports optional logrotate configuration for the service's log files.

Use `systemd_unit` when you want to run a binary or script as a managed system service with automatic restart, resource limits, and proper init integration — without Docker.

---

## What It Does

1. Writes the systemd unit file to `/etc/systemd/system/<name>.service`
2. Runs `systemctl daemon-reload`
3. Enables the service (`systemctl enable`)
4. Starts the service (`systemctl start`)
5. Optionally writes a logrotate config to `/etc/logrotate.d/<name>`

---

## Example

```yaml
kind: systemd_unit

meta:
  name: my-worker
  description: Background processing worker

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

unit:
  name: my-worker
  description: My background worker service
  exec_start: /usr/local/bin/my-worker --config /etc/my-worker/config.toml
  user: deploy
  group: deploy
  working_directory: /opt/my-worker
  restart: always
  restart_sec: 5
  environment:
    APP_ENV: production
    LOG_LEVEL: info
  log_file: /var/log/my-worker/worker.log
  logrotate:
    rotate: 7
    compress: true
    daily: true
```

---

## Schema

### `unit`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Service name (used as the `.service` filename) |
| `description` | string | No | Systemd unit `Description` |
| `exec_start` | string | Yes | Command to execute (full path + arguments) |
| `user` | string | No | User to run the service as |
| `group` | string | No | Group to run the service as |
| `working_directory` | string | No | Working directory for the service |
| `restart` | string | No | Restart policy: `always`, `on-failure`, `unless-stopped` |
| `restart_sec` | int | No | Seconds to wait before restarting |
| `environment` | dict | No | Environment variables for the service |
| `log_file` | string | No | Path to the log file (used by logrotate) |

### `unit.logrotate`

| Field | Type | Required | Description |
|---|---|---|---|
| `rotate` | int | No | Number of rotations to keep (default: 7) |
| `compress` | bool | No | Compress rotated logs (default: true) |
| `daily` | bool | No | Rotate daily (default: true) |
| `weekly` | bool | No | Rotate weekly |
| `postrotate` | string | No | Shell command to run after rotation (e.g. reload the service) |

---

## Idempotency

On re-apply, loft-cli hashes the generated unit file content. If the unit file hasn't changed and the service is running, the step is skipped. If the unit file changes, the service is reloaded (or restarted) automatically.
