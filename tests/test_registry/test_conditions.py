"""Tests for the condition DSL evaluator (loft-cli/registry/conditions.py)."""

from __future__ import annotations

from loft_cli_core.registry.conditions import evaluate_condition

# ------------------------------------------------------------------ #
# _resolve_path (tested indirectly via evaluate_condition)
# ------------------------------------------------------------------ #


class TestFieldPresent:
    def test_simple_key_present(self):
        ctx = {"wireguard": {"enabled": True}}
        assert evaluate_condition({"field_present": "wireguard.enabled"}, ctx) is True

    def test_simple_key_absent(self):
        ctx = {"wireguard": {}}
        assert evaluate_condition({"field_present": "wireguard.enabled"}, ctx) is False

    def test_top_level_key_present(self):
        ctx = {"feature": "active"}
        assert evaluate_condition({"field_present": "feature"}, ctx) is True

    def test_top_level_key_absent(self):
        ctx = {}
        assert evaluate_condition({"field_present": "feature"}, ctx) is False

    def test_none_value_treated_as_absent(self):
        ctx = {"wireguard": {"enabled": None}}
        assert evaluate_condition({"field_present": "wireguard.enabled"}, ctx) is False

    def test_empty_string_treated_as_absent(self):
        ctx = {"name": ""}
        assert evaluate_condition({"field_present": "name"}, ctx) is False

    def test_empty_list_treated_as_absent(self):
        ctx = {"items": []}
        assert evaluate_condition({"field_present": "items"}, ctx) is False

    def test_false_value_treated_as_absent(self):
        ctx = {"enabled": False}
        assert evaluate_condition({"field_present": "enabled"}, ctx) is False

    def test_zero_treated_as_present(self):
        """Zero is a valid value (distinct from None/empty), so it should be present."""
        ctx = {"count": 0}
        # 0 is not in our "absent" list (None, "", [], False), so it IS present
        assert evaluate_condition({"field_present": "count"}, ctx) is True

    def test_deep_nested_path(self):
        ctx = {"a": {"b": {"c": "value"}}}
        assert evaluate_condition({"field_present": "a.b.c"}, ctx) is True

    def test_deep_nested_path_missing_intermediate(self):
        ctx = {"a": {}}
        assert evaluate_condition({"field_present": "a.b.c"}, ctx) is False

    def test_intermediate_is_not_dict(self):
        ctx = {"a": "string_not_dict"}
        assert evaluate_condition({"field_present": "a.b"}, ctx) is False


# ------------------------------------------------------------------ #
# field_equals
# ------------------------------------------------------------------ #


class TestFieldEquals:
    def test_string_match(self):
        ctx = {"host": {"os_family": "debian"}}
        cond = {"field_equals": {"path": "host.os_family", "value": "debian"}}
        assert evaluate_condition(cond, ctx) is True

    def test_string_no_match(self):
        ctx = {"host": {"os_family": "alpine"}}
        cond = {"field_equals": {"path": "host.os_family", "value": "debian"}}
        assert evaluate_condition(cond, ctx) is False

    def test_integer_match(self):
        ctx = {"ssh": {"port": 2222}}
        cond = {"field_equals": {"path": "ssh.port", "value": 2222}}
        assert evaluate_condition(cond, ctx) is True

    def test_integer_no_match(self):
        ctx = {"ssh": {"port": 22}}
        cond = {"field_equals": {"path": "ssh.port", "value": 2222}}
        assert evaluate_condition(cond, ctx) is False

    def test_boolean_match(self):
        ctx = {"enabled": True}
        cond = {"field_equals": {"path": "enabled", "value": True}}
        assert evaluate_condition(cond, ctx) is True

    def test_none_match(self):
        ctx = {"key": None}
        cond = {"field_equals": {"path": "key", "value": None}}
        assert evaluate_condition(cond, ctx) is True

    def test_missing_path_vs_none(self):
        ctx = {}
        cond = {"field_equals": {"path": "missing", "value": None}}
        # _resolve_path returns None for missing — so this is True
        assert evaluate_condition(cond, ctx) is True

    def test_missing_path_vs_string_is_false(self):
        ctx = {}
        cond = {"field_equals": {"path": "missing", "value": "x"}}
        assert evaluate_condition(cond, ctx) is False


# ------------------------------------------------------------------ #
# all
# ------------------------------------------------------------------ #


