# Fleet Doctor Example

Demonstrates the `loft-cli doctor --fleet` command — running drift detection
across multiple hosts in a single invocation.

## What it does

The `--fleet` flag accepts a directory of YAML spec files and runs the doctor
command against each host in turn, then prints an aggregated summary table.

## Usage

```bash
# Check all hosts in the fleet directory
loft-cli doctor --fleet examples/doctor-fleet/fleet/

# Check only web servers (glob selector)
loft-cli doctor --fleet examples/doctor-fleet/fleet/ --selector 'web-*.yaml'

# Keep going even if one host errors
loft-cli doctor --fleet examples/doctor-fleet/fleet/ --continue-on-error

# Single-host (original behaviour, unchanged)
loft-cli doctor examples/bootstrap.yaml
```

## Fleet directory layout

```
doctor-fleet/
  fleet/
    web-1.yaml     # bootstrap spec for web server 1
    web-2.yaml     # bootstrap spec for web server 2
  README.md
```

## Output

For each host, the agent doctor output is printed inline. After all hosts are
checked a summary table is printed:

```
Fleet Doctor Summary
 Spec    Host            Status   Drifted Resources   Error
 web-1   203.0.113.11   clean
 web-2   203.0.113.12   drifted  ufw_rules

Summary: 2 host(s) — 1 clean, 1 drifted, 0 error(s)
```

Exit code is **1** if any host is drifted or errored, **0** if all are clean.

## Selector examples

| Selector         | Matches                          |
|------------------|----------------------------------|
| `web-*.yaml`     | `web-1.yaml`, `web-2.yaml`, ...  |
| `*.yaml`         | all YAML specs in the directory  |
| `prod-db-*.yaml` | all production DB specs          |
