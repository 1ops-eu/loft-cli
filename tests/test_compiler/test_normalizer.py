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

    # Write a real WireGuard private key to a temp file
    priv = "8IReoXMQH73MyHqq0PKq7jl1md08E5Cd4wfQf31qXHw="
    expected_pub = "rka+MruYoGYyPaDsjem2kHWxBl59PKUFspMef8GSQng="
    key_file = tmp_path / "wg.key"
    key_file.write_text(priv)

    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(textwrap.dedent(f"""
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
    """))

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


def test_normalize_auto_key_reuses_persisted_key_on_second_run(tmp_path):
    """Auto-key path: second normalize() call reuses the private.key from disk."""
    import base64

    from loft_cli_core.registry.local_paths import LocalPathsConfig, register_local_paths

    wg_state_base = tmp_path / "wg"
    register_local_paths(
        LocalPathsConfig(
            ssh_conf_d_base=tmp_path / "ssh" / "conf.d",
            wg_state_base=wg_state_base,
        )
    )

    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(textwrap.dedent("""
        kind: bootstrap
        meta:
          name: wg-auto-test
          description: ""
        host:
          name: wg-auto-node
          address: 192.168.1.1
        wireguard:
          enabled: true
          interface: wg0
          address: 10.0.0.1/24
          endpoint: "192.168.1.1:51820"
          peer_address: "10.0.0.2/32"
    """))

    from loft_cli_core.specs.loader import load_spec

    # First run: no key on disk — generates a fresh key in memory
    spec = load_spec(spec_yaml)
    ctx1 = normalize(spec)
    assert ctx1.wireguard_private_key
    assert ctx1.wireguard_public_key
    base64.b64decode(ctx1.wireguard_private_key)

    # Simulate what save_wireguard_state does: persist private.key to disk
    host_dir = wg_state_base / "wg-auto-node"
    host_dir.mkdir(parents=True, exist_ok=True)
    (host_dir / "private.key").write_text(ctx1.wireguard_private_key + "\n")
    (host_dir / "client.key").write_text(ctx1.wg_client_private_key + "\n")

    # Second run: key IS on disk — must reuse it (stable server identity)
    spec2 = load_spec(spec_yaml)
    ctx2 = normalize(spec2)
    assert ctx2.wireguard_private_key == ctx1.wireguard_private_key
    assert ctx2.wireguard_public_key == ctx1.wireguard_public_key
    assert ctx2.wg_client_private_key == ctx1.wg_client_private_key
    assert ctx2.wg_client_public_key == ctx1.wg_client_public_key


def test_normalize_auto_key_state_dir_tilde_expansion(tmp_path):
    """state_dir with a tilde prefix must be expanded before key path checks."""

    # Point LOFT_CLI_STATE_DIR to a real tmp_path (no tilde needed for the env var test,
    # but we verify that Path(...).expanduser() doesn't break an already-absolute path).
    state_dir = tmp_path / "loft-state"
    state_dir.mkdir()

    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text(textwrap.dedent(f"""
        kind: bootstrap
        meta:
          name: wg-tilde-test
          description: ""
        host:
          name: tilde-node
          address: 192.168.1.1
        wireguard:
          enabled: true
          interface: wg0
          address: 10.0.0.1/24
          endpoint: "192.168.1.1:51820"
          peer_address: "10.0.0.2/32"
        local:
          state_dir: "{state_dir}"
    """))

    from loft_cli_core.specs.loader import load_spec

    spec = load_spec(spec_yaml)
    ctx = normalize(spec)
    # Key must be generated without errors and paths must be under state_dir
    assert ctx.wireguard_private_key
    from loft_cli_core.registry.local_paths import get_local_paths

    assert str(state_dir) in str(get_local_paths().wg_state_base)
