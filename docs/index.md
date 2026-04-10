# loft-cli

> **A self-hosted infrastructure compiler — turns a typed YAML spec into a reviewable plan, deterministic execution, and human-readable ops docs for fresh Linux servers.**

loft-cli is **Layer 1**. It makes VMs ready and usable: bootstrap, harden, install services, deploy containers, manage configuration, detect drift, and verify state — all from a single typed YAML spec.

---

## Why loft-cli?

When you provision a server manually, the steps live in your head. With Ansible playbooks or shell scripts, the intent is buried in imperative code. loft-cli takes a different approach:

1. You write **what** you want (a YAML spec)
2. loft-cli generates **what it will do** (a reviewable plan)
3. You approve, then it executes **exactly** that plan

What you review is exactly what executes. Every time.

---

## Quick Install

=== "pip"

    ```bash
    pip install loft-cli
    ```

=== "Binary (Linux)"

    ```bash
    curl -L https://github.com/1ops-eu/loft-cli/releases/latest/download/loft-cli-linux-amd64 \
      -o /usr/local/bin/loft-cli
    chmod +x /usr/local/bin/loft-cli
    ```

=== "Binary (macOS)"

    ```bash
    curl -L https://github.com/1ops-eu/loft-cli/releases/latest/download/loft-cli-macos-arm64 \
      -o /usr/local/bin/loft-cli
    chmod +x /usr/local/bin/loft-cli
    ```

=== "Docker"

    ```bash
    docker run --rm ghcr.io/1ops-eu/loft-cli:latest --help
    ```

---

## The Four-Step Workflow

```bash
# 1. Validate — check your spec for errors
loft-cli validate my-server.yaml

# 2. Plan — see exactly what will happen
loft-cli plan my-server.yaml

# 3. Docs — generate a Markdown runbook
loft-cli docs my-server.yaml -o RUNBOOK.md

# 4. Apply — execute the plan
loft-cli apply my-server.yaml
```

---

## What You Get From One Spec

From a single YAML spec, loft-cli produces:

- A **secure, hardened Linux server** (SSH key-only, custom port, ufw firewall, optional WireGuard VPN)
- A **Markdown runbook** you can put in your wiki
- A **local `~/.ssh/conf.d/` entry** so `ssh prod-1` just works
- A **local inventory** with full historization

---

## Spec Kinds

| Kind | What it does |
|---|---|
| [`bootstrap`](spec-reference/bootstrap.md) | Harden a fresh Debian/Ubuntu server |
| [`service`](spec-reference/service.md) | Install PostgreSQL, Nginx, Docker, containers |
| [`file_template`](spec-reference/file-template.md) | Render managed config files from Jinja2 templates |
| [`compose_project`](spec-reference/compose-project.md) | Deploy Docker Compose stacks |
| [`stack`](spec-reference/stack.md) | Group resources with dependency ordering |
| [`http_check`](spec-reference/http-check.md) | HTTP readiness probe with retry/backoff |
| [`systemd_unit`](spec-reference/systemd-unit.md) | Host-native systemd services |
| [`systemd_timer`](spec-reference/systemd-timer.md) | Scheduled execution via systemd |
| [`backup_job`](spec-reference/backup-job.md) | Backup with retention and scheduling |
| [`postgres_ensure`](spec-reference/postgres-ensure.md) | Ensure PostgreSQL users, databases, extensions |

---

## What loft-cli is NOT

- Not a general-purpose config management system (not Ansible)
- Not a Kubernetes orchestrator
- Not a UI/SaaS product
- Not an application-level orchestrator — it does not configure SaaS apps, import workflows, or seed business data

**loft-cli is Layer 1.** Once it's done, the server is a functioning platform. Application-level configuration belongs in a separate orchestration layer.

---

## Next Steps

- [Getting Started](getting-started.md) — install, write your first spec, bootstrap a server
- [Concepts](concepts.md) — understand the pipeline, agent architecture, and safety model
- [Spec Reference](spec-reference/index.md) — full field-by-field documentation for every kind
