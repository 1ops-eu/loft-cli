"""Selector module for multi-host fleet operations.

Provides label-based filtering of spec files in a directory so that fleet
commands can target a subset of hosts with a single selector expression.

Selector expression syntax
--------------------------
A selector is a comma-separated list of ``key=value`` predicate pairs.
All predicates must match (AND semantics).  Example::

    role=worker,env=staging

Label matching
--------------
Labels are read from the ``meta.labels`` mapping in each spec YAML file.
If a spec does not have a ``meta.labels`` field it is treated as having an
empty label set and will not match any non-empty selector.

Usage
-----
::

    from loft_cli.local.selector import select_specs

    paths = select_specs("/path/to/specs", "role=worker,env=staging")
    for path in paths:
        # run apply pipeline on each matching spec
        ...
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_selector(expr: str) -> dict[str, str]:
    """Parse a selector expression into a dict of key→value predicates.

    Parameters
    ----------
    expr:
        A comma-separated list of ``key=value`` pairs, e.g.
        ``"role=worker,env=staging"``.

    Returns
    -------
    dict[str, str]
        A mapping of label key to expected value.

    Raises
    ------
    ValueError
        If *expr* is empty or any predicate is malformed (missing ``=``,
        empty key, or empty value).
    """
    if not expr or not expr.strip():
        raise ValueError("Selector expression must not be empty")

    predicates: dict[str, str] = {}
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Malformed selector predicate '{part}': expected 'key=value' format")
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed selector predicate '{part}': key must not be empty")
        if not value:
            raise ValueError(f"Malformed selector predicate '{part}': value must not be empty")
        predicates[key] = value

    if not predicates:
        raise ValueError("Selector expression must contain at least one 'key=value' predicate")

    return predicates


def evaluate_selector(selector: dict[str, str], labels: dict[str, str]) -> bool:
    """Evaluate whether a set of labels satisfies all selector predicates.

    Implements AND semantics: every predicate in *selector* must be present
    in *labels* with a matching value.

    Parameters
    ----------
    selector:
        The parsed selector dict returned by :func:`parse_selector`.
    labels:
        The label dict from the spec's ``meta.labels`` field (may be empty).

    Returns
    -------
    bool
        ``True`` if all predicates match, ``False`` otherwise.
    """
    return all(labels.get(key) == expected for key, expected in selector.items())


def select_specs(spec_dir: str | Path, selector_expr: str) -> list[Path]:
    """Scan *spec_dir* for YAML spec files that match *selector_expr*.

    Files are scanned recursively in lexicographic (sorted) order.  For each
    file the raw YAML is read and ``meta.labels`` is extracted (if present).
    The file is included in the result only if all selector predicates match
    the spec's labels.

    Parameters
    ----------
    spec_dir:
        Directory to search for ``*.yaml`` / ``*.yml`` files.
    selector_expr:
        Selector expression string, e.g. ``"role=worker,env=staging"``.

    Returns
    -------
    list[Path]
        Sorted list of matching spec file paths.

    Raises
    ------
    ValueError
        If *selector_expr* is invalid (propagated from :func:`parse_selector`),
        or if no spec files in *spec_dir* match the selector (actionable
        message includes which labels were scanned and the selector used).
    """
    import yaml

    spec_dir = Path(spec_dir)
    selector = parse_selector(selector_expr)

    # Collect all YAML files in lexicographic order.
    yaml_files: list[Path] = sorted(
        [p for p in spec_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".yaml", ".yml")]
    )

    matched: list[Path] = []
    scanned_labels: list[tuple[str, dict[str, str]]] = []

    for spec_path in yaml_files:
        try:
            raw_text = spec_path.read_text(encoding="utf-8")
            # Use safe_load_all to handle multi-document files; take the first
            # document only for label matching (primary spec document).
            documents = [d for d in yaml.safe_load_all(raw_text) if d is not None]
        except Exception:
            # Skip unparseable files silently.
            continue

        for raw in documents:
            if not isinstance(raw, dict):
                continue

            meta = raw.get("meta", {}) or {}
            labels: dict[str, str] = meta.get("labels", {}) or {}
            # Coerce values to strings for comparison robustness.
            labels = {str(k): str(v) for k, v in labels.items()}

            scanned_labels.append((str(spec_path), labels))

            if evaluate_selector(selector, labels):
                matched.append(spec_path)
                break  # Only match a file once even if it has multiple documents.

    if not matched:
        # Build an actionable error message.
        scanned_summary = (
            ", ".join(f"{path}({lbl})" for path, lbl in scanned_labels)
            if scanned_labels
            else "none"
        )
        raise ValueError(
            f"No spec files in '{spec_dir}' matched selector '{selector_expr}'. "
            f"Scanned {len(scanned_labels)} file(s). "
            f"Labels found: [{scanned_summary}]. "
            f"Check that your spec files define 'meta.labels' matching the selector."
        )

    return matched
