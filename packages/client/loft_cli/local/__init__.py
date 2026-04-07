"""Local state management for loft-cli (SSH config, inventory, tunnels, selectors)."""

from loft_cli.local.selector import select_specs

__all__ = ["select_specs"]
