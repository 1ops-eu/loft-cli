"""Tests for the catalog registry (loft-cli/registry/catalog.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loft_cli_core.registry.catalog import (
    CatalogEntry,
    OutputTemplate,
    StepTemplate,
    get_catalog_entry,
    list_catalog_entries,
    register_catalog_entry,
)

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _isolated_registry(monkeypatch):
    """Monkeypatch the catalog registry dict to be empty for the duration of a test."""
    monkeypatch.setattr("loft_cli_core.registry.catalog._CATALOG_REGISTRY", {})


# ------------------------------------------------------------------ #
# Models
# ------------------------------------------------------------------ #


class TestModels:
    def test_catalog_entry_minimal(self):
        entry = CatalogEntry(kind="my_kind", description="Does something.")
        assert entry.kind == "my_kind"
        assert entry.description == "Does something."
        assert entry.fields == []
        assert entry.step_templates == []
        assert entry.outputs == []

    def test_output_template(self):
        out = OutputTemplate(
            name="connection_string", description="DB URL.", example="postgres://..."
        )
        assert out.name == "connection_string"
        assert out.example == "postgres://..."

    def test_output_template_empty_example(self):
        out = OutputTemplate(name="foo", description="bar")
        assert out.example == ""

    def test_step_template(self):
        step = StepTemplate(id="setup", description="Set up the service.")
        assert step.id == "setup"
        assert step.condition is None

    def test_step_template_with_condition(self):
        step = StepTemplate(
            id="wg_setup",
            description="Set up WireGuard.",
            condition={"field_present": "wireguard.enabled"},
        )
        assert step.condition == {"field_present": "wireguard.enabled"}

    def test_catalog_entry_extra_forbid(self):
        with pytest.raises(ValidationError):
            CatalogEntry(kind="foo", description="bar", unexpected_field="oops")

    def test_output_template_extra_forbid(self):
        with pytest.raises(ValidationError):
            OutputTemplate(name="foo", description="bar", bad_field="oops")

    def test_step_template_extra_forbid(self):
        with pytest.raises(ValidationError):
            StepTemplate(id="foo", description="bar", bad_field="oops")


# ------------------------------------------------------------------ #
# register_catalog_entry / get_catalog_entry
# ------------------------------------------------------------------ #


class TestRegisterAndGet:
    def test_register_and_retrieve(self, monkeypatch):
        _isolated_registry(monkeypatch)
        entry = CatalogEntry(kind="bootstrap", description="Harden a host.")
        register_catalog_entry("bootstrap", entry)
        result = get_catalog_entry("bootstrap")
        assert result is entry

    def test_unknown_kind_returns_none(self, monkeypatch):
        _isolated_registry(monkeypatch)
        assert get_catalog_entry("nonexistent") is None

    def test_overwrite_existing_entry(self, monkeypatch):
        _isolated_registry(monkeypatch)
        e1 = CatalogEntry(kind="my_kind", description="First version.")
        e2 = CatalogEntry(kind="my_kind", description="Second version.")
        register_catalog_entry("my_kind", e1)
        register_catalog_entry("my_kind", e2)
        assert get_catalog_entry("my_kind") is e2

    def test_multiple_kinds_independent(self, monkeypatch):
        _isolated_registry(monkeypatch)
        e1 = CatalogEntry(kind="a", description="A.")
        e2 = CatalogEntry(kind="b", description="B.")
        register_catalog_entry("a", e1)
        register_catalog_entry("b", e2)
        assert get_catalog_entry("a") is e1
        assert get_catalog_entry("b") is e2


# ------------------------------------------------------------------ #
# list_catalog_entries
# ------------------------------------------------------------------ #


class TestListCatalogEntries:
    def test_empty_registry(self, monkeypatch):
        _isolated_registry(monkeypatch)
        assert list_catalog_entries() == []

    def test_single_entry(self, monkeypatch):
        _isolated_registry(monkeypatch)
        entry = CatalogEntry(kind="bootstrap", description="Harden.")
        register_catalog_entry("bootstrap", entry)
        result = list_catalog_entries()
        assert len(result) == 1
        assert result[0] is entry

    def test_multiple_entries_in_registration_order(self, monkeypatch):
        _isolated_registry(monkeypatch)
        e1 = CatalogEntry(kind="first", description="First.")
        e2 = CatalogEntry(kind="second", description="Second.")
        e3 = CatalogEntry(kind="third", description="Third.")
        register_catalog_entry("first", e1)
        register_catalog_entry("second", e2)
        register_catalog_entry("third", e3)
        result = list_catalog_entries()
        assert [e.kind for e in result] == ["first", "second", "third"]

    def test_returns_list_not_view(self, monkeypatch):
        _isolated_registry(monkeypatch)
        result = list_catalog_entries()
        assert isinstance(result, list)


# ------------------------------------------------------------------ #
# With outputs and step templates
# ------------------------------------------------------------------ #


class TestCatalogEntryWithOutputs:
    def test_entry_with_outputs(self, monkeypatch):
        _isolated_registry(monkeypatch)
        entry = CatalogEntry(
            kind="postgres_ensure",
            description="Ensure PostgreSQL resources.",
            outputs=[
                OutputTemplate(
                    name="database_url",
                    description="Connection string.",
                    example="postgres://user:***@localhost:5432/mydb",
                )
            ],
        )
        register_catalog_entry("postgres_ensure", entry)
        result = get_catalog_entry("postgres_ensure")
        assert len(result.outputs) == 1
        assert result.outputs[0].name == "database_url"
        assert result.outputs[0].example == "postgres://user:***@localhost:5432/mydb"

    def test_entry_with_step_templates(self, monkeypatch):
        _isolated_registry(monkeypatch)
        entry = CatalogEntry(
            kind="bootstrap",
            description="Bootstrap.",
            step_templates=[
                StepTemplate(
                    id="wireguard_setup",
                    description="Configure WireGuard.",
                    condition={"field_present": "wireguard.enabled"},
                )
            ],
        )
        register_catalog_entry("bootstrap", entry)
        result = get_catalog_entry("bootstrap")
        assert len(result.step_templates) == 1
        assert result.step_templates[0].id == "wireguard_setup"


# ------------------------------------------------------------------ #
# Addon simulation — addon registers an entry after built-ins
# ------------------------------------------------------------------ #


class TestAddonRegistration:
    def test_addon_entry_appears_in_list(self, monkeypatch):
        """Simulate an addon registering a catalog entry after built-ins."""
        _isolated_registry(monkeypatch)

        # Register a built-in first
        builtin = CatalogEntry(kind="bootstrap", description="Built-in kind.")
        register_catalog_entry("bootstrap", builtin)

        # Then an addon registers its own entry
        addon_entry = CatalogEntry(
            kind="pro_deploy",
            description="Browser-triggered deployment via loft-cli-pro.",
            outputs=[
                OutputTemplate(
                    name="deploy_url",
                    description="Public URL of the deployed application.",
                    example="https://myapp.example.com",
                )
            ],
        )
        register_catalog_entry("pro_deploy", addon_entry)

        result = list_catalog_entries()
        kinds = [e.kind for e in result]
        assert "bootstrap" in kinds
        assert "pro_deploy" in kinds
        # Built-in should appear before addon (registration order)
        assert kinds.index("bootstrap") < kinds.index("pro_deploy")

    def test_addon_entry_accessible_via_get(self, monkeypatch):
        _isolated_registry(monkeypatch)
        addon_entry = CatalogEntry(kind="pro_deploy", description="Addon kind.")
        register_catalog_entry("pro_deploy", addon_entry)
        assert get_catalog_entry("pro_deploy") is addon_entry


# ------------------------------------------------------------------ #
# Integration — built-in kinds visible after load_addons()
# ------------------------------------------------------------------ #


class TestBuiltinCatalogEntries:
    def test_bootstrap_registered_after_load_addons(self):
        from loft_cli_core.registry import load_addons

        load_addons()
        entry = get_catalog_entry("bootstrap")
        assert entry is not None
        assert entry.kind == "bootstrap"

    def test_all_builtin_kinds_registered(self):
        from loft_cli_core.registry import load_addons

        load_addons()
        entries = list_catalog_entries()
        kinds = {e.kind for e in entries}
        expected_kinds = {
            "bootstrap",
            "service",
            "file_template",
            "compose_project",
            "stack",
            "http_check",
            "backup_job",
            "systemd_unit",
            "systemd_timer",
            "postgres_ensure",
            "package",
        }
        assert expected_kinds.issubset(kinds)

    def test_bootstrap_has_outputs(self):
        from loft_cli_core.registry import load_addons

        load_addons()
        entry = get_catalog_entry("bootstrap")
        output_names = {o.name for o in entry.outputs}
        assert "ssh_alias" in output_names
        assert "ssh_port" in output_names

    def test_all_outputs_have_nonempty_example(self):
        from loft_cli_core.registry import load_addons

        load_addons()
        for entry in list_catalog_entries():
            for output in entry.outputs:
                assert (
                    output.example
                ), f"OutputTemplate '{output.name}' on kind '{entry.kind}' has empty example"

    def test_output_names_unique_per_kind(self):
        from loft_cli_core.registry import load_addons

        load_addons()
        for entry in list_catalog_entries():
            names = [o.name for o in entry.outputs]
            assert len(names) == len(
                set(names)
            ), f"Kind '{entry.kind}' has duplicate output names: {names}"

    def test_registry_symbols_accessible_from_init(self):
        """Verify addon API surface: all symbols accessible from registry __init__."""
        from loft_cli_core.registry import (
            CatalogEntry,
            OutputTemplate,
            StepTemplate,
            get_catalog_entry,
            list_catalog_entries,
            register_catalog_entry,
        )

        assert callable(register_catalog_entry)
        assert callable(get_catalog_entry)
        assert callable(list_catalog_entries)
        assert CatalogEntry is not None
        assert StepTemplate is not None
        assert OutputTemplate is not None
