# kind: compose_project

> Manages a Docker Compose project on the server: uploads the compose file and configuration, validates, pulls images, starts services, and verifies health.

Use `compose_project` to deploy multi-container applications described by a `docker-compose.yml` file.

---

## What It Does

1. Uploads the `docker-compose.yml` to the target directory on the server
2. Runs `docker compose config` to validate the compose file
3. Pulls all images (`docker compose pull`)
4. Starts services (`docker compose up -d`)
5. Waits for all containers to reach healthy status (configurable timeout)
6. Optionally runs `post_deploy` steps

---

## Example

```yaml
kind: compose_project

meta:
  name: app-stack
  description: Main application Compose stack

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

project:
  name: myapp
  compose_file: docker-compose.yml
  directory: /opt/myapp
  env_file: .env.production
  pull: true
  health_check:
    timeout_seconds: 120
    interval_seconds: 5
```

---

## Schema

### `project`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Compose project name (sets `COMPOSE_PROJECT_NAME`) |
| `compose_file` | string | Yes | Path to the `docker-compose.yml`, relative to the spec file |
| `directory` | string | Yes | Destination directory on the server where the compose file is uploaded |
| `env_file` | string | No | Path to a `.env` file to upload alongside the compose file |
| `pull` | bool | No | Pull images before `up` (default: true) |
| `health_check.timeout_seconds` | int | No | Maximum time to wait for containers to become healthy (default: 60) |
| `health_check.interval_seconds` | int | No | How often to poll container health (default: 5) |

---

## Health Checking

After `docker compose up -d`, loft-cli polls the health status of all containers. A container is considered healthy when it either:

- Reports `healthy` status (if it defines a Docker healthcheck)
- Reaches `running` status and stays running (for containers without healthchecks)

If any container fails to reach healthy status within `timeout_seconds`, the apply fails with a clear error showing which containers are unhealthy.

---

## Idempotency

On re-apply, loft-cli computes the hash of the compose file content and compares it to the recorded hash. If the compose file is unchanged and all containers are running, the project is considered up-to-date and the step is skipped.

Changing the compose file (e.g. updating an image tag) causes the file to be re-uploaded and `docker compose up -d` to be re-run, which recreates only the affected services.

---

## Combining With Other Kinds

`compose_project` is typically used within a `kind: stack` alongside `file_template` (for `.env` files) and `http_check` (for application-level readiness):

```yaml
kind: stack
# ...
resources:
  - kind: file_template     # Render .env file
    # ...
  - kind: compose_project   # Deploy the stack
    depends_on: [env-file]
    # ...
  - kind: http_check        # Verify the app is serving
    depends_on: [app-stack]
    # ...
```
