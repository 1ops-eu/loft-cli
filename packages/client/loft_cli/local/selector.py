"""Selector utilities for fleet commands.

Provides helpers to filter a directory of YAML specs by label expressions,
following the pattern ``key=value[,key=value,...]``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_selector(expr: str) -> list[tuple[str, str]]:
    """Parse a selector expression into a list of (key, value) predicates.

    Parameters
    ----------
    expr:
        Comma-separated ``key=value`` pairs, e.g. ``"env=prod,team=platform"``.

    Returns
    -------
    list[tuple[str, str]]
        Ordered list of ``(key, value)`` tuples representing AND-combined predicates.

    Raises
    ------
    ValueError
        If ``expr`` is empty, or if any term does not contain ``=``.
    """
    expr = expr.strip()
    if not expr:
        raise ValueError("Selector expression must not be empty")

    predicates: list[tuple[str, str]] = []
    for term in expr.split(","):
        term = term.strip()
        if "=" not in term:
            raise ValueError(f"Invalid selector term '{term}': expected 'key=value' format")
        key, _, value = term.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid selector term '{term}': key must not be empty")
        predicates.append((key, value))

    return predicates


def evaluate_selector(selector: list[tuple[str, str]], labels: dict[str, str]) -> bool:
    """Return True if *all* predicates in ``selector`` match the given ``labels``.

    Parameters
    ----------
    selector:
        List of ``(key, value)`` predicates as returned by :func:`parse_selector`.
    labels:
        The label dict from a spec's ``meta.labels`` field.

    Returns
    -------
    bool
        ``True`` when every predicate matches (AND semantics); ``False`` otherwise.
    """
    return all(labels.get(key) == value for key, value in selector)


def select_specs(spec_dir: str, selector_expr: str) -> list[tuple[str, Any]]:
    """Recursively scan *spec_dir* for YAML specs and return those matching *selector_expr*.

    Parameters
    ----------
    spec_dir:
        Path to the directory to scan (searched recursively for ``*.yaml``/``*.yml``).
    selector_expr:
        Comma-separated ``key=value`` label selector expression.

    Returns
    -------
    list[tuple[str, Any]]
        Ordered list of ``(path_str, spec)`` pairs for every spec whose
        ``meta.labels`` match all predicates in *selector_expr*.
        ``path_str`` is the absolute path to the YAML file as a string.

    Raises
    ------
    ValueError
        If *selector_expr* is invalid (propagated from :func:`parse_selector`).
    ValueError
        If no specs match the selector expression.
    """
    from loft_cli_core.specs.loader import load_spec

    selector = parse_selector(selector_expr)

    root = Path(spec_dir).expanduser().resolve()
    yaml_files: list[Path] = sorted(list(root.rglob("*.yaml")) + list(root.rglob("*.yml")))

    matches: list[tuple[str, Any]] = []
    for yaml_path in yaml_files:
        try:
            loaded = load_spec(yaml_path, strict_env=False)
        except Exception:
            # Skip files that are not valid loft-cli specs
            continue

        # load_spec may return a single spec or a list (multi-document)
        specs: list[Any] = loaded if isinstance(loaded, list) else [loaded]
        for spec in specs:
            meta = getattr(spec, "meta", None)
            if meta is None:
                continue
            labels: dict[str, str] = getattr(meta, "labels", {}) or {}
            if evaluate_selector(selector, labels):
                matches.append((str(yaml_path), spec))

    if not matches:
        raise ValueError(f"No specs found matching selector '{selector_expr}' in '{spec_dir}'")

    return matches
