# Fleet Selector Example

Demonstrates `meta.labels` and the `--fleet`/`--selector` flags for fleet-wide
apply and doctor commands.

## Directory layout

```
hosts/
  worker-1.yaml   — env=staging, role=worker
  worker-2.yaml   — env=staging, role=worker
  prod-db-1.yaml  — env=production, role=db
```

## Usage

Apply only the staging workers:

```bash
loft-cli apply --fleet hosts/ --selector env=staging,role=worker
```

Run doctor on all staging hosts:

```bash
loft-cli doctor --fleet hosts/ --selector env=staging
```

Apply all hosts without a selector (all parseable specs):

```bash
loft-cli apply --fleet hosts/
```

Continue on error (don't abort on first failure):

```bash
loft-cli apply --fleet hosts/ --selector env=staging --continue-on-error
```

## Label format

Labels are set in the `meta` block of any spec:

```yaml
meta:
  name: staging-worker-1
  labels:
    env: staging
    role: worker
```

Selector expressions are comma-separated `key=value` predicates (AND semantics):

```
env=staging           # matches any spec with env=staging
env=staging,role=worker  # matches specs with BOTH env=staging AND role=worker
```
