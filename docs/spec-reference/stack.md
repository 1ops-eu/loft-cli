# kind: stack

> Groups related resources (`file_template`, `compose_project`, `http_check`, etc.) into a single deployable application boundary. Resources are declared inline with explicit dependency ordering and executed via topological sort.

Use `stack` when you have multiple interdependent resources that should be deployed together: a config file, a Compose project, and a health check, for example.

---

## What It Does

1. Validates dependency declarations for circular references (at validation time — no silent cycles)
2. Sorts resources topologically by `depends_on`
3. Executes resources in order, each using its own planner
4. Records all resources as `stack_resource` entries in the inventory

---

## Example

```yaml
kind: stack

meta:
  name: myapp
  description: Full application stack — config, Compose, readiness check

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

resources:
  - kind: file_template
    meta:
      name: app-env
    template:
      src: templates/app.env.j2
      dest: /opt/myapp/.env
      vars:
        db_host: 127.0.0.1
        db_name: myapp
        db_password: ${DB_PASSWORD}

  - kind: compose_project
    meta:
      name: app-compose
    depends_on:
      - app-env
    project:
      name: myapp
      compose_file: docker-compose.yml
      directory: /opt/myapp

  - kind: http_check
    meta:
      name: app-ready
    depends_on:
      - app-compose
    check:
      url: http://localhost:8080/health
      expected_status: 200
      retries: 20
      retry_delay_seconds: 5
```

---

## Schema

### Top-level

| Field | Type | Required | Description |
|---|---|---|---|
| `meta.name` | string | Yes | Stack name |
| `host` | object | Yes | Target host (same as other kinds) |
| `login` | object | Yes | SSH credentials |
| `resources` | list | Yes | List of resource declarations |

### `resources[]`

Each resource is a full spec-kind declaration with one addition:

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | string | Yes | Resource type: `file_template`, `compose_project`, `http_check`, `systemd_unit`, `systemd_timer`, `backup_job`, `postgres_ensure` |
| `meta.name` | string | Yes | Resource name — used as the `depends_on` reference key |
| `depends_on` | list[string] | No | Names of resources that must complete before this one starts |
| *(kind-specific fields)* | | | Same fields as the standalone spec kind |

---

## Dependency Ordering

Resources are executed in the order determined by `depends_on` declarations. Circular dependencies are detected at validation time and cause a hard error — the plan is never generated.

If multiple resources have no dependency relationship, they are executed in declaration order (stable sort).

---

## Step ID Prefixing

Steps generated from stack resources are prefixed with the resource name for traceability:

```
app-env/render_template
app-env/upload_file
app-compose/upload_compose_file
app-compose/docker_compose_up
app-ready/http_get
```

This makes run logs easy to navigate when a stack has many resources.
