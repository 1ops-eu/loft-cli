"""Load and parse YAML specs into typed Pydantic models."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

# Matches ${...} tokens — the full token including optional prefix and default.
_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Maximum include depth to prevent runaway recursion before circular-include
# detection fires.
_MAX_INCLUDE_DEPTH = 10


class SpecLoadError(Exception):
    """Raised when a spec file cannot be loaded or parsed."""


def load_env_file(path: Path) -> dict[str, str]:
    """Load a .env file and return a dict of variable name → value.

    Supports:
    - Lines of the form ``KEY=VALUE`` or ``KEY="VALUE"`` / ``KEY='VALUE'``
    - ``export KEY=VALUE``
    - Comments (lines starting with ``#``)
    - Blank lines (ignored)

    Does NOT modify ``os.environ``; the caller is responsible for that.
    """
    env: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for _lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip optional 'export ' prefix
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


def _resolve_values(obj: Any, *, strict: bool = True, _path: str = "") -> Any:
    """Recursively resolve ``${[prefix:]key[:-default]}`` tokens in a YAML structure.

    Token syntax
    ------------
    ``${VAR}``
        Bare reference — shorthand for ``${env:VAR}``.  Permanent backward
        compat; will never be deprecated.

    ``${env:VAR}``
        Explicit environment variable lookup via the ``env`` resolver.

    ``${file:/path/to/file}``
        Read file contents via the built-in ``file`` resolver.

    ``${prefix:key}``
        Dispatch to an addon-registered resolver (e.g. ``sops``, ``vault``).

    ``${VAR:-default}``
        Use *default* if the resolved value is ``None`` (key not found).
        Works with any prefix: ``${env:VAR:-fallback}``,
        ``${file:/opt/key.pub:-}`` etc.

    Parameters
    ----------
    obj:
        The parsed YAML data (nested dicts, lists, scalars).
    strict:
        When ``True`` (default), raise :class:`SpecLoadError` if a token
        cannot be resolved and has no default value.  When ``False``
        ("passthrough"), leave the ``${...}`` token unchanged.
    _path:
        Internal — tracks the YAML field path for error messages.
    """
    if isinstance(obj, str):
        # Import lazily so this function stays usable before load_addons() runs.
        from loft_cli_core.registry.resolvers import get_resolver, list_resolvers

        def replace(m: re.Match) -> str:
            token = m.group(1)
            location = f" in field '{_path}'" if _path else ""

            # 1. Split off default value (shell convention: :-)
            if ":-" in token:
                ref_part, default = token.split(":-", 1)
            else:
                ref_part, default = token, None

            # 2. Extract prefix (first colon in ref_part).
            #    No colon → bare ${VAR} → permanent shorthand for ${env:VAR}.
            if ":" in ref_part:
                prefix, key = ref_part.split(":", 1)
            else:
                prefix, key = "env", ref_part

            # 3. Resolve via registry.
            resolver = get_resolver(prefix)
            if resolver is None:
                known = ", ".join(list_resolvers()) or "none"
                raise SpecLoadError(
                    f"Unknown resolver '{prefix}' in '${{{token}}}'{location}. "
                    f"Registered resolvers: {known}. "
                    f"Is an addon missing?"
                )

            val = resolver(key)

            # 4. Value found — return it.
            if val is not None:
                return val

            # 5. Value not found — try default.
            if default is not None:
                return default

            # 6. No default — strict vs passthrough.
            if strict:
                raise SpecLoadError(
                    f"Unresolved variable '${{{token}}}'{location}: "
                    f"resolver '{prefix}' returned no value for key '{key}'"
                )
            return m.group(0)  # passthrough: leave ${...} unchanged

        return _ENV_PATTERN.sub(replace, obj)
    elif isinstance(obj, dict):
        return {
            k: _resolve_values(v, strict=strict, _path=f"{_path}.{k}" if _path else k)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            _resolve_values(item, strict=strict, _path=f"{_path}[{i}]")
            for i, item in enumerate(obj)
        ]
    return obj


# Keep the old name available so any code that imported _resolve_env_vars
# directly (e.g. existing tests) continues to work without change.
_resolve_env_vars = _resolve_values


def _resolve_includes(raw: dict, base_dir: Path, *, depth: int = 0) -> dict:
    """Resolve ``includes:`` directives in a raw YAML dict before Pydantic validation.

    This function is a **no-op** for non-blueprint specs (any spec whose ``kind``
    field is not ``"blueprint"``).

    For blueprint specs it:
    1. Iterates the ``includes`` list (each item must have an ``include`` key).
    2. Resolves each include path relative to ``base_dir``.
    3. Loads the included file recursively (also calling ``_resolve_includes``).
    4. Merges the included file's ``resources`` into the parent ``resources`` list
       (included resources come *before* the parent's inline resources, in order).
    5. Applies the include's ``with`` bindings as input overrides on the included
       file's ``inputs`` defaults.
    6. Enforces a maximum depth of :data:`_MAX_INCLUDE_DEPTH`.

    Parameters
    ----------
    raw:
        Parsed YAML dict (before Pydantic validation).
    base_dir:
        Directory of the spec file being processed — used to resolve relative paths.
    depth:
        Current include depth (starts at 0 for the top-level file).
    """
    if raw.get("kind") != "blueprint":
        # Passthrough: non-blueprint specs are unaffected.
        return raw

    if depth > _MAX_INCLUDE_DEPTH:
        raise SpecLoadError(
            f"Include depth exceeded maximum ({_MAX_INCLUDE_DEPTH}). "
            "Possible circular include — run 'loft-cli validate' to diagnose."
        )

    includes_list = raw.get("includes", [])
    if not includes_list:
        return raw

    # We'll build the merged resources list: included resources first, then inline.
    merged_resources: list[dict] = []

    for inc in includes_list:
        if not isinstance(inc, dict):
            continue
        include_path_str = inc.get("include", "")
        if not include_path_str:
            continue

        # Resolve the include path
        include_path = Path(include_path_str)
        if not include_path.is_absolute():
            include_path = (base_dir / include_path_str).resolve()

        if not include_path.exists():
            raise SpecLoadError(
                f"Include target '{include_path}' not found (referenced from '{base_dir}')"
            )

        # Load the included file (raw YAML, no env resolution yet)
        try:
            included_text = include_path.read_text(encoding="utf-8")
            included_raw = yaml.safe_load(included_text)
        except yaml.YAMLError as exc:
            raise SpecLoadError(
                f"YAML parse error in included file '{include_path}': {exc}"
            ) from exc

        if not isinstance(included_raw, dict):
            raise SpecLoadError(f"Included file '{include_path}' must be a YAML mapping")

        # Apply ``with`` bindings: override the included file's input defaults
        with_bindings: dict[str, str] = inc.get("with", {})
        if with_bindings and "inputs" in included_raw:
            patched_inputs = []
            for inp in included_raw["inputs"]:
                if isinstance(inp, dict) and inp.get("name") in with_bindings:
                    inp = dict(inp)
                    inp["default"] = with_bindings[inp["name"]]
                    inp["required"] = False
                patched_inputs.append(inp)
            included_raw["inputs"] = patched_inputs

        # Recursively resolve includes in the included file
        included_raw = _resolve_includes(
            included_raw,
            include_path.parent,
            depth=depth + 1,
        )

        # Collect resources from the included file
        merged_resources.extend(included_raw.get("resources", []))

    # Append the parent's own inline resources after the included ones
    merged_resources.extend(raw.get("resources", []))

    # Return a copy of raw with merged resources (do not mutate the original)
    result = dict(raw)
    result["resources"] = merged_resources
    return result


def load_spec(
    path: Path,
    *,
    strict_env: bool = True,
    env_file: Path | None = None,
    env_files: list[Path] | None = None,
) -> Any:
    """Load and parse a YAML spec file into a typed model.

    Parameters
    ----------
    path:
        Path to the YAML spec file.
    strict_env:
        When True (default), unresolved ``${...}`` references raise an error.
        When False, they are left unchanged (passthrough mode).
    env_file:
        Optional path to a single ``.env`` file (backward-compatible).
    env_files:
        Optional list of ``.env`` file paths.  Files are loaded in order;
        later files override earlier ones, but existing ``os.environ``
        values always take precedence.  When both ``env_file`` and
        ``env_files`` are provided, ``env_file`` is prepended to the list.
    """
    # Ensure built-in and addon kinds are registered (idempotent).
    from loft_cli_core.registry import get_spec_model, list_spec_kinds, load_addons

    load_addons()

    if not path.exists():
        raise SpecLoadError(f"Spec file not found: {path}")

    # Build the ordered list of env files (RFC 008: overlay layering).
    all_env_files: list[Path] = []
    if env_file is not None:
        all_env_files.append(env_file)
    if env_files:
        all_env_files.extend(env_files)

    # Load env files in order: later files override earlier, but existing
    # os.environ values always take precedence.
    merged_env: dict[str, str] = {}
    for ef in all_env_files:
        if not ef.exists():
            raise SpecLoadError(f"Env file not found: {ef}")
        merged_env.update(load_env_file(ef))
    for key, value in merged_env.items():
        os.environ.setdefault(key, value)

    text = path.read_text(encoding="utf-8")

    # Support multiple YAML documents separated by ---
    try:
        documents = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        raise SpecLoadError(f"YAML parse error in {path}: {e}") from e

    # Filter out empty documents (e.g. trailing ---)
    documents = [d for d in documents if d is not None]

    if not documents:
        raise SpecLoadError(f"Spec file is empty: {path}")

    specs = []
    for doc_idx, raw in enumerate(documents):
        if not isinstance(raw, dict):
            raise SpecLoadError(
                f"Document {doc_idx + 1} in {path} must be a YAML mapping, got {type(raw).__name__}"
            )

        # Resolve include directives for blueprint specs before Pydantic validation.
        # This merges included files' resources into the parent's resources list.
        # Non-blueprint specs are unaffected (passthrough).
        raw = _resolve_includes(raw, path.parent)

        kind = raw.get("kind")
        model_class = get_spec_model(kind)
        if model_class is None:
            known = ", ".join(list_spec_kinds()) or "none"
            raise SpecLoadError(
                f"Unknown spec kind '{kind}' in document {doc_idx + 1}. Supported: {known}"
            )

        try:
            data = _resolve_values(raw, strict=strict_env)
        except SpecLoadError:
            raise

        try:
            specs.append(model_class.model_validate(data))
        except Exception as e:
            if type(e).__name__ == "ValidationError":
                raise SpecLoadError(
                    f"Spec validation error in {path} (document {doc_idx + 1}):\n{e}"
                ) from e
            raise

    # Return single spec for backward compatibility, list for multi-doc
    if len(specs) == 1:
        return specs[0]
    return specs
