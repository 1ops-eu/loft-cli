# selector — Label-based spec selection

This example demonstrates the `select_specs` function from `loft_cli.local`,
which lets you filter YAML specs in a directory by label selectors.

## Spec files

- `worker-staging.yaml` — `role=worker, env=staging`
- `db-prod.yaml` — `role=db, env=prod`

## Labels in a spec

Add `meta.labels` as a plain key/value mapping to any spec:

```yaml
meta:
  name: my-spec
  labels:
    role: worker
    env: staging
```

## Using the selector API

```python
from loft_cli.local import select_specs

# Select only worker specs in staging
matches = select_specs("examples/selector", "role=worker,env=staging")
for path, spec in matches:
    print(path, spec.meta.name)
# -> examples/selector/worker-staging.yaml  worker-tools

# Multiple predicates are AND-matched — this returns nothing (raises ValueError)
try:
    select_specs("examples/selector", "role=worker,env=prod")
except ValueError as e:
    print(e)  # No specs in '...' matched selector 'role=worker,env=prod'
```

## Selector syntax

| Expression             | Meaning                                      |
|------------------------|----------------------------------------------|
| `role=worker`          | label `role` must equal `worker`             |
| `env=staging`          | label `env` must equal `staging`             |
| `role=worker,env=prod` | `role=worker` AND `env=prod` both must match |

- Predicates are separated by `,`
- All predicates must match (logical AND)
- An empty or malformed expression raises `ValueError`
