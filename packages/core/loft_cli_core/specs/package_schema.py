"""Pydantic v2 models for kind: package YAML specs.

Installs or removes system packages on a remote host using the host's
native package manager (apt on Debian/Ubuntu, yum/dnf on RHEL-family).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from loft_cli_core.specs.bootstrap_schema import (
    CheckBlock,
    HostBlock,
    InventoryBlock,
    MetaBlock,
)


class PackageLoginBlock(BaseModel):
    """Login defaults matching post-bootstrap convention (admin@2222)."""

    model_config = ConfigDict(extra="forbid")

    user: str = Field(default="admin", description="SSH username for connecting to the server.")
    private_key: str = Field(
        default="~/.ssh/id_ed25519", description="Path to the SSH private key for this connection."
    )
    password: str | None = Field(
        default=None, description="SSH password. Use only when key auth is not available."
    )
    port: int = Field(
        default=2222, description="SSH port on the server (post-bootstrap default is 2222)."
    )


class PackageEntry(BaseModel):
    """A single package to install or remove."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Package name to install or remove, e.g. 'nginx' or 'curl'.")
    state: Literal["present", "absent"] = Field(
        default="present", description="Desired state: 'present' to install, 'absent' to remove."
    )
    version: str | None = Field(
        default=None,
        description="Optional pinned version string, e.g. '1.22.1-1'. Installs the exact version if specified.",
    )


class PackageLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class PackageSpec(BaseModel):
    """Spec for installing or removing system packages on a remote host."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["package"]
    meta: MetaBlock
    host: HostBlock
    login: PackageLoginBlock = Field(default_factory=PackageLoginBlock)
    packages: list[PackageEntry] = Field(
        description="List of packages to install or remove. At least one required."
    )
    update_cache: bool = Field(
        default=True,
        description="Set to true to run 'apt-get update' or 'yum makecache' before installing packages.",
    )
    local: PackageLocalBlock = Field(default_factory=PackageLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
