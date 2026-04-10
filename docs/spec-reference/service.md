# kind: service

> Installs services on an already-bootstrapped server: PostgreSQL, Nginx, Docker, and Docker containers.

`kind: service` is the multi-service spec kind — a single spec file can declare PostgreSQL, Nginx, Docker, and containers all together. Each block is optional; the planner only generates steps for populated blocks.

---

## What It Does

The `service` kind dispatches to sub-planners based on which blocks are present:

- **`postgres`** — installs PostgreSQL, configures `listen_addresses`, optionally creates a role and database
- **`nginx`** — installs Nginx, deploys site configuration, enables the site
- **`docker`** — installs Docker Engine
- **`containers`** — pulls images, creates and starts containers with health checks

---

## Example: PostgreSQL

```yaml
kind: service

meta:
  name: postgres-primary
  description: Install PostgreSQL 16

host:
  name: prod-node-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

postgres:
  enabled: true
  version: "16"
  listen_addresses:
    - 127.0.0.1
  create_role:
    name: appuser
    password_env: APP_DB_PASSWORD
  create_database:
    name: appdb
    owner: appuser

local:
  inventory:
    enabled: true
```

## Example: Docker + Container

```yaml
kind: service

meta:
  name: app-services
  description: Docker + application container

host:
  name: prod-node-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

docker:
  enabled: true

containers:
  - name: webapp
    image: ghcr.io/acme/myapp:1.0.0
    ports:
      - "8080:8080"
    env:
      APP_ENV: production
    restart: unless-stopped
    healthcheck:
      type: http
      url: http://localhost:8080/health
      expect_status: 200

local:
  inventory:
    enabled: true
```

---

## Schema

### `postgres`

| Field | Type | Required | Description |
|---|---|---|---|
| `enabled` | bool | Yes | Enable PostgreSQL installation |
| `version` | string | No | PostgreSQL version (e.g. `"16"`) |
| `listen_addresses` | list[string] | No | IP addresses PostgreSQL listens on |
| `create_role.name` | string | No | Role name to create |
| `create_role.password_env` | string | No | Environment variable containing the role password |
| `create_database.name` | string | No | Database name to create |
| `create_database.owner` | string | No | Owner role for the database |

### `nginx`

| Field | Type | Required | Description |
|---|---|---|---|
| `enabled` | bool | Yes | Enable Nginx installation |
| `sites` | list | No | Site configurations to deploy |
| `sites[].name` | string | Yes | Site name (used as config filename) |
| `sites[].server_name` | string | Yes | `server_name` directive value |
| `sites[].listen_port` | int | No | Port to listen on (default: 80) |
| `sites[].proxy_pass` | string | No | Upstream URL for reverse proxy |
| `sites[].root` | string | No | Document root (for static sites) |

### `docker`

| Field | Type | Required | Description |
|---|---|---|---|
| `enabled` | bool | Yes | Enable Docker Engine installation |

### `containers`

Each item in the `containers` list:

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Container name |
| `image` | string | Yes | Docker image (including tag) |
| `ports` | list[string] | No | Port mappings (`"host:container"`) |
| `env` | dict | No | Environment variables |
| `volumes` | list[string] | No | Volume mounts (`"host:container"`) |
| `restart` | string | No | Restart policy (`always`, `unless-stopped`, `on-failure`) |
| `healthcheck.type` | string | No | `http` or `tcp` |
| `healthcheck.url` | string | No | URL to poll (for `http` type) |
| `healthcheck.expect_status` | int | No | Expected HTTP status code |

!!! note
    Containers require `docker.enabled: true` in the same spec (or Docker already installed on the server).
