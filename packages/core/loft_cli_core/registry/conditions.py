"""Condition DSL evaluator for StepTemplate conditions.

Conditions allow a kind to declare "include this step only when field X is
set" without duplicating planner logic.  They make catalog entries
self-describing in terms of when their steps are active.

Supported condition types
-------------------------

**Field presence** — true when the value at the path is not None/empty::

    {"field_present": "wireguard.enabled"}

**Field equality** — true when the value at the path equals *value*::

    {"field_equals": {"path": "host.os_family", "value": "debian"}}

**Boolean combinations**::

    {"all": [<condition>, ...]}   # all sub-conditions must be true
    {"any": [<condition>, ...]}   # at least one sub-condition must be true
    {"not": <condition>}          # inverts the sub-condition

Path resolution
---------------
Dot-separated paths are resolved against the context ``dict`` using nested
key traversal.  A missing intermediate key returns ``False`` (never an error).

Example usage inside a StepTemplate::

    StepTemplate(
        id="wireguard_setup",
        description="Generate WireGuard keypair and write server config",
        condition={"field_present": "wireguard.enabled"},
    )
"""

from __future__ import annotations


def _resolve_path(path: str, context: dict) -> object:
    """Traverse *context* using dot-separated *path*.

    Returns the value at the path, or ``None`` if any intermediate key is
    missing or the context is not a dict at some level.
    """
    parts = path.split(".")
    current: object = context
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def evaluate_condition(condition: dict, context: dict) -> bool:
    """Evaluate a condition dict against *context*.

    Parameters
    ----------
    condition:
        A condition dict as described in the module docstring.
    context:
        A plain ``dict`` representation of the spec (e.g. from
        ``spec.model_dump()``).

    Returns
    -------
    ``True`` if the condition is satisfied, ``False`` otherwise.  Missing
    paths always return ``False`` rather than raising an exception.
    """
    if not isinstance(condition, dict):
        return False

    # ── field_present ──────────────────────────────────────────────────
    if "field_present" in condition:
        path: str = condition["field_present"]
        value = _resolve_path(path, context)
        if value is None:
            return False
        # Also treat empty string, empty list, and False as "not present"
        return not (value == "" or value == [] or value is False)

    # ── field_equals ───────────────────────────────────────────────────
    if "field_equals" in condition:
        spec = condition["field_equals"]
        path = spec.get("path", "")
        expected = spec.get("value")
        value = _resolve_path(path, context)
        return value == expected

    # ── all ────────────────────────────────────────────────────────────
    if "all" in condition:
        sub_conditions = condition["all"]
        if not isinstance(sub_conditions, list):
            return False
        return all(evaluate_condition(c, context) for c in sub_conditions)

    # ── any ────────────────────────────────────────────────────────────
    if "any" in condition:
        sub_conditions = condition["any"]
        if not isinstance(sub_conditions, list):
            return False
        return any(evaluate_condition(c, context) for c in sub_conditions)

    # ── not ────────────────────────────────────────────────────────────
    if "not" in condition:
        sub_condition = condition["not"]
        if not isinstance(sub_condition, dict):
            return False
        return not evaluate_condition(sub_condition, context)

    # Unknown condition type — default to False rather than raising
    return False
