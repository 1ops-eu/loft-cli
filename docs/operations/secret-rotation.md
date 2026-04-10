# Secret Rotation

loft-cli provides `rotate-secret` as a first-class day-2 operation for rotating secrets without manual server access.

---

## Rotating a Secret

```bash
loft-cli rotate-secret <spec.yaml> --secret NAME [--env-file PATH]...
```

This command:

1. Generates a new value for the named secret (or reads the new value from an updated env variable)
2. Updates the secret on the server
3. Re-applies the affected resources (e.g. restarts the application with the new secret)
4. Records the rotation in the local inventory

---

## Example

Rotating a database password:

```bash
# Update the value in your .env file first:
# APP_DB_PASSWORD=new-secure-password-here

loft-cli rotate-secret services.yaml \
  --secret APP_DB_PASSWORD \
  --env-file servers/prod-1/.env
```

---

## Policy Approval Tokens

If the server has a `policy.yaml` with `require_approval` rules, some steps may require an approval token before they execute.

Generate a time-limited token:

```bash
loft-cli rotate-secret --generate-approval-token --step-id <STEP_ID>
```

Pass the token during apply:

```bash
loft-cli apply spec.yaml --approval-token <TOKEN>
```

Tokens are:

- **HMAC-SHA256 signed** — tamper-evident
- **Time-limited** — expire after a configurable TTL (default: 1 hour)
- **Server-scoped** — keyed to the specific server, cannot be reused across hosts
- **Validated locally** — no network round-trip required

---

## Policy Engine

The policy engine controls step execution on the agent. Configure it via `/etc/loft-cli/policy.yaml` on the server:

```yaml
version: "1"
default_action: auto_apply

rules:
  - name: require-approval-for-schema-changes
    match_tags: [schema_migration]
    action: require_approval

  - name: deny-root-commands
    match_id: "run_as_root_*"
    action: deny

  - name: auto-apply-health-checks
    match_kind: http_check
    action: auto_apply
```

Rules are evaluated in order. The first matching rule wins. If no rule matches, `default_action` applies.

Policy is **inert by default** — no `policy.yaml` means all steps execute without restriction.

### Rule Matching

Each rule can match on any combination of (all specified conditions must hold):

| Field | Matches | Example |
|---|---|---|
| `match_kind` | Step kind (exact) | `"ssh_command"`, `"http_check"` |
| `match_id` | Step ID (glob pattern) | `"install_*"`, `"*_migration"` |
| `match_tags` | Any of the listed tags | `[destructive, schema_migration]` |
