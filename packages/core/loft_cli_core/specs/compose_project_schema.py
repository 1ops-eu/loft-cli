"""Pydantic v2 models for kind: compose_project YAML specs.

Manages Docker Compose projects: upload compose file and templates,
pull images, start the stack, and verify container health.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from loft_cli_core.specs.bootstrap_schema import (
    CheckBlock,
    HostBlock,
    InventoryBlock,
    MetaBlock,
)


class ComposeTemplateBlock(BaseModel):
    """A file to render from a Jinja2 template and upload into the project directory."""

    model_config = ConfigDict(extra="forbid")

    src: str  # local Jinja2 template path (spec-relative)
    dest: str  # filename relative to project directory


class ManagedDirectoryBlock(BaseModel):
    """An additional directory to create under (or outside) the project root."""

    model_config = ConfigDict(extra="forbid")

    path: str  # relative to project directory (or absolute)
    mode: str = "0755"
    owner: str = "root"
    group: str = "root"


class PlainFileBlock(BaseModel):
    """A plain file to upload verbatim (no Jinja2 rendering)."""

    model_config = ConfigDict(extra="forbid")

    src: str  # local file path (spec-relative)
    dest: str  # destination path (relative to project directory or absolute)
    mode: str = "0644"
    owner: str = "root"
    group: str = "root"


class HttpReadyCheck(BaseModel):
    """HTTP-level readiness check — poll a URL until it returns the expected status."""

    model_config = ConfigDict(extra="forbid")

    url: str
    expect_status: int = 200
    timeout: int = 120
    interval: int = 5


class ComposeHealthCheckBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    timeout: int = 120  # total seconds to wait for all containers healthy
    interval: int = 5  # seconds between polls
    http_ready: HttpReadyCheck | None = None


# ── Post-deploy action models ──────────────────────────────────────────────────


class PostDeployShellAction(BaseModel):
    """Run a shell command on the remote host after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["shell"]
    command: str


class PostDeployContainerExecAction(BaseModel):
    """Run a command inside a running container after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["container_exec"]
    container: str
    command: str


class PostDeployHttpRequestAction(BaseModel):
    """Make an HTTP request to the deployed service after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["http_request"]
    method: str = "GET"
    url: str
    body: str | None = None
    expect_status: int = 200


PostDeployAction = Annotated[
    PostDeployShellAction | PostDeployContainerExecAction | PostDeployHttpRequestAction,
    Field(discriminator="type"),
]


class ComposeProjectLoginBlock(BaseModel):
    """Login defaults matching post-bootstrap convention (admin@2222)."""

    model_config = ConfigDict(extra="forbid")

    user: str = "admin"
    private_key: str = "~/.ssh/id_ed25519"
    password: str | None = None
    port: int = 2222


class ComposeProjectLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = ""
    inventory: InventoryBlock = Field(default_factory=InventoryBlock)


class ComposeProjectBlock(BaseModel):
    """The core project configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str  # docker compose project name
    directory: str  # remote base directory (absolute)
    compose_file: str = "docker-compose.yml"  # compose filename (in project dir or spec-relative)
    templates: list[ComposeTemplateBlock] = Field(default_factory=list)
    files: list[PlainFileBlock] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)
    directories: list[ManagedDirectoryBlock] = Field(default_factory=list)
    pull_before_up: bool = True
    rebuild: bool = False  # force --force-recreate on docker compose up
    healthcheck: ComposeHealthCheckBlock = Field(default_factory=ComposeHealthCheckBlock)
    post_deploy: list[PostDeployAction] = Field(default_factory=list)


class ComposeProjectSpec(BaseModel):
    """Spec for deploying a Docker Compose project on a remote host."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["compose_project"]
    meta: MetaBlock
    host: HostBlock
    login: ComposeProjectLoginBlock = Field(default_factory=ComposeProjectLoginBlock)
    project: ComposeProjectBlock
    local: ComposeProjectLocalBlock = Field(default_factory=ComposeProjectLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
