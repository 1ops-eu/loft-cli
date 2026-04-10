# kind: postgres_ensure

> Ensures PostgreSQL resources exist on a running instance: users, databases, extensions, and grants. Structured declarations only — no arbitrary SQL.

Use `postgres_ensure` for declarative database setup: create the application user, create the database, install extensions, and grant permissions — all idempotently.

---

## What It Does

1. Connects to the running PostgreSQL instance (via `psql` on the server)
2. For each declared user: creates the role if it doesn't exist, sets the password
3. For each declared database: creates it if it doesn't exist, sets the owner
4. For each declared extension: creates it in the specified database if absent
5. For each declared grant: applies the privilege grant

All operations are idempotent — re-applying with the same declarations produces no changes.

---

## Example

```yaml
kind: postgres_ensure

meta:
  name: app-db-setup
  description: Create application database user, database, and extensions

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

ensure:
  users:
    - name: app
      password_env: APP_DB_PASSWORD
    - name: readonly
      password_env: READONLY_DB_PASSWORD

  databases:
    - name: myapp
      owner: app
    - name: myapp_test
      owner: app

  extensions:
    - database: myapp
      name: pgcrypto
    - database: myapp
      name: uuid-ossp

  grants:
    - database: myapp
      schema: public
      privileges: [SELECT, INSERT, UPDATE, DELETE]
      role: app
    - database: myapp
      schema: public
      privileges: [SELECT]
      role: readonly
```

---

## Schema

### `ensure`

#### `ensure.users[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | PostgreSQL role name |
| `password_env` | string | Yes | Environment variable containing the password |

#### `ensure.databases[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Database name |
| `owner` | string | No | Owner role (must exist or be declared in `users`) |

#### `ensure.extensions[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `database` | string | Yes | Database to install the extension into |
| `name` | string | Yes | Extension name (e.g. `pgcrypto`, `uuid-ossp`, `vector`) |

#### `ensure.grants[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `database` | string | Yes | Database where the grant applies |
| `schema` | string | No | Schema to grant on (default: `public`) |
| `privileges` | list[string] | Yes | Privileges to grant (e.g. `[SELECT, INSERT]`) |
| `role` | string | Yes | Role to grant privileges to |

---

## Notes

**No arbitrary SQL.** `postgres_ensure` only supports the structured operations listed above. For complex schema migrations or one-time SQL operations, use a `post_deploy` step in a `compose_project` or a `systemd_unit` with a migration script.

**Password handling.** Passwords are passed via environment variables (never hardcoded in the spec). The environment variable is resolved on the client side and passed to the agent as part of the plan. The agent executes `ALTER ROLE ... PASSWORD '...'` on the server.

**Connection.** By default, connects to `127.0.0.1:5432` as `postgres`. Customize via `ensure.postgres_host` and `ensure.postgres_port` if needed.
