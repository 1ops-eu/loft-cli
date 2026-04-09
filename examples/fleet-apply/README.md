# fleet-apply example

Demonstrates fleet apply: applying specs to multiple hosts using `--fleet` and label selectors.

## Structure

```
fleet/
  worker-01.yaml   # role=worker, env=staging
  worker-02.yaml   # role=worker, env=staging
  db-01.yaml       # role=database, env=staging
```

## Usage

Apply to all hosts in the fleet directory:

```sh
loft-cli apply --fleet ./fleet/
```

Apply only to `role=worker` hosts:

```sh
loft-cli apply --fleet ./fleet/ --selector "role=worker"
```

Apply to all `env=staging` hosts, continuing even if one fails:

```sh
loft-cli apply --fleet ./fleet/ --selector "env=staging" --continue-on-error
```

## Labels

Specs opt into fleet selection by declaring `meta.labels`:

```yaml
meta:
  name: worker-01
  labels:
    role: worker
    env: staging
```

Selectors use `key=value` syntax, comma-separated for AND logic:

- `role=worker` — all worker specs
- `env=staging,role=worker` — workers in staging only
