"""Pydantic v2 models for kind: stack YAML specs.

A stack groups related resources (file_template, compose_project, etc.)
into a single deployable application boundary.  Stack members are
declared inline and executed in dependency order.

Design principles
-----------------
- Stacks expand into normal resource steps during planning.
- Operators still see the final concrete plan (no opaque magic bundles).
- Circular dependencies are rejected at validation time.
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


class StackLoginBlock(BaseModel):
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


class StackLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class StackResourceBlock(BaseModel):
    """A single resource within a stack.

    Each resource references a spec kind (file_template, compose_project,
    etc.) and carries its kind-specific configuration inline.  Optional
    ``depends_on`` declares ordering dependencies between resources in
    the same stack.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Unique resource name within the stack, e.g. 'traefik-config'.")
    kind: str = Field(
        description="Spec kind for this resource: 'file_template', 'compose_project', etc."
    )
    config: dict = Field(
        default_factory=dict, description="Kind-specific configuration block for this resource."
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Names of other resources in this stack that must be applied first.",
    )


class StackSpec(BaseModel):
    """Spec for deploying a stack of related resources on a single host."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["stack"]
    meta: MetaBlock
    host: HostBlock
    login: StackLoginBlock = Field(default_factory=StackLoginBlock)
    local: StackLocalBlock = Field(default_factory=StackLocalBlock)
    resources: list[StackResourceBlock] = Field(default_factory=list)
    checks: list[CheckBlock] = Field(default_factory=list)
