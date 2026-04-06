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

    src: str = Field(description="Local Jinja2 template path relative to the spec file.")
    dest: str = Field(
        description="Destination filename relative to the project directory on the server."
    )


class ManagedDirectoryBlock(BaseModel):
    """An additional directory to create under (or outside) the project root."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        description="Directory path to create; relative to project directory or absolute."
    )
    mode: str = Field(
        default="0755", description="Directory permissions as an octal string, e.g. '0755'."
    )
    owner: str = Field(default="root", description="OS user that owns the directory.")
    group: str = Field(default="root", description="OS group that owns the directory.")


class PlainFileBlock(BaseModel):
    """A plain file to upload verbatim (no Jinja2 rendering)."""

    model_config = ConfigDict(extra="forbid")

    src: str = Field(
        description="Local file path relative to the spec file to upload without rendering."
    )
    dest: str = Field(description="Destination path relative to the project directory or absolute.")
    mode: str = Field(
        default="0644", description="File permissions as an octal string, e.g. '0644'."
    )
    owner: str = Field(default="root", description="OS user that owns the uploaded file.")
    group: str = Field(default="root", description="OS group that owns the uploaded file.")


class HttpReadyCheck(BaseModel):
    """HTTP-level readiness check — poll a URL until it returns the expected status."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="URL to poll until it returns the expected HTTP status.")
    expect_status: int = Field(
        default=200, description="HTTP status code that indicates the service is ready."
    )
    timeout: int = Field(
        default=120, description="Total seconds to wait for the URL to become ready."
    )
    interval: int = Field(default=5, description="Seconds between polling attempts.")


class ComposeHealthCheckBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Set to true to wait for all containers to reach healthy status after starting.",
    )
    timeout: int = Field(
        default=120, description="Total seconds to wait for all containers to report healthy."
    )
    interval: int = Field(default=5, description="Seconds between container health poll attempts.")
    http_ready: HttpReadyCheck | None = Field(
        default=None,
        description="Optional HTTP readiness check in addition to Docker health checks.",
    )


# ── Post-deploy action models ──────────────────────────────────────────────────


class PostDeployShellAction(BaseModel):
    """Run a shell command on the remote host after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["shell"]
    command: str = Field(
        description="Shell command to execute on the remote host after the compose stack is running."
    )


class PostDeployContainerExecAction(BaseModel):
    """Run a command inside a running container after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["container_exec"]
    container: str = Field(
        description="Name of the running container to execute the command inside."
    )
    command: str = Field(description="Command to run inside the container via 'docker exec'.")


class PostDeployHttpRequestAction(BaseModel):
    """Make an HTTP request to the deployed service after the stack is up."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["http_request"]
    method: str = Field(
        default="GET", description="HTTP method to use for the request: GET, POST, PUT, etc."
    )
    url: str = Field(description="URL to send the HTTP request to.")
    body: str | None = Field(default=None, description="Optional request body as a string.")
    expect_status: int = Field(
        default=200,
        description="Expected HTTP response status code for a successful post-deploy action.",
    )


PostDeployAction = Annotated[
    PostDeployShellAction | PostDeployContainerExecAction | PostDeployHttpRequestAction,
    Field(discriminator="type"),
]


class ComposeProjectLoginBlock(BaseModel):
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


class ComposeProjectLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class ComposeProjectBlock(BaseModel):
    """The core project configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Docker Compose project name (used as the --project-name flag).")
    directory: str = Field(
        description="Absolute path on the remote server where the project files are uploaded."
    )
    compose_file: str = Field(
        default="docker-compose.yml",
        description="Compose file name within the project directory, or a spec-relative local path.",
    )
    templates: list[ComposeTemplateBlock] = Field(
        default_factory=list,
        description="Jinja2 templates to render and upload into the project directory.",
    )
    files: list[PlainFileBlock] = Field(
        default_factory=list,
        description="Plain files to upload verbatim into the project directory.",
    )
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variables available to Jinja2 templates during rendering.",
    )
    directories: list[ManagedDirectoryBlock] = Field(
        default_factory=list,
        description="Additional directories to create in or alongside the project directory.",
    )
    pull_before_up: bool = Field(
        default=True,
        description="Set to true to run 'docker compose pull' before starting the stack.",
    )
    rebuild: bool = Field(
        default=False,
        description="Set to true to force --force-recreate on 'docker compose up' (recreates containers).",
    )
    healthcheck: ComposeHealthCheckBlock = Field(
        default_factory=ComposeHealthCheckBlock,
        description="Controls health and readiness checks after the stack starts.",
    )
    post_deploy: list[PostDeployAction] = Field(
        default_factory=list, description="Actions to run after the stack is up and healthy."
    )


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
