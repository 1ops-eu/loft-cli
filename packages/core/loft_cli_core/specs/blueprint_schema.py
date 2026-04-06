"""Pydantic v2 models for kind: blueprint YAML specs.

A blueprint is a reusable, parameterised composition of existing spec kinds.
It declares ``inputs`` (with optional defaults), optional ``includes`` (references
to other blueprint files), and inline ``resources`` (same shape as StackResourceBlock).

Design principles
-----------------
- Blueprints are expanded into primitive steps during planning — no blueprint
  wrappers appear in the final plan.
- Input tokens (``${name}``) in resource configs are substituted before delegation
  to per-kind planners.
- Include files are merged into the parent ``resources`` list in order at load time.
- Circular includes are detected at validation time.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from loft_cli_core.specs.bootstrap_schema import HostBlock, MetaBlock
from loft_cli_core.specs.stack_schema import StackLocalBlock, StackLoginBlock


class BlueprintInputSpec(BaseModel):
    """Declaration of a single input parameter accepted by a blueprint.

    Inputs are referenced as ``${name}`` tokens inside resource configs.
    """

    model_config = ConfigDict(extra="forbid")

    name: str  # input name (used as ${name} in resources)
    required: bool = True  # when True, a value must be supplied at plan time
    default: str | None = None  # only meaningful when required=False
    description: str = ""  # human-readable hint


class BlueprintIncludeBlock(BaseModel):
    """A reference to another blueprint or resource file to be merged in.

    The included file's resources are appended to the parent's resources list
    in the order the include appears.  ``with_`` bindings override the included
    file's input defaults.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    include: str  # local or repo-relative path (e.g. ./fragment.yaml, blueprints/caddy.yaml)
    with_: Annotated[dict[str, str], Field(default_factory=dict, alias="with")] = Field(
        default_factory=dict
    )


class BlueprintResourceBlock(BaseModel):
    """An inline resource within a blueprint.

    Same shape as ``StackResourceBlock`` in stack_schema.py so that the same
    topological sort and planner delegation logic can be reused.
    """

    model_config = ConfigDict(extra="forbid")

    name: str  # unique within the blueprint (e.g. "caddy")
    kind: str  # the spec kind: "compose_project", "backup_job", etc.
    config: dict = Field(default_factory=dict)  # kind-specific config block
    depends_on: list[str] = Field(default_factory=list)  # other resource names in this blueprint


class BlueprintSpec(BaseModel):
    """Spec for a reusable, parameterised composition of infrastructure resources."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["blueprint"]
    meta: MetaBlock
    host: HostBlock
    login: StackLoginBlock = Field(default_factory=StackLoginBlock)
    local: StackLocalBlock = Field(default_factory=StackLocalBlock)
    inputs: list[BlueprintInputSpec] = Field(default_factory=list)
    includes: list[BlueprintIncludeBlock] = Field(default_factory=list)
    resources: list[BlueprintResourceBlock] = Field(default_factory=list)
