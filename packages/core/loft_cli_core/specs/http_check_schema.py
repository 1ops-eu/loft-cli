"""Pydantic v2 models for kind: http_check YAML specs.

GET-only HTTP readiness probe with configurable retry, backoff, and timeout.
Usable as a dependency gate in stacks — "proceed only when this URL returns
the expected status code".  No request bodies, no mutations, no response
templating.
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


class HttpCheckConfig(BaseModel):
    """Configuration for a GET-only HTTP readiness probe."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="URL to GET for the readiness check.")
    expected_status: int = Field(
        default=200, description="HTTP status code that indicates a passing check."
    )
    retries: int = Field(
        default=5, description="Number of GET attempts before marking the check as failed."
    )
    interval: int = Field(default=3, description="Seconds to wait between retry attempts.")
    timeout: int = Field(default=10, description="Per-request timeout in seconds.")


class HttpCheckLoginBlock(BaseModel):
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


class HttpCheckLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class HttpCheckSpec(BaseModel):
    """Spec for GET-only HTTP readiness checks, usable as stack dependency gates."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["http_check"]
    meta: MetaBlock
    host: HostBlock
    login: HttpCheckLoginBlock = Field(default_factory=HttpCheckLoginBlock)
    check: HttpCheckConfig
    local: HttpCheckLocalBlock = Field(default_factory=HttpCheckLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