class TestAll:
    def test_all_true(self):
        ctx = {"a": "x", "b": "y"}
        cond = {
            "all": [
                {"field_present": "a"},
                {"field_present": "b"},
            ]
        }
        assert evaluate_condition(cond, ctx) is True

    def test_one_false(self):
        ctx = {"a": "x"}
        cond = {
            "all": [
                {"field_present": "a"},
                {"field_present": "b"},  # missing
            ]
        }
        assert evaluate_condition(cond, ctx) is False

    def test_empty_all_is_true(self):
        """Vacuous truth: all([]) is True in Python."""
        assert evaluate_condition({"all": []}, {}) is True

    def test_all_with_non_list_returns_false(self):
        assert evaluate_condition({"all": "not_a_list"}, {}) is False

    def test_nested_all(self):
        ctx = {"a": "x", "b": "y", "c": "z"}
        cond = {
            "all": [
                {"field_present": "a"},
                {"all": [{"field_present": "b"}, {"field_present": "c"}]},
            ]
        }
        assert evaluate_condition(cond, ctx) is True


# ------------------------------------------------------------------ #
# any
# ------------------------------------------------------------------ #


class TestAny:
    def test_one_true(self):
        ctx = {"a": "x"}
        cond = {
            "any": [
                {"field_present": "a"},
                {"field_present": "missing"},
            ]
        }
        assert evaluate_condition(cond, ctx) is True

    def test_all_false(self):
        ctx = {}
        cond = {
            "any": [
                {"field_present": "a"},
                {"field_present": "b"},
            ]
        }
        assert evaluate_condition(cond, ctx) is False

    def test_empty_any_is_false(self):
        """Vacuous: any([]) is False in Python."""
        assert evaluate_condition({"any": []}, {}) is False

    def test_any_with_non_list_returns_false(self):
        assert evaluate_condition({"any": 42}, {}) is False


# ------------------------------------------------------------------ #
# not
# ------------------------------------------------------------------ #


class TestNot:
    def test_not_true_becomes_false(self):
        ctx = {"x": "value"}
        assert evaluate_condition({"not": {"field_present": "x"}}, ctx) is False

    def test_not_false_becomes_true(self):
        ctx = {}
        assert evaluate_condition({"not": {"field_present": "x"}}, ctx) is True

    def test_not_non_dict_returns_false(self):
        assert evaluate_condition({"not": "bad"}, {}) is False

    def test_double_not(self):
        ctx = {"x": "value"}
        cond = {"not": {"not": {"field_present": "x"}}}
        assert evaluate_condition(cond, ctx) is True


# ------------------------------------------------------------------ #
# Unknown / malformed conditions
# ------------------------------------------------------------------ #


class TestUnknown:
    def test_unknown_condition_type_returns_false(self):
        assert evaluate_condition({"unknown_op": "value"}, {}) is False

    def test_non_dict_condition_returns_false(self):
        assert evaluate_condition("not_a_dict", {}) is False  # type: ignore[arg-type]

    def test_none_condition_returns_false(self):
        assert evaluate_condition(None, {}) is False  # type: ignore[arg-type]

    def test_empty_condition_returns_false(self):
        assert evaluate_condition({}, {}) is False


# ------------------------------------------------------------------ #
# Combinations reflecting real-world usage
# ------------------------------------------------------------------ #


class TestRealWorldPatterns:
    def test_wireguard_step_condition(self):
        """WireGuard step: only when wireguard.enabled is truthy."""
        cond = {"field_present": "wireguard.enabled"}
        assert evaluate_condition(cond, {"wireguard": {"enabled": True}}) is True
        assert evaluate_condition(cond, {"wireguard": {"enabled": False}}) is False
        assert evaluate_condition(cond, {}) is False

    def test_debian_only_step_condition(self):
        """Step active only on Debian."""
        cond = {"field_equals": {"path": "host.os_family", "value": "debian"}}
        assert evaluate_condition(cond, {"host": {"os_family": "debian"}}) is True
        assert evaluate_condition(cond, {"host": {"os_family": "alpine"}}) is False

    def test_complex_combined_condition(self):
        """Step active when WireGuard present AND host is debian."""
        cond = {
            "all": [
                {"field_present": "wireguard.enabled"},
                {"field_equals": {"path": "host.os_family", "value": "debian"}},
            ]
        }
        ctx_match = {"wireguard": {"enabled": True}, "host": {"os_family": "debian"}}
        ctx_no_wg = {"host": {"os_family": "debian"}}
        ctx_wrong_os = {"wireguard": {"enabled": True}, "host": {"os_family": "alpine"}}

        assert evaluate_condition(cond, ctx_match) is True
        assert evaluate_condition(cond, ctx_no_wg) is False
        assert evaluate_condition(cond, ctx_wrong_os) is False

    def test_optional_step_with_any(self):
        """Step active when either postgres or mysql is present."""
        cond = {
            "any": [
                {"field_present": "postgres.enabled"},
                {"field_present": "mysql.enabled"},
            ]
        }
        assert evaluate_condition(cond, {"postgres": {"enabled": True}}) is True
        assert evaluate_condition(cond, {"mysql": {"enabled": True}}) is True
        assert evaluate_condition(cond, {}) is False
