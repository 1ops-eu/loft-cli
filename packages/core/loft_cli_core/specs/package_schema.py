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

    user: str = "admin"
    private_key: str = "~/.ssh/id_ed25519"
    password: str | None = None
    port: int = 2222


class PackageEntry(BaseModel):
    """A single package to install or remove."""

    model_config = ConfigDict(extra="forbid")

    name: str  # package name, e.g. "nginx", "curl"
    state: Literal["present", "absent"] = "present"
    version: str | None = None  # optional pinned version (e.g. "1.22.1-1")


class PackageLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = ""
    inventory: InventoryBlock = Field(default_factory=InventoryBlock)


class PackageSpec(BaseModel):
    """Spec for installing or removing system packages on a remote host."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["package"]
    meta: MetaBlock
    host: HostBlock
    login: PackageLoginBlock = Field(default_factory=PackageLoginBlock)
    packages: list[PackageEntry]
    update_cache: bool = True  # run apt-get update / yum makecache before installing
    local: PackageLocalBlock = Field(default_factory=PackageLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
