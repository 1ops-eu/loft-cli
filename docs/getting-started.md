# Getting Started

This guide walks you from installation through your first successful server bootstrap.

---

## Prerequisites

- Python 3.11+ **or** a pre-built binary (no Python needed with the binary)
- SSH access to a fresh Debian or Ubuntu server as `root`
- An SSH key pair (`ssh-keygen -t ed25519` if you don't have one)

---

## Installation

=== "pip (recommended)"

    ```bash
    pip install loft-cli
    loft-cli --help
    ```

=== "Standalone binary (Linux)"

    Download the binary for your platform from the [Releases](https://github.com/1ops-eu/loft-cli/releases/latest) page:

    ```bash
    # Linux x86-64
    curl -L https://github.com/1ops-eu/loft-cli/releases/latest/download/loft-cli-linux-amd64 \
      -o /usr/local/bin/loft-cli
    chmod +x /usr/local/bin/loft-cli

    # Linux ARM64
    curl -L https://github.com/1ops-eu/loft-cli/releases/latest/download/loft-cli-linux-arm64 \
      -o /usr/local/bin/loft-cli
    chmod +x /usr/local/bin/loft-cli
    ```

=== "Standalone binary (macOS)"

    ```bash
    # Apple Silicon (M1/M2/M3)
    curl -L https://github.com/1ops-eu/loft-cli/releases/latest/download/loft-cli-macos-arm64 \
      -o /usr/local/bin/loft-cli
    chmod +x /usr/local/bin/loft-cli
    ```

=== "Docker"

    ```bash
    docker run --rm \
      -v ~/.ssh:/root/.ssh:ro \
      -v $(pwd):/workspace:ro \
      ghcr.io/1ops-eu/loft-cli:latest --help
    ```

Verify the install:

```bash
loft-cli version
```

---

## Your First Spec

Create a file called `my-server.yaml`:

```yaml
kind: bootstrap

meta:
  name: my-first-server
  description: Harden a fresh Ubuntu server

host:
  name: prod-1
  address: 203.0.113.10      # Replace with your server's IP
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

local:
  ssh_config:
    enabled: true
    host_alias: prod-1
  inventory:
    enabled: true
```

---

## Step 1: Validate

Check the spec for errors before doing anything:

```bash
loft-cli validate my-server.yaml
```

If validation passes, you'll see a green confirmation. Errors are reported with the exact field path.

---

## Step 2: Preview the Plan

See exactly what loft-cli will do — before it does anything:

```bash
loft-cli plan my-server.yaml
```

This prints a numbered list of steps. Review them carefully. The bootstrap plan is ~25 steps including three safety gates that prevent SSH lockouts.

---

## Step 3: Generate Ops Docs (optional)

Generate a Markdown runbook you can put in your wiki:

```bash
loft-cli docs my-server.yaml -o PROD_1_BOOTSTRAP.md
```

---

## Step 4: Apply

Execute the plan:

```bash
loft-cli apply my-server.yaml
```

loft-cli will:

1. Connect to your server as `root`
2. Install the `loft-cli-agent` on the server
3. Upload the plan and invoke the agent
4. The agent executes all steps locally (no SSH round-trips per command)
5. Run [Goss](https://github.com/goss-org/goss) server verification at the end
6. Write a local SSH config entry and inventory record

After apply, SSH directly to the server:

```bash
ssh prod-1    # uses the ~/.ssh/conf.d/ entry loft-cli created
```

!!! success "Bootstrap complete"
    Your server is now hardened: SSH key-only on port 2222, root login disabled, UFW firewall active, and admin user `deploy` configured.

---

## Using Environment Variables

For sensitive values (IP addresses, passwords, key paths), use `${VAR}` references in your spec and load them from a `.env` file:

```yaml
host:
  address: ${SERVER_IP}

login:
  private_key: ${SSH_KEY_PATH}
```

```bash
# .env
SERVER_IP=203.0.113.10
SSH_KEY_PATH=~/.ssh/id_ed25519
```

```bash
loft-cli apply my-server.yaml --env-file .env
```

`--env-file` is repeatable. Later files override earlier ones. Shell environment variables always take precedence.

---

## Next: Install Services

Once the server is bootstrapped, install services with `kind: service`:

```bash
# Install PostgreSQL
loft-cli apply postgres.yaml --env-file .env

# Deploy a Docker container
loft-cli apply app.yaml --env-file .env
```

See the [Spec Reference](spec-reference/index.md) for all available spec kinds.

---

## Recommended Project Layout

```
my-project/
  servers/
    prod-1/
      bootstrap.yaml      ← kind: bootstrap
      services.yaml       ← kind: service, stack, etc.
      .env                ← per-server variables
    staging-1/
      bootstrap.yaml
      services.yaml
      .env
  shared/
    .env                  ← shared variables (org SSH key, org name, ...)
  templates/
    nginx-site.conf.j2    ← Jinja2 templates for kind: file_template
```

Apply with layered env files:

```bash
loft-cli apply servers/prod-1/bootstrap.yaml \
  --env-file shared/.env \
  --env-file servers/prod-1/.env
```
