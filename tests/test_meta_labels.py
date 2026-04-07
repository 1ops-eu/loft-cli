"""Unit tests for MetaBlock labels schema (v0.10 fleet feature).

Coverage:
- A spec file with meta.labels parses without error and labels are accessible.
- A spec file without meta.labels parses without error (defaults to empty dict).
- Unknown fields in meta (other than name, description, labels) raise ValidationError.
"""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from loft_cli_core.specs.bootstrap_schema import MetaBlock


class TestMetaBlockLabels:
    """Tests for the labels field on MetaBlock."""

    def test_meta_labels_with_values_parses_ok(self):
        """MetaBlock with labels dict parses without error."""
        block = MetaBlock(name="staging-worker", labels={"env": "staging", "role": "worker"})
        assert block.labels == {"env": "staging", "role": "worker"}

    def test_meta_labels_single_label(self):
        """MetaBlock with a single label parses ok."""
        block = MetaBlock(name="prod-node", labels={"env": "prod"})
        assert block.labels["env"] == "prod"

    def test_meta_labels_defaults_to_empty_dict(self):
        """MetaBlock without labels defaults to an empty dict."""
        block = MetaBlock(name="no-labels")
        assert block.labels == {}

    def test_meta_labels_explicit_empty_dict(self):
        """MetaBlock with labels={} is valid and stays empty."""
        block = MetaBlock(name="empty-labels", labels={})
        assert block.labels == {}

    def test_meta_labels_multiple_labels(self):
        """MetaBlock accepts multiple labels."""
        block = MetaBlock(
            name="multi",
            labels={"env": "staging", "role": "worker", "region": "eu-west"},
        )
        assert len(block.labels) == 3
        assert block.labels["region"] == "eu-west"

    def test_meta_unknown_field_raises_validation_error(self):
        """Unknown fields in meta (other than name, description, labels) raise ValidationError."""
        with pytest.raises(ValidationError):
            MetaBlock(name="test", unknown_field="should-fail")

    def test_meta_unknown_field_raises_validation_error_extra_key(self):
        """A second unknown field variant also raises ValidationError."""
        with pytest.raises(ValidationError):
            MetaBlock(name="test", bogus_key="value", another_bogus="also-bad")

    def test_meta_description_is_optional(self):
        """MetaBlock with only name and labels is valid (description defaults to '')."""
        block = MetaBlock(name="minimal", labels={"env": "test"})
        assert block.description == ""
        assert block.labels == {"env": "test"}

    def test_meta_description_and_labels_together(self):
        """MetaBlock with name, description, and labels all set."""
        block = MetaBlock(
            name="full",
            description="A fully populated meta block",
            labels={"env": "staging"},
        )
        assert block.description == "A fully populated meta block"
        assert block.labels == {"env": "staging"}


class TestMetaLabelsViaSpecFile:
    """Integration-style tests: load a real YAML spec file and verify meta.labels."""

    def test_spec_with_labels_loads_correctly(self, tmp_path):
        """A spec file with meta.labels: {env: staging, role: worker} parses without error."""
        spec_text = textwrap.dedent("""\
            kind: bootstrap
            meta:
              name: staging-worker-01
              labels:
                env: staging
                role: worker
            host:
              name: staging-worker-01
              address: 192.168.1.10
            login:
              user: root
              private_key: ~/.ssh/id_ed25519
              port: 22
            local:
              inventory:
                enabled: false
        """)
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec_text)

        from loft_cli_core.specs.loader import load_spec

        spec = load_spec(spec_file)
        assert spec.meta.labels == {"env": "staging", "role": "worker"}

    def test_spec_without_labels_parses_ok(self, tmp_path):
        """A spec file without meta.labels parses without error and defaults to empty dict."""
        spec_text = textwrap.dedent("""\
            kind: bootstrap
            meta:
              name: no-labels-host
            host:
              name: no-labels-host
              address: 192.168.1.20
            login:
              user: root
              private_key: ~/.ssh/id_ed25519
              port: 22
            local:
              inventory:
                enabled: false
        """)
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec_text)

        from loft_cli_core.specs.loader import load_spec

        spec = load_spec(spec_file)
        assert spec.meta.labels == {}

    def test_spec_with_unknown_meta_field_fails(self, tmp_path):
        """Unknown fields in meta (other than name, description, labels) raise SpecLoadError."""
        spec_text = textwrap.dedent("""\
            kind: bootstrap
            meta:
              name: bad-meta
              unknown_meta_field: should-fail
            host:
              name: bad-meta
              address: 192.168.1.30
        """)
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec_text)

        from loft_cli_core.specs.loader import SpecLoadError, load_spec

        with pytest.raises(SpecLoadError):
            load_spec(spec_file)
