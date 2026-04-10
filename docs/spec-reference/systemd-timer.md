# kind: systemd_timer

> Deploys scheduled execution via systemd timers — a oneshot service unit paired with a `.timer` unit. The standard systemd alternative to cron.

---

## What It Does

1. Writes a `<name>.service` unit file (type `oneshot`)
2. Writes a `<name>.timer` unit file with the schedule
3. Runs `systemctl daemon-reload`
4. Enables and starts the timer

---

## Example

```yaml
kind: systemd_timer

meta:
  name: nightly-cleanup
  description: Nightly database cleanup job

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

timer:
  name: nightly-cleanup
  description: Run cleanup script every night at 2am
  exec_start: /usr/local/bin/cleanup.sh --database myapp
  user: deploy
  on_calendar: "02:00"
  persistent: true
  environment:
    DB_HOST: 127.0.0.1
```

---

## Schema

### `timer`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Timer/service name |
| `description` | string | No | Description for both units |
| `exec_start` | string | Yes | Command to execute |
| `user` | string | No | User to run the command as |
| `on_calendar` | string | Yes | Systemd calendar expression (e.g. `"02:00"`, `"Mon *-*-* 03:00:00"`, `"hourly"`) |
| `persistent` | bool | No | Run the timer immediately if it was missed (default: true) |
| `environment` | dict | No | Environment variables for the service |

---

## Calendar Expressions

systemd uses its own calendar specification format:

| Schedule | Expression |
|---|---|
| Every day at 2am | `02:00` |
| Every hour | `hourly` |
| Every Monday at 3am | `Mon 03:00` |
| Every 15 minutes | `*:0/15` |
| Every day at midnight | `daily` |
| First day of the month | `*-*-01 00:00:00` |

See `man systemd.time` for the full specification.

---

## Versus `kind: backup_job`

For database backups, prefer [`kind: backup_job`](backup-job.md) — it provides structured backup declarations with retention policy and is purpose-built for that use case. `systemd_timer` is for generic scheduled scripts.
