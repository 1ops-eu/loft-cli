# kind: http_check

> A GET-only HTTP readiness probe with retry/backoff. Returns success only when the endpoint responds with the expected status code within the configured retry budget.

Use `http_check` as a post-deploy verification step, as a dependency gate inside a `kind: stack`, or as a standalone readiness check for any running service.

---

## What It Does

1. Makes a GET request to the configured URL
2. Checks the response status code against `expected_status`
3. Retries with `retry_delay_seconds` intervals if the check fails
4. Succeeds when the endpoint responds correctly within the retry budget
5. Fails if all retries are exhausted

---

## Example

```yaml
kind: http_check

meta:
  name: app-ready
  description: Verify the application is serving traffic

host:
  name: prod-1
  address: 203.0.113.10
  os_family: debian

login:
  user: deploy
  private_key: ~/.ssh/id_ed25519
  port: 2222

check:
  url: http://localhost:3000/health
  expected_status: 200
  retries: 10
  retry_delay_seconds: 5
  timeout_seconds: 10
```

---

## Schema

### `check`

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | URL to check. The request is made **from the server** (not from your local machine). |
| `expected_status` | int | No | Expected HTTP response status code (default: 200) |
| `retries` | int | No | Number of retry attempts (default: 5) |
| `retry_delay_seconds` | int | No | Seconds to wait between retries (default: 5) |
| `timeout_seconds` | int | No | Per-request timeout in seconds (default: 10) |

---

## Notes

**The request is made from the server.** Use `http://localhost:PORT` or internal IPs to check locally-running services. Do not use public domain names unless DNS resolution is available on the server at check time.

**GET only.** `http_check` does not support POST, PUT, or other methods. For more complex checks, use a `kind: systemd_unit` with a custom health-check script.

**Suitable as a stack gate.** Use `http_check` as the final resource in a `kind: stack` with `depends_on` pointing at the Compose project. The stack apply will not complete until the app is actually serving traffic.

```yaml
resources:
  - kind: compose_project
    meta:
      name: my-app
    # ...

  - kind: http_check
    meta:
      name: my-app-ready
    depends_on:
      - my-app
    check:
      url: http://localhost:8080/health
      retries: 24
      retry_delay_seconds: 5
```
