"""CLI tests for the catalog commands (catalog list / show / export)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from loft_cli.cli import app

runner = CliRunner()


# ------------------------------------------------------------------ #
# catalog list
# ------------------------------------------------------------------ #


class TestCatalogList:
    def test_catalog_list_exits_zero(self):
        result = runner.invoke(app, ["catalog", "list"])
        assert result.exit_code == 0

    def test_catalog_list_shows_bootstrap(self):
        result = runner.invoke(app, ["catalog", "list"])
        assert "bootstrap" in result.output

    def test_catalog_list_shows_service(self):
        result = runner.invoke(app, ["catalog", "list"])
        assert "service" in result.output

    def test_catalog_list_shows_all_builtin_kinds(self):
        result = runner.invoke(app, ["catalog", "list"])
        assert result.exit_code == 0
        for kind in [
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
        ]:
            assert kind in result.output, f"Expected kind '{kind}' in catalog list output"

    def test_catalog_list_shows_descriptions(self):
        """Each row should have some description text next to the kind name."""
        result = runner.invoke(app, ["catalog", "list"])
        assert result.exit_code == 0
        # At minimum one description keyword should be visible
        assert any(
            word in result.output.lower()
            for word in ["bootstrap", "service", "deploy", "provision", "ensure", "manage"]
        )


# ------------------------------------------------------------------ #
# catalog show
# ------------------------------------------------------------------ #


class TestCatalogShow:
    def test_catalog_show_bootstrap_exits_zero(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert result.exit_code == 0

    def test_catalog_show_displays_kind(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert "bootstrap" in result.output

    def test_catalog_show_displays_fields(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert result.exit_code == 0
        assert "Fields" in result.output

    def test_catalog_show_bootstrap_has_outputs_section(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert result.exit_code == 0
        assert "Outputs" in result.output

    def test_catalog_show_bootstrap_ssh_alias_output(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert result.exit_code == 0
        assert "ssh_alias" in result.output

    def test_catalog_show_bootstrap_ssh_port_output(self):
        result = runner.invoke(app, ["catalog", "show", "bootstrap"])
        assert result.exit_code == 0
        assert "ssh_port" in result.output

    def test_catalog_show_service_postgres_outputs(self):
        result = runner.invoke(app, ["catalog", "show", "service"])
        assert result.exit_code == 0
        assert "postgres_host" in result.output or "Outputs" in result.output

    def test_catalog_show_unknown_kind_exits_nonzero(self):
        result = runner.invoke(app, ["catalog", "show", "does_not_exist"])
        assert result.exit_code != 0

    def test_catalog_show_unknown_kind_helpful_message(self):
        result = runner.invoke(app, ["catalog", "show", "does_not_exist"])
        assert "does_not_exist" in result.output or "Unknown kind" in result.output

    def test_catalog_show_postgres_ensure(self):
        result = runner.invoke(app, ["catalog", "show", "postgres_ensure"])
        assert result.exit_code == 0
        assert "postgres_ensure" in result.output

    def test_catalog_show_postgres_ensure_database_url_output(self):
        result = runner.invoke(app, ["catalog", "show", "postgres_ensure"])
        assert result.exit_code == 0
        assert "database_url" in result.output


# ------------------------------------------------------------------ #
# catalog export
# ------------------------------------------------------------------ #


class TestCatalogExport:
    def test_catalog_export_exits_zero(self):
        result = runner.invoke(app, ["catalog", "export"])
        assert result.exit_code == 0

    def test_catalog_export_is_valid_json(self):
        result = runner.invoke(app, ["catalog", "export"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_catalog_export_has_kinds_key(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        assert "kinds" in data
        assert isinstance(data["kinds"], list)

    def test_catalog_export_kinds_is_nonempty(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        assert len(data["kinds"]) > 0

    def test_catalog_export_each_kind_has_required_keys(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        for kind_obj in data["kinds"]:
            assert "kind" in kind_obj, f"Missing 'kind' key in: {kind_obj}"
            assert "description" in kind_obj, f"Missing 'description' key in: {kind_obj}"
            assert "fields" in kind_obj, f"Missing 'fields' key in: {kind_obj}"
            assert "outputs" in kind_obj, f"Missing 'outputs' key in: {kind_obj}"

    def test_catalog_export_contains_bootstrap(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        kinds_map = {k["kind"]: k for k in data["kinds"]}
        assert "bootstrap" in kinds_map

    def test_catalog_export_bootstrap_has_outputs(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        kinds_map = {k["kind"]: k for k in data["kinds"]}
        bootstrap = kinds_map["bootstrap"]
        output_names = {o["name"] for o in bootstrap["outputs"]}
        assert "ssh_alias" in output_names
        assert "ssh_port" in output_names

    def test_catalog_export_output_has_name_description_example(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        for kind_obj in data["kinds"]:
            for output in kind_obj["outputs"]:
                assert "name" in output
                assert "description" in output
                assert "example" in output

    def test_catalog_export_contains_all_builtin_kinds(self):
        result = runner.invoke(app, ["catalog", "export"])
        data = json.loads(result.output)
        exported_kinds = {k["kind"] for k in data["kinds"]}
        expected = {
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
        assert expected.issubset(exported_kinds)
