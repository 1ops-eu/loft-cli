"""Fleet spec selection via label selectors.

Provides three public functions:

    parse_selector(expr)          -- "role=worker,env=staging" -> [("role","worker"), ...]
    evaluate_selector(sel, labs)  -- AND-match all predicates against a labels dict
    select_specs(spec_dir, expr)  -- glob a directory, parse YAMLs, return matching (path, spec) pairs
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_selector(expr: str) -> list[tuple[str, str]]:
    """Parse a comma-separated label selector expression.

    Each predicate must have the form ``key=value``.  Returns a list of
    ``(key, value)`` tuples — one per predicate.

    Parameters
    ----------
    expr:
        Selector expression, e.g. ``"role=worker,env=staging"``.

    Raises
    ------
    ValueError
        If *expr* is empty or any predicate is not in ``key=value`` form.
    """
    expr = expr.strip()
    if not expr:
        raise ValueError("Selector expression must not be empty")

    predicates: list[tuple[str, str]] = []
    for raw_part in expr.split(","):
        part = raw_part.strip()
        if "=" not in part:
            raise ValueError(f"Malformed selector predicate {part!r}: expected 'key=value' form")
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed selector predicate {part!r}: key must not be empty")
        predicates.append((key, value))

    return predicates


def evaluate_selector(
    selector: list[tuple[str, str]],
    labels: dict[str, str],
) -> bool:
    """Return True iff *labels* satisfies every predicate in *selector*.

    The evaluation is a logical AND across all predicates: every ``(key,
    value)`` pair in *selector* must exist in *labels* with an equal value.
    An empty *selector* matches any labels dict.

    Parameters
    ----------
    selector:
        List of ``(key, value)`` tuples as produced by :func:`parse_selector`.
    labels:
        Mapping of label key → value to test against.
    """
    return all(labels.get(key) == value for key, value in selector)


def select_specs(
    spec_dir: str | Path,
    selector_expr: str,
) -> list[tuple[str, Any]]:
    """Discover and filter YAML spec files by a label selector.

    Recursively globs *spec_dir* for ``*.yaml`` and ``*.yml`` files, loads
    each as a loft-cli spec (with ``strict_env=False`` so environment
    variables need not be set), extracts ``meta.labels`` from the spec (or
    the raw YAML if Pydantic validation is not applicable), and returns those
    whose labels match *selector_expr*.

    Parameters
    ----------
    spec_dir:
        Directory to search recursively.
    selector_expr:
        Label selector expression, e.g. ``"role=worker,env=staging"``.

    Returns
    -------
    list of (path_str, spec) tuples
        Each element is the spec file's absolute path (as a string) and the
        parsed spec object.  Returned in filesystem glob order.

    Raises
    ------
    ValueError
        If *selector_expr* is malformed or if no specs in *spec_dir* match
        the selector.
    """
    import yaml

    from loft_cli_core.specs.loader import load_spec

    spec_dir = Path(spec_dir)
    selector = parse_selector(selector_expr)

    # Collect all YAML files recursively.
    yaml_files: list[Path] = sorted(list(spec_dir.rglob("*.yaml")) + list(spec_dir.rglob("*.yml")))

    matches: list[tuple[str, Any]] = []

    for yaml_path in yaml_files:
        # Extract labels from raw YAML without Pydantic validation so that
        # (a) env-var placeholders don't need to be present, and
        # (b) we don't fail on unknown kinds or missing required fields.
        try:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            # Skip unparseable files silently.
            continue

        if not isinstance(raw, dict):
            continue

        # Labels live at meta.labels — a plain str→str mapping.
        meta = raw.get("meta", {}) or {}
        labels: dict[str, str] = {}
        if isinstance(meta, dict):
            raw_labels = meta.get("labels", {}) or {}
            if isinstance(raw_labels, dict):
                labels = {str(k): str(v) for k, v in raw_labels.items()}

        if not evaluate_selector(selector, labels):
            continue

        # Parse the spec properly (passthrough env vars so no ${...} errors).
        try:
            spec = load_spec(yaml_path, strict_env=False)
        except Exception:
            # If the spec can't be fully loaded (missing env, unknown kind, …)
            # still include it so callers can inspect or skip it themselves.
            spec = raw

        matches.append((str(yaml_path), spec))

    if not matches:
        raise ValueError(f"No specs in '{spec_dir}' matched selector '{selector_expr}'")

    return matches
