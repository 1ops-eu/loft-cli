"""Addon-overridable local filesystem path configuration.

Core code always calls ``get_local_paths()`` to discover where loft-cli
stores its local state (SSH conf.d entries, WireGuard key material, inventory
database, run logs, etc.).

The defaults place everything under standard XDG-adjacent directories:

    ~/.ssh/conf.d/loft-cli/   -- per-host SSH config fragments
    ~/.wg/loft-cli/           -- per-host WireGuard key material and metadata
    ~/.loft-cli/inventory.db  -- local server inventory
    ~/.loft-cli/runs/         -- apply execution logs

When ``LOFT_CLI_STATE_DIR`` is set (or ``state_dir`` is passed explicitly),
all paths are derived from that base directory instead:

    {state_dir}/ssh/conf.d/    -- SSH config fragments
    {state_dir}/wg/            -- WireGuard state
    {state_dir}/inventory.db   -- inventory database
    {state_dir}/runs/          -- execution logs

This allows full isolation between production and test/CI contexts with a
single environment variable.

Priority order (highest to lowest):

1. Explicit field values (``ssh_conf_d_base=...``, ``wg_state_base=...``)
2. ``state_dir`` (either from ``LOFT_CLI_STATE_DIR`` env var or explicit)
3. Built-in defaults (``~/.ssh/conf.d/loft-cli/``, etc.)

Commercial clones or multi-environment addons can override these paths
**without modifying any core source file** by registering a
``LocalPathsConfig`` in their ``register()`` function:

    from loft_cli_core.registry.local_paths import register_local_paths, LocalPathsConfig
    from pathlib import Path

    def register():
        register_local_paths(LocalPathsConfig(
            ssh_conf_d_base=Path("~/.ssh/conf.d/mycompany/prod/").expanduser(),
            wg_state_base=Path("~/.wg/mycompany/prod/").expanduser(),
        ))

Semantics: last registration wins.  Core calls ``register_local_paths``
once (via ``_builtins._register_builtins``) to set the defaults; addons
loaded afterward simply replace the config object.

Planned: ``loft-cli doctor`` will display the active paths so operators
always know exactly where their local state lives.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Sentinel object to distinguish "not provided" from None/explicit values.
_UNSET: Path = Path("__UNSET__")


def _default_state_dir() -> Path | None:
    """Read LOFT_CLI_STATE_DIR from environment, or return None."""
    val = os.environ.get("LOFT_CLI_STATE_DIR")
    if val:
        return Path(val).expanduser()
    return None


@dataclass
class LocalPathsConfig:
    """Filesystem base directories for loft-cli local state.

    Attributes
    ----------
    state_dir:
        When set, all other paths are derived from this base directory
        unless explicitly overridden.  Read from ``LOFT_CLI_STATE_DIR``
        environment variable by default, or passed explicitly.

    ssh_conf_d_base:
        Directory that contains per-host SSH config fragments.
        Core appends ``{host_name}.conf`` to form the final path.
        The ``Include`` directive written to ``~/.ssh/config`` will be
        ``Include {ssh_conf_d_base}/*``, so all fragments in the directory
        are covered by a single glob -- no per-file Include management needed.

    wg_state_base:
        Directory under which per-host WireGuard state is stored.
        Core appends ``{host_name}/`` to form the per-host directory, then
        writes ``private.key``, ``public.key``, ``wg0.conf``,
        ``client.key``, ``client.conf``, and ``metadata.json`` inside it.

    inventory_db_path:
        Path to the SQLite inventory database file.

    log_dir:
        Directory for JSON apply execution logs.
    """

    state_dir: Path | None = field(default_factory=_default_state_dir)
    # Use _UNSET sentinel so __post_init__ can distinguish "not provided"
    # from an explicit value.
    ssh_conf_d_base: Path = field(default_factory=lambda: _UNSET)
    wg_state_base: Path = field(default_factory=lambda: _UNSET)
    inventory_db_path: Path = field(default_factory=lambda: _UNSET)
    log_dir: Path = field(default_factory=lambda: _UNSET)
    keys_base: Path = field(default_factory=lambda: _UNSET)

    def __post_init__(self) -> None:
        """Fill unset paths from state_dir or built-in defaults."""
        if self.ssh_conf_d_base is _UNSET:
            self.ssh_conf_d_base = (
                (self.state_dir / "ssh" / "conf.d")
                if self.state_dir
                else Path("~/.ssh/conf.d/loft-cli").expanduser()
            )
        if self.wg_state_base is _UNSET:
            self.wg_state_base = (
                (self.state_dir / "wg") if self.state_dir else Path("~/.wg/loft-cli").expanduser()
            )
        if self.inventory_db_path is _UNSET:
            self.inventory_db_path = (
                (self.state_dir / "inventory.db")
                if self.state_dir
                else Path("~/.loft-cli/inventory.db").expanduser()
            )
        if self.log_dir is _UNSET:
            self.log_dir = (
                (self.state_dir / "runs")
                if self.state_dir
                else Path("~/.loft-cli/runs").expanduser()
            )
        if self.keys_base is _UNSET:
            self.keys_base = (
                (self.state_dir / "keys")
                if self.state_dir
                else Path("~/.loft-cli/keys").expanduser()
            )


# Module-level singleton -- replaced wholesale on each call to register_local_paths().
_config: LocalPathsConfig = LocalPathsConfig()


def register_local_paths(config: LocalPathsConfig) -> None:
    """Replace the active local paths config (last registration wins)."""
    global _config
    _config = config


def get_local_paths() -> LocalPathsConfig:
    """Return the currently active local paths config."""
    return _config


def provider_ssh_conf_d_base(provider: str, config: LocalPathsConfig | None = None) -> Path:
    """Return the SSH conf.d base directory namespaced under a provider.

    When ``provider`` is non-empty, fragments are stored in a subdirectory
    named after the provider so that keys from different cloud providers do
    not collide:

        {ssh_conf_d_base}/{provider}/  (e.g. ~/.ssh/conf.d/loft-cli/hetzner/)

    When ``provider`` is empty the base directory itself is returned
    (backward-compatible behaviour).
    """
    base = (config or _config).ssh_conf_d_base
    if provider:
        return base / provider
    return base


def ssh_key_dir(provider: str, host_name: str, config: LocalPathsConfig | None = None) -> Path:
    """Return the SSH key directory for a given provider and host.

    Keys are stored under:
        {keys_base}/{provider}/{host_name}/  (e.g. ~/.loft-cli/keys/hetzner/my-server/)
    """
    base = (config or _config).keys_base
    return base / provider / host_name


def provider_wg_state_base(provider: str, config: LocalPathsConfig | None = None) -> Path:
    """Return the WireGuard state base directory namespaced under a provider.

    When ``provider`` is non-empty, WG key material is stored under:

        {wg_state_base}/{provider}/  (e.g. ~/.wg/loft-cli/hetzner/)

    When ``provider`` is empty the base directory itself is returned.
    """
    base = (config or _config).wg_state_base
    if provider:
        return base / provider
    return base
