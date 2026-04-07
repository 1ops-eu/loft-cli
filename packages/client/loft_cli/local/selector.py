"""Fleet selector: parse, evaluate, and filter spec files by label expressions.

Usage
-----
    from loft_cli.local.selector import parse_selector, evaluate_selector, select_specs

    # Parse a selector expression like "env=staging,role=worker"
    predicates = parse_selector("env=staging,role=worker")

    # Check whether a labels dict matches all predicates (AND)
    match = evaluate_selector(predicates, {"env": "staging", "role": "worker"})  # True

    # Scan a directory and return (filepath, parsed_spec) tuples for matching specs
    results = select_specs("./hosts/", "env=staging")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_selector(expr: str) -> list[tuple[str, str]]:
    """Parse a comma-separated ``key=value`` selector expression.

    Parameters
    ----------
    expr:
        Selector string, e.g. ``"role=worker"`` or ``"env=staging,role=worker"``.

    Returns
    -------
    list[tuple[str, str]]
        List of ``(key, value)`` predicate pairs.

    Raises
    ------
    ValueError
        If *expr* is empty or any predicate is not in ``key=value`` format.
    """
    if not expr or not expr.strip():
        raise ValueError("Selector cannot be empty")

    predicates: list[tuple[str, str]] = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid selector '{part}': must be key=value format")
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid selector '{part}': key must not be empty")
        predicates.append((key, value))

    if not predicates:
        raise ValueError("Selector cannot be empty")

    return predicates


def evaluate_selector(selector: list[tuple[str, str]], labels: dict[str, str]) -> bool:
    """Return True when *labels* satisfies all predicates in *selector* (AND).

    Parameters
    ----------
    selector:
        List of ``(key, value)`` pairs as returned by :func:`parse_selector`.
    labels:
        Labels dict from ``parsed_spec.meta.labels``.
    """
    return all(labels.get(key) == value for key, value in selector)


def select_specs(
    spec_dir: str,
    selector_expr: str,
) -> list[tuple[str, Any]]:
    """Scan *spec_dir* recursively for YAML specs matching *selector_expr*.

    Files are scanned in lexicographic order.  Each file is parsed with
    :func:`loft_cli_core.specs.loader.load_spec` (strict env is disabled so
    specs with unresolved ``${VAR}`` references are still loadable for label
    inspection).

    Parameters
    ----------
    spec_dir:
        Path to the directory to scan.
    selector_expr:
        Selector expression string (forwarded to :func:`parse_selector`).

    Returns
    -------
    list[tuple[str, Any]]
        List of ``(filepath, parsed_spec)`` tuples for matching specs, in
        lexicographic path order.

    Raises
    ------
    ValueError
        - If *selector_expr* is empty or malformed (forwarded from
          :func:`parse_selector`).
        - If no specs in *spec_dir* match the selector.
    """
    from loft_cli_core.specs.loader import SpecLoadError, load_spec

    predicates = parse_selector(selector_expr)

    dir_path = Path(spec_dir)
    if not dir_path.is_dir():
        raise ValueError(f"Fleet directory does not exist or is not a directory: {spec_dir}")

    # Collect all YAML files in lexicographic order
    yaml_files = sorted(
        p for p in dir_path.rglob("*") if p.suffix in (".yaml", ".yml") and p.is_file()
    )

    results: list[tuple[str, Any]] = []
    for yaml_path in yaml_files:
        try:
            parsed = load_spec(yaml_path, strict_env=False)
        except (SpecLoadError, Exception):
            # Skip files that can't be parsed (wrong format, unknown kind, etc.)
            continue

        # Handle multi-doc specs — iterate each document
        specs = parsed if isinstance(parsed, list) else [parsed]
        for spec in specs:
            meta = getattr(spec, "meta", None)
            if meta is None:
                continue
            labels = getattr(meta, "labels", {}) or {}
            if evaluate_selector(predicates, labels):
                results.append((str(yaml_path), spec))

    if not results:
        raise ValueError(
            f"No specs matched selector '{selector_expr}' in directory '{spec_dir}'. "
            "Check that your spec files have the correct meta.labels."
        )

    return results


def _scan_all_specs(spec_dir: str) -> list[tuple[str, Any]]:
    """Return all parseable specs from *spec_dir* (no filtering).

    Used internally by fleet commands when no ``--selector`` is provided.
    Returns list of ``(filepath, parsed_spec)`` tuples in lexicographic order.
    Silently skips files that cannot be parsed.

    Raises
    ------
    ValueError
        If the directory contains no parseable specs.
    """
    from loft_cli_core.specs.loader import SpecLoadError, load_spec

    dir_path = Path(spec_dir)
    if not dir_path.is_dir():
        raise ValueError(f"Fleet directory does not exist or is not a directory: {spec_dir}")

    yaml_files = sorted(
        p for p in dir_path.rglob("*") if p.suffix in (".yaml", ".yml") and p.is_file()
    )

    results: list[tuple[str, Any]] = []
    for yaml_path in yaml_files:
        try:
            parsed = load_spec(yaml_path, strict_env=False)
        except (SpecLoadError, Exception):
            continue

        specs = parsed if isinstance(parsed, list) else [parsed]
        for spec in specs:
            meta = getattr(spec, "meta", None)
            if meta is None:
                continue
            results.append((str(yaml_path), spec))

    if not results:
        raise ValueError(f"No parseable specs found in directory '{spec_dir}'.")

    return results
