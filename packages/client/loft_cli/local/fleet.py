"""Fleet spec selection — scan a directory and filter by label selectors.

A fleet directory contains one YAML spec file per host.  The ``select_specs``
function scans the directory for ``*.yaml`` files and optionally filters them
using a label selector expression.

Selector syntax
---------------
A selector is a comma-separated list of ``key=value`` terms, all of which must
match for a spec to be included (AND logic).  An empty selector matches every
spec in the directory.

Examples::

    ""               → all specs
    "role=worker"    → specs whose meta.labels.role == "worker"
    "env=staging,role=worker" → specs where both labels match
"""

from __future__ import annotations

from pathlib import Path


def _parse_selector(selector: str) -> list[tuple[str, str]]:
    """Parse a selector string into a list of (key, value) pairs.

    Parameters
    ----------
    selector:
        Comma-separated ``key=value`` terms.  Whitespace around delimiters is
        stripped.  An empty string returns an empty list (matches everything).

    Raises
    ------
    ValueError
        When a term is not in ``key=value`` form.
    """
    if not selector.strip():
        return []
    terms: list[tuple[str, str]] = []
    for term in selector.split(","):
        term = term.strip()
        if not term:
            continue
        if "=" not in term:
            raise ValueError(
                f"Invalid selector term '{term}': expected 'key=value' format. "
                f"Example: 'role=worker' or 'env=staging,role=worker'"
            )
        key, _, value = term.partition("=")
        terms.append((key.strip(), value.strip()))
    return terms


def _spec_matches(spec_path: Path, terms: list[tuple[str, str]]) -> bool:
    """Return True if the spec at *spec_path* matches all label selector *terms*.

    The spec is parsed with ``strict_env=False`` so that unresolved ``${VAR}``
    references do not cause errors during fleet scanning (env vars may not be
    set on the operator's machine for all fleet hosts).

    Parameters
    ----------
    spec_path:
        Path to a YAML spec file.
    terms:
        Parsed selector terms from :func:`_parse_selector`.  An empty list
        means "match everything".
    """
    if not terms:
        return True

    try:
        from loft_cli_core.specs.loader import load_spec

        spec_or_list = load_spec(spec_path, strict_env=False)
    except Exception:
        # Unparseable files are silently excluded from the fleet.
        return False

    specs = spec_or_list if isinstance(spec_or_list, list) else [spec_or_list]

    # A file matches if ANY of its documents (for multi-doc files) satisfies all
    # selector terms.  In practice fleet files are single-document.
    for spec in specs:
        labels: dict[str, str] = getattr(getattr(spec, "meta", None), "labels", {}) or {}
        if all(labels.get(k) == v for k, v in terms):
            return True

    return False


def select_specs(fleet_dir: Path, selector: str = "") -> list[Path]:
    """Return spec files in *fleet_dir* that match *selector*.

    Parameters
    ----------
    fleet_dir:
        Directory to scan.  Only ``*.yaml`` files are considered; subdirectories
        are not traversed.
    selector:
        Label selector expression (see module docstring).  An empty string
        selects every spec file in the directory.

    Returns
    -------
    list[Path]
        Sorted list of matching spec paths (sorted by filename for deterministic
        ordering).

    Raises
    ------
    ValueError
        When *selector* contains an invalid term.
    """
    terms = _parse_selector(selector)
    candidates = sorted(fleet_dir.glob("*.yaml"))
    return [p for p in candidates if _spec_matches(p, terms)]
