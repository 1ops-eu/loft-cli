# kind: backup_job

> Defines backup operations with retention policy and scheduling via a systemd timer. Supports `postgres_dump` and `directory` backup types.

---

## What It Does

1. Generates a backup script for the configured backup type
2. Deploys it as a systemd oneshot service + timer (via `systemd_timer` primitives)
3. Configures retention: prunes backups older than `retention_days`
4. Runs on the configured schedule

---

## Example: PostgreSQL Dump

```yaml
kind: backup_job

meta:
  name: db-backup
  description: Nightly PostgreSQL backup with 30-day retention

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

backup:
  type: postgres_dump
  database: myapp
  user: postgres
  destination: /var/backups/myapp/postgres
  retention_days: 30
  schedule: "03:00"
  compress: true
```

## Example: Directory Backup

```yaml
kind: backup_job

meta:
  name: uploads-backup
  description: Daily backup of uploaded files

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

backup:
  type: directory
  source: /opt/myapp/uploads
  destination: /var/backups/myapp/uploads
  retention_days: 14
  schedule: "04:00"
  compress: true
```

---

## Schema

### `backup`

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | `postgres_dump` or `directory` |
| `destination` | string | Yes | Directory on the server where backups are stored |
| `retention_days` | int | No | Delete backups older than this many days (default: 30) |
| `schedule` | string | No | systemd calendar expression for when to run (default: `"03:00"`) |
| `compress` | bool | No | Compress backup files with gzip (default: true) |

**For `postgres_dump`:**

| Field | Type | Required | Description |
|---|---|---|---|
| `database` | string | Yes | Database name to dump |
| `user` | string | No | PostgreSQL user (default: `postgres`) |
| `host` | string | No | PostgreSQL host (default: `127.0.0.1`) |
| `port` | int | No | PostgreSQL port (default: 5432) |

**For `directory`:**

| Field | Type | Required | Description |
|---|---|---|---|
| `source` | string | Yes | Source directory to back up |

---

## Backup File Naming

Backup files are named with a timestamp: `<name>-YYYY-MM-DD-HHmmss.sql.gz` (for postgres_dump) or `<name>-YYYY-MM-DD-HHmmss.tar.gz` (for directory).

Retention cleanup runs after every backup, removing files in the destination directory older than `retention_days`.
