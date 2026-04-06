# loft-cli catalog — feature catalog introspection

The `loft-cli catalog` commands let you introspect the full catalog of spec
kinds registered in loft-cli (including any installed addon kinds).

## Commands

### catalog list

Print a table of all registered kinds with short descriptions:

```
$ loft-cli catalog list
Kind                Description
bootstrap           Harden a fresh Debian/Ubuntu host ...
service             Install and configure services ...
file_template       Render Jinja2 templates and upload managed config files ...
compose_project     Deploy a Docker Compose project ...
stack               Group related resources into a deployable boundary ...
http_check          GET-only HTTP readiness probe ...
backup_job          Host-local backup operations with retention ...
systemd_unit        Deploy and manage a host-native systemd service ...
systemd_timer       Deploy scheduled execution via systemd timers ...
postgres_ensure     Ensure PostgreSQL resources exist ...
package             Install or remove system packages ...
```

### catalog show <kind>

Print detailed field information for a single kind:

```
$ loft-cli catalog show bootstrap
Kind: bootstrap
Harden a fresh Debian/Ubuntu host: SSH hardening, firewall, admin user setup...

Fields:
  meta.name                      str          (required)  Human-readable name for this spec...
  meta.description               str          (optional)  Optional longer description...
  host.name                      str          (required)  Human-readable name for this host...
  host.address                   str          (required)  Public IP address or DNS hostname...
  ...

Outputs:
  ssh_alias
    SSH Host alias to connect to this host after bootstrap.
    Example: ssh {provider}--{host.name}  # e.g. ssh hetzner--dev-vps
  ssh_port
    SSH port as configured by the bootstrap spec.
    Example: 2222
```

If the kind is unknown, the command exits non-zero with a clear error:

```
$ loft-cli catalog show unknown-kind
Unknown kind: 'unknown-kind'
Run 'loft-cli catalog list' to see all available kinds.
```

### catalog export

Serialize all catalog entries to JSON for machine-readable consumption:

```
$ loft-cli catalog export | python -m json.tool
{
  "kinds": [
    {
      "kind": "bootstrap",
      "description": "Harden a fresh Debian/Ubuntu host ...",
      "fields": [
        {"name": "host.address", "type": "str", "required": true, "description": "..."}
      ],
      "outputs": [
        {"name": "ssh_alias", "description": "...", "example": "..."}
      ]
    },
    ...
  ]
}
```

## Addon extension

External addons can register their own catalog entries. Entries registered by
addons appear after the built-in kinds in all three catalog commands:

```python
# In loft_cli_pro/register.py:
from loft_cli_core.registry import register_catalog_entry, CatalogEntry, OutputTemplate

def register():
    register_catalog_entry("pro_deploy", CatalogEntry(
        kind="pro_deploy",
        description="Browser-triggered deployment via loft-cli-pro.",
        outputs=[
            OutputTemplate(
                name="deploy_url",
                description="Public URL of the deployed application.",
                example="https://myapp.example.com",
            ),
        ],
    ))
```

After installing the addon:
```
$ loft-cli catalog list
Kind            Description
...
pro_deploy      Browser-triggered deployment via loft-cli-pro.
```
