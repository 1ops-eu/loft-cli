# Spec Reference

loft-cli specs are YAML files with a `kind` field that determines what gets deployed. Every spec follows the same four-step pipeline: validate → plan → docs → apply.

---

## All Spec Kinds

| Kind | Description | Platform |
|---|---|---|
| [`bootstrap`](bootstrap.md) | Harden a fresh Debian/Ubuntu server | Debian, Ubuntu |
| [`service`](service.md) | Install PostgreSQL, Nginx, Docker, containers | Any bootstrapped host |
| [`file_template`](file-template.md) | Render managed config files from Jinja2 templates | Any bootstrapped host |
| [`compose_project`](compose-project.md) | Deploy Docker Compose stacks | Any host with Docker |
| [`stack`](stack.md) | Group resources with dependency ordering | Any bootstrapped host |
| [`http_check`](http-check.md) | HTTP readiness probe with retry/backoff | Any bootstrapped host |
| [`systemd_unit`](systemd-unit.md) | Host-native systemd services | Debian, Ubuntu |
| [`systemd_timer`](systemd-timer.md) | Scheduled execution via systemd timers | Debian, Ubuntu |
| [`backup_job`](backup-job.md) | Backup with retention and scheduling | Debian, Ubuntu |
| [`postgres_ensure`](postgres-ensure.md) | Ensure PostgreSQL users, databases, extensions | Any host with PostgreSQL |

---

## Common Fields

Every spec has a `meta` block and a `host` block:

```yaml
meta:
  name: my-resource           # Required. Unique name for this resource.
  description: My description # Optional. Human-readable description.

host:
  name: prod-1                # Required. Matches the host_alias in your SSH config.
  address: 203.0.113.10       # Required for bootstrap; optional if SSH config is set.
  os_family: debian           # "debian" or "rhel"
```

And a `login` block (for specs that connect to a server):

```yaml
login:
  user: deploy                # SSH user
  private_key: ~/.ssh/id_ed25519
  port: 2222
```

---

## Multi-Document Specs

A single YAML file can contain multiple specs separated by `---`. All documents are processed in order:

```yaml
kind: postgres_ensure
meta:
  name: app-db
# ...
---
kind: compose_project
meta:
  name: app-stack
# ...
```

This is the recommended pattern for deploying a complete application: database resources first, then the application stack.

---

## Environment Variables

Use `${VAR}` references anywhere in a spec:

```yaml
host:
  address: ${SERVER_IP}
login:
  private_key: ${SSH_KEY_PATH}
```

Load values from a `.env` file:

```bash
loft-cli apply spec.yaml --env-file .env
```

`--env-file` is repeatable. Shell environment variables always take precedence over `.env` files.
