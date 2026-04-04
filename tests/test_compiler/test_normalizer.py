"""Tests for the normalizer."""

import textwrap

import pytest

from loft_cli.compiler.normalizer import normalize
from loft_cli_core.registry.local_paths import LocalPathsConfig, register_local_paths
from loft_cli_core.specs.loader import load_spec


@pytest.fixture(autouse=True)
def restore_defaults():
    yield
    register_local_paths(LocalPathsConfig())


def test_normalize_sets_ssh_conf_d_path(bootstrap_yaml):
    spec = load_spec(bootstrap_yaml)
    ctx = normalize(spec)
    assert ctx.ssh_conf_d_path is not None
    assert "test-node-1.conf" in str(ctx.ssh_conf_d_path)


def test_normalize_ssh_conf_d_path_uses_loft_cli_subdir(bootstrap_yaml):
    """Default base is ~/.ssh/conf.d/loft-cli/ — not the old ~/.ssh/conf.d/."""
    spec = load_spec(bootstrap_yaml)
    ctx = normalize(spec)
    assert ctx.ssh_conf_d_path is not None
    assert "loft-cli" in str(ctx.ssh_conf_d_path)


def test_normalize_ssh_conf_d_path_honours_custom_base(bootstrap_yaml, tmp_path):
    """Addon override: deeper path propagates through normalize()."""
    custom_base = tmp_path / "mycompany" / "project1" / "ssh"
    register_local_paths(
        LocalPathsConfig(
            ssh_conf_d_base=custom_base,
            wg_state_base=tmp_path / "wg",
        )
    )
    spec = load_spec(bootstrap_yaml)
    ctx = normalize(spec)
    assert ctx.ssh_conf_d_path is not None
    assert ctx.ssh_conf_d_path.parent == custom_base


def test_normalize_sets_db_path(bootstrap_yaml):
    spec = load_spec(bootstrap_yaml)
    ctx = normalize(spec)
    assert ctx.db_path is not None


def test_normalize_resolves_login_key(bootstrap_yaml):
    spec = load_spec(bootstrap_yaml)
    ctx = normalize(spec)
    assert ctx.login_key_path is not None
    assert "id_ed25519" in str(ctx.login_key_path)


def test_normalize_derives_wireguard_public_key(tmp_path):
    """When a valid WireGuard private key is supplied, public key is derived via PyNaCl."""
    import textwrap

    # Write a real WireGuard private key to a temp file
    priv = "8IReoXMQH73MyHqq0PKq7jl1md08E5Cd4wfQf31qXHw="
    expected_pub = "rka+MruYoGYyPaDsjem2kHWxBl59PKUFspMef8GSQng="
    key_file = tmp_path / "wg.key"
    key_file.write_text(priv)

    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(
        textwrap.dedent(f"""
        kind: bootstrap
        meta:
          name: wg-test
          description: ""
        host:
          name: wg-node
          address: 192.168.1.1
        wireguard:
          enabled: true
          interface: wg0
          address: 10.0.0.1/24
          private_key_file: "{key_file}"
          endpoint: "192.168.1.1:51820"
          peer_address: "10.0.0.2/32"
    """)
    )

    spec = load_spec(spec_yaml)
    ctx = normalize(spec)

    assert ctx.wireguard_private_key == priv
    assert ctx.wireguard_public_key == expected_pub
    # Client key pair must be auto-generated (non-empty, valid base64)
    import base64

    assert ctx.wg_client_private_key
    assert ctx.wg_client_public_key
    base64.b64decode(ctx.wg_client_private_key)  # must be valid base64
    base64.b64decode(ctx.wg_client_public_key)


# ---------------------------------------------------------------------------
# Auto-key eager persistence (bug #167)
# ---------------------------------------------------------------------------


def _auto_key_spec_yaml(tmp_path):
    """Write a minimal bootstrap spec with wireguard.enabled=true and no private_key_file."""
    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(
        textwrap.dedent("""\
        kind: bootstrap
        meta:
          name: auto-key-test
          description: ""
        host:
          name: auto-key-node
          address: 192.168.56.20
        wireguard:
          enabled: true
          interface: wg0
          address: 10.10.0.1/24
          endpoint: "192.168.56.20:51820"
          peer_address: "10.10.0.2/32"
    """)
    )
    return spec_yaml


def test_auto_key_persisted_to_disk_after_normalize(tmp_path):
    """Bug #167: normalize() must eagerly write private.key to disk for auto-key specs."""
    wg_base = tmp_path / "wg"
    register_local_paths(LocalPathsConfig(wg_state_base=wg_base))

    spec = load_spec(_auto_key_spec_yaml(tmp_path))
    ctx = normalize(spec)

    key_file = wg_base / "auto-key-node" / "private.key"
    assert key_file.exists(), "private.key must be written to disk during normalize()"
    assert key_file.read_text(encoding="utf-8").strip() == ctx.wireguard_private_key
    assert oct(key_file.stat().st_mode)[-3:] == "600"


def test_auto_client_key_persisted_to_disk_after_normalize(tmp_path):
    """Bug #167: normalize() must eagerly write client.key to disk for auto-key specs."""
    wg_base = tmp_path / "wg"
    register_local_paths(LocalPathsConfig(wg_state_base=wg_base))

    spec = load_spec(_auto_key_spec_yaml(tmp_path))
    ctx = normalize(spec)

    key_file = wg_base / "auto-key-node" / "client.key"
    assert key_file.exists(), "client.key must be written to disk during normalize()"
    assert key_file.read_text(encoding="utf-8").strip() == ctx.wg_client_private_key
    assert oct(key_file.stat().st_mode)[-3:] == "600"


def test_auto_key_stable_across_repeated_normalize(tmp_path):
    """Bug #167: repeated normalize() calls must reuse the same auto-generated key."""
    wg_base = tmp_path / "wg"
    register_local_paths(LocalPathsConfig(wg_state_base=wg_base))

    spec_yaml = _auto_key_spec_yaml(tmp_path)
    ctx1 = normalize(load_spec(spec_yaml))
    ctx2 = normalize(load_spec(spec_yaml))

    assert ctx1.wireguard_private_key == ctx2.wireguard_private_key
    assert ctx1.wg_client_private_key == ctx2.wg_client_private_key


def test_explicit_private_key_file_not_written_to_disk(tmp_path):
    """When private_key_file is set, normalize() must NOT write keys to wg_state_base."""
    wg_base = tmp_path / "wg"
    register_local_paths(LocalPathsConfig(wg_state_base=wg_base))

    priv = "8IReoXMQH73MyHqq0PKq7jl1md08E5Cd4wfQf31qXHw="
    key_file = tmp_path / "wg.key"
    key_file.write_text(priv)

    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(
        textwrap.dedent(f"""\
        kind: bootstrap
        meta:
          name: explicit-key-test
          description: ""
        host:
          name: explicit-key-node
          address: 192.168.1.1
        wireguard:
          enabled: true
          interface: wg0
          address: 10.0.0.1/24
          private_key_file: "{key_file}"
          endpoint: "192.168.1.1:51820"
          peer_address: "10.0.0.2/32"
    """)
    )

    normalize(load_spec(spec_yaml))

    # The wg_state_base must NOT have a private.key written by the normalizer
    state_key = wg_base / "explicit-key-node" / "private.key"
    assert not state_key.exists(), (
        "normalize() must not write private.key when private_key_file is supplied"
    )
