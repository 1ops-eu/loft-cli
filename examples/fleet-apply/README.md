# fleet-apply example

Demonstrates `loft-cli apply --fleet` to apply a directory of specs sequentially.

## Usage

### Apply all specs in the fleet

```bash
loft-cli apply --fleet examples/fleet-apply/specs
```

Output:
```
Fleet apply: 2 host(s) matched
[1/2] worker-1.yaml
  ...apply output for worker-1...
[2/2] worker-2.yaml
  ...apply output for worker-2...
Done: 2 succeeded, 0 failed
```

### Continue past failures

```bash
loft-cli apply --fleet examples/fleet-apply/specs --continue-on-error
```

If one host fails, the remaining hosts are still attempted. The final summary
reports per-host attribution:

```
Done: 1 succeeded, 1 failed
Failed hosts:
  ✗ examples/fleet-apply/specs/worker-2.yaml
```

### Dry-run a fleet

```bash
loft-cli apply --fleet examples/fleet-apply/specs --dry-run
```

### Filter with a selector (requires meta.labels support)

```bash
loft-cli apply --fleet examples/fleet-apply/specs --selector role=worker
```

Specs are filtered by matching `meta.labels.role == "worker"`.

## Files

```
specs/
  worker-1.yaml   -- package spec targeting 203.0.113.11
  worker-2.yaml   -- package spec targeting 203.0.113.12
```
