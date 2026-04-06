# Compose Logs Example

Shows how to stream Docker Compose service logs via `loft-cli logs` (#285).

## Prerequisites

1. A running compose stack on an inventory host (e.g. deployed via the
   `compose-post-deploy` example or `compose-project` example).
2. The host must be recorded in the inventory (`local.inventory.enabled: true`
   during apply).

## Usage

```bash
# Stream logs from the app service on prod-node-1 (press Ctrl+C to stop)
loft-cli logs prod-node-1 app

# Show the last 100 lines and exit (no follow)
loft-cli logs prod-node-1 app --lines 100 --no-follow

# List the 20 most recent apply runs
loft-cli logs --limit 20

# Show full step details for a specific run ID
loft-cli logs --run ce70a7df
```

## How it works

`loft-cli logs` looks up `prod-node-1` in the local inventory database
(`~/.loft-cli/inventory.db`), opens an SSH connection, and runs:

```
docker compose logs [--follow] [--tail <lines>] <service>
```

Output is streamed line-by-line to your terminal. Press Ctrl+C to disconnect.
