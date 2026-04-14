"""Catalog registry — the 8th registry in the loft-cli registry series.

Maps kind strings to ``CatalogEntry`` objects that describe each kind's
fields, step templates, and observable outputs.  This registry makes
loft-cli self-describing: ``loft-cli catalog list/show/export`` all draw
from this registry.

Extending the catalog from an external addon
---------------------------------------------
External addons register catalog entries the same way they register spec
kinds, planners, etc.:

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

``list_catalog_entries()`` returns built-in entries first (in registration
order) followed by addon-registered entries — this is the natural result of
``load_addons()`` loading built-ins before external addons.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OutputTemplate(BaseModel):
    """Declares what a kind produces after apply."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    example: str = ""


class StepTemplate(BaseModel):
    """A named step blueprint that can be conditionally included in a plan."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    condition: dict | None = None  # evaluated by Condition DSL (see conditions.py)
    code_block: str | None = None  # shell command template with <placeholders>


class CatalogEntry(BaseModel):
    """Full self-description of a registered kind."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    description: str
    fields: list[dict] = []
    step_templates: list[StepTemplate] = []
    outputs: list[OutputTemplate] = []


# ---------------------------------------------------------------------------
# Internal registry store
# ---------------------------------------------------------------------------

_CATALOG_REGISTRY: dict[str, CatalogEntry] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register_catalog_entry(kind: str, entry: CatalogEntry) -> None:
    """Register a catalog entry for *kind*, replacing any previous entry."""
    _CATALOG_REGISTRY[kind] = entry


def get_catalog_entry(kind: str) -> CatalogEntry | None:
    """Return the ``CatalogEntry`` for *kind*, or ``None`` if not registered."""
    return _CATALOG_REGISTRY.get(kind)


def list_catalog_entries() -> list[CatalogEntry]:
    """Return all registered catalog entries in registration order."""
    return list(_CATALOG_REGISTRY.values())
