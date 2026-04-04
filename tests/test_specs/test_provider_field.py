"""Tests for host.provider field in BootstrapSpec (WP #176).

Ensures that:
- BootstrapSpec accepts ``host.provider: hetzner`` without a ValidationError.
- ``host.provider`` defaults to the empty string when omitted.
- The loader (load_spec) accepts specs with and without provider.
- Invalid extra fields are still rejected (extra="forbid" is intact).
"""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from loft_cli_core.specs.bootstrap_schema import BootstrapSpec
from loft_cli_core.specs.loader import SpecLoadError, load_spec

# ---------------------------------------------------------------------------
# Helper: minimal valid bootstrap YAML with a provider field
# ---------------------------------------------------------------------------

_MINIMAL_WITH_PROVIDER = textwrap.dedent("""\
    kind: bootstrap
    meta:
      name: test-provider-node
    host:
      name: hz-node-1
      address: 192.0.2.10
      provider: hetzner
""")

_MINIMAL_WITHOUT_PROVIDER = textwrap.dedent("""\
    kind: bootstrap
    meta:
      name: test-no-provider
    host:
      name: vg-node-1
      address: 192.168.56.10
""")

_MINIMAL_WITH_EMPTY_PROVIDER = textwrap.dedent("""\
    kind: bootstrap
    meta:
      name: test-empty-provider
    host:
      name: bare-node-1
      address: 10.0.0.5
      provider: ""
""")


# ---------------------------------------------------------------------------
# Schema-level tests (BootstrapSpec direct construction)
# ---------------------------------------------------------------------------


def test_host_provider_accepted_by_schema():
    """host.provider: hetzner must not raise ValidationError."""
    spec = BootstrapSpec.model_validate(
        {
            "kind": "bootstrap",
            "meta": {"name": "hz-test"},
            "host": {"name": "hz-1", "address": "192.0.2.1", "provider": "hetzner"},
        }
    )
    assert spec.host.provider == "hetzner"


def test_host_provider_defaults_to_empty_string():
    """host.provider must default to '' when omitted."""
    spec = BootstrapSpec.model_validate(
        {
            "kind": "bootstrap",
            "meta": {"name": "bare-test"},
            "host": {"name": "bare-1", "address": "10.0.0.1"},
        }
    )
    assert spec.host.provider == ""


def test_host_provider_empty_string_explicit():
    """Explicitly setting host.provider to '' is valid."""
    spec = BootstrapSpec.model_validate(
        {
            "kind": "bootstrap",
            "meta": {"name": "explicit-empty"},
            "host": {"name": "n1", "address": "10.0.0.2", "provider": ""},
        }
    )
    assert spec.host.provider == ""


@pytest.mark.parametrize(
    "provider_value",
    ["hetzner", "digitalocean", "aws", "gcp", "azure", "vultr", "linode", "my-custom-provider"],
)
def test_host_provider_accepts_various_string_values(provider_value: str):
    """provider field accepts arbitrary non-empty strings."""
    spec = BootstrapSpec.model_validate(
        {
            "kind": "bootstrap",
            "meta": {"name": "multi-provider-test"},
            "host": {"name": "node-1", "address": "10.1.2.3", "provider": provider_value},
        }
    )
    assert spec.host.provider == provider_value


def test_host_extra_field_still_rejected():
    """extra='forbid' must still reject unknown fields on host."""
    with pytest.raises(ValidationError, match="extra"):
        BootstrapSpec.model_validate(
            {
                "kind": "bootstrap",
                "meta": {"name": "extra-field-test"},
                "host": {
                    "name": "n1",
                    "address": "10.0.0.1",
                    "unknown_field": "should-fail",
                },
            }
        )


# ---------------------------------------------------------------------------
# Loader-level tests (load_spec from YAML files)
# ---------------------------------------------------------------------------


def test_load_spec_with_provider(tmp_path):
    """load_spec must accept a spec file containing host.provider: hetzner."""
    f = tmp_path / "bootstrap-provider.yaml"
    f.write_text(_MINIMAL_WITH_PROVIDER)
    spec = load_spec(f)
    assert isinstance(spec, BootstrapSpec)
    assert spec.host.provider == "hetzner"
    assert spec.host.name == "hz-node-1"


def test_load_spec_without_provider(tmp_path):
    """load_spec must work with specs that omit host.provider."""
    f = tmp_path / "bootstrap-no-provider.yaml"
    f.write_text(_MINIMAL_WITHOUT_PROVIDER)
    spec = load_spec(f)
    assert isinstance(spec, BootstrapSpec)
    assert spec.host.provider == ""


def test_load_spec_with_empty_provider(tmp_path):
    """load_spec must accept host.provider: '' (explicit empty string)."""
    f = tmp_path / "bootstrap-empty-provider.yaml"
    f.write_text(_MINIMAL_WITH_EMPTY_PROVIDER)
    spec = load_spec(f)
    assert isinstance(spec, BootstrapSpec)
    assert spec.host.provider == ""


def test_load_spec_provider_preserved_through_roundtrip(tmp_path):
    """host.provider value must survive a model_dump → model_validate roundtrip."""
    f = tmp_path / "bootstrap-roundtrip.yaml"
    f.write_text(_MINIMAL_WITH_PROVIDER)
    spec = load_spec(f)
    dumped = spec.model_dump()
    spec2 = BootstrapSpec.model_validate(dumped)
    assert spec2.host.provider == "hetzner"


def test_load_spec_no_validation_error_for_hetzner_provider(tmp_path):
    """Regression: host.provider: hetzner must NOT raise SpecLoadError / ValidationError."""
    f = tmp_path / "regression-176.yaml"
    f.write_text(_MINIMAL_WITH_PROVIDER)
    # Must not raise
    try:
        spec = load_spec(f)
    except (SpecLoadError, Exception) as exc:
        pytest.fail(f"Unexpected error loading spec with host.provider: {exc}")
    assert spec.host.provider == "hetzner"
