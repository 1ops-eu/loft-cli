# Package Install Example

Demonstrates `kind: package` — declarative apt/apk package installation
(v0.7 feature #288).

## What it does

1. Connects to the target server via SSH
2. Runs `apt-get update` (because `update_cache: true`)
3. Installs `curl`, `jq`, `htop`, and `ncdu` via `apt-get install -y`
4. Records the operation in the local inventory

## Usage

```bash
loft-cli validate examples/package-install/package-install.yaml
loft-cli plan    examples/package-install/package-install.yaml
loft-cli apply   examples/package-install/package-install.yaml
```

## Removing packages

Set `state: absent` on any package entry to remove it:

```yaml
packages:
  - name: htop
    state: absent
```

## Pinning versions

```yaml
packages:
  - name: nginx
    state: present
    version: "1.22.1-1"
```

## Prerequisites

- A bootstrapped server with SSH access on port 2222 (admin user)
