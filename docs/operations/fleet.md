# Fleet Operations

loft-cli supports light multi-host operations — running commands across a set of servers selected by tags, roles, or other attributes from your local inventory.

---

## Fleet Selectors

Select hosts from the local inventory using attribute selectors:

```yaml
kind: fleet_apply

meta:
  name: deploy-workers

selector:
  role: worker
  env: production

spec:
  # Spec to apply to each selected host
  kind: compose_project
  # ...
```

Selectors support:

| Operator | Example | Matches |
|---|---|---|
| Equality | `role: worker` | Hosts with `role=worker` |
| Multiple | `role: worker, env: prod` | Hosts matching all conditions |

---

## Sequential Apply

Fleet operations apply specs sequentially across selected hosts, one host at a time. This ensures:

- A failure on one host stops the fleet apply before affecting other hosts
- You can review the result of each host before the next begins
- No simultaneous mutations across the fleet

---

## Fleet Doctor

Check drift across all selected hosts at once:

```bash
loft-cli doctor servers/fleet-services.yaml
```

With a fleet selector spec:

```yaml
kind: fleet_doctor

selector:
  role: worker

spec:
  # Spec to check on each selected host
  kind: compose_project
  # ...
```

The output shows drift status per host, making it easy to identify which servers have drifted.

---

## Aggregated Output

Fleet commands aggregate results across all selected hosts:

```
prod-worker-1  ✓  up-to-date (3/3 resources)
prod-worker-2  ✗  drifted (1/3 resources: compose_project)
prod-worker-3  ✓  up-to-date (3/3 resources)

Summary: 1 host drifted, 2 hosts up-to-date
```

---

## Failure Handling

By default, fleet apply stops on the first host failure. This conservative default prevents a bad deploy from rolling across the entire fleet.

Future versions will support configurable failure modes (e.g. continue on failure, max-failures threshold).

---

## Recommended Approach

For small fleets, manage hosts individually with per-host specs and env files:

```bash
for host in prod-1 prod-2 prod-3; do
  loft-cli apply servers/$host/services.yaml \
    --env-file shared/.env \
    --env-file servers/$host/.env
done
```

Use fleet selectors when you have a homogeneous group of hosts running the same spec and want to manage them as a unit.
