"""Unit tests for the fleet selector evaluator (v0.10 feature).

Coverage:
- parse_selector("role=worker") → [("role", "worker")]
- parse_selector("env=staging,role=worker") → two predicates
- parse_selector("badformat") raises ValueError
- evaluate_selector returns True when all predicates match labels dict
- evaluate_selector returns False when any predicate does not match
- AND logic: both predicates must match
- select_specs with no matches raises ValueError with actionable message
- select_specs scans subdirectories recursively and returns results in lexicographic order
"""

from __future__ import annotations

from pathlib import Path

import pytest

from loft_cli.local.selector import evaluate_selector, parse_selector, select_specs


class TestParseSelector:
    """Tests for parse_selector()."""

    def test_single_predicate(self):
        """parse_selector('role=worker') returns one predicate tuple."""
        result = parse_selector("role=worker")
        assert result == [("role", "worker")]

    def test_two_predicates(self):
        """parse_selector('env=staging,role=worker') returns two predicate tuples."""
        result = parse_selector("env=staging,role=worker")
        assert result == [("env", "staging"), ("role", "worker")]

    def test_three_predicates(self):
        """parse_selector handles three comma-separated predicates."""
        result = parse_selector("env=prod,role=worker,region=eu")
        assert result == [("env", "prod"), ("role", "worker"), ("region", "eu")]

    def test_whitespace_stripped(self):
        """parse_selector strips leading/trailing whitespace from key and value."""
        result = parse_selector(" env = staging ")
        assert result == [("env", "staging")]

    def test_bad_format_raises_value_error(self):
        """parse_selector('badformat') raises ValueError (no '=' sign)."""
        with pytest.raises(ValueError, match="badformat"):
            parse_selector("badformat")

    def test_bad_format_in_second_predicate_raises(self):
        """parse_selector raises ValueError when second predicate is malformed."""
        with pytest.raises(ValueError):
            parse_selector("env=staging,badformat")

    def test_empty_expression_raises_value_error(self):
        """parse_selector('') raises ValueError for empty input."""
        with pytest.raises(ValueError):
            parse_selector("")

    def test_whitespace_only_raises_value_error(self):
        """parse_selector('   ') raises ValueError for whitespace-only input."""
        with pytest.raises(ValueError):
            parse_selector("   ")

    def test_value_with_equals_sign(self):
        """parse_selector handles values that contain '=' (only first '=' is the separator)."""
        result = parse_selector("key=val=ue")
        # partition splits on the first '=' only
        assert result == [("key", "val=ue")]


class TestEvaluateSelector:
    """Tests for evaluate_selector()."""

    def test_returns_true_when_all_predicates_match(self):
        """evaluate_selector returns True when all predicates match labels dict."""
        selector = [("env", "staging"), ("role", "worker")]
        labels = {"env": "staging", "role": "worker", "extra": "ignored"}
        assert evaluate_selector(selector, labels) is True

    def test_returns_false_when_one_predicate_does_not_match(self):
        """evaluate_selector returns False when any predicate does not match."""
        selector = [("env", "staging"), ("role", "worker")]
        labels = {"env": "staging", "role": "control"}  # role mismatch
        assert evaluate_selector(selector, labels) is False

    def test_returns_false_when_label_key_missing(self):
        """evaluate_selector returns False when a required key is absent from labels."""
        selector = [("env", "staging")]
        labels = {}  # env key missing
        assert evaluate_selector(selector, labels) is False

    def test_and_logic_both_must_match(self):
        """AND logic: both predicates must match for the result to be True."""
        selector = [("env", "staging"), ("role", "worker")]
        # Only env matches
        labels_partial = {"env": "staging"}
        assert evaluate_selector(selector, labels_partial) is False
        # Both match
        labels_full = {"env": "staging", "role": "worker"}
        assert evaluate_selector(selector, labels_full) is True

    def test_empty_selector_matches_any_labels(self):
        """An empty selector matches any labels dict (vacuously true)."""
        assert evaluate_selector([], {"env": "prod"}) is True
        assert evaluate_selector([], {}) is True

    def test_single_predicate_match(self):
        """Single-predicate selector matches when the label is present with correct value."""
        selector = [("role", "worker")]
        assert evaluate_selector(selector, {"role": "worker"}) is True
        assert evaluate_selector(selector, {"role": "control"}) is False

    def test_value_case_sensitive(self):
        """evaluate_selector is case-sensitive: 'Staging' != 'staging'."""
        selector = [("env", "staging")]
        assert evaluate_selector(selector, {"env": "Staging"}) is False
        assert evaluate_selector(selector, {"env": "staging"}) is True


class TestSelectSpecs:
    """Tests for select_specs()."""

    def _write_spec(self, path: Path, name: str, labels: dict | None = None) -> None:
        """Write a minimal bootstrap spec YAML file with optional labels."""
        import yaml

        data: dict = {
            "kind": "bootstrap",
            "meta": {"name": name},
            "host": {"name": name, "address": "192.168.1.100"},
            "login": {"user": "root", "private_key": "~/.ssh/id_ed25519", "port": 22},
            "local": {"inventory": {"enabled": False}},
        }
        if labels:
            data["meta"]["labels"] = labels
        path.write_text(yaml.dump(data))

    def test_no_matches_raises_value_error(self, tmp_path):
        """select_specs with no matching specs raises ValueError with an actionable message."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        # Write a spec that does NOT match the selector
        spec_file = fleet_dir / "prod-01.yaml"
        self._write_spec(spec_file, "prod-01", labels={"env": "prod"})

        with pytest.raises(ValueError, match="No specs"):
            select_specs(str(fleet_dir), "env=staging")

    def test_matching_spec_is_returned(self, tmp_path):
        """select_specs returns a spec that matches the selector."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_file = fleet_dir / "staging-01.yaml"
        self._write_spec(spec_file, "staging-01", labels={"env": "staging", "role": "worker"})

        results = select_specs(str(fleet_dir), "env=staging")
        assert len(results) == 1
        path_str, _ = results[0]
        assert "staging-01.yaml" in path_str

    def test_non_matching_specs_excluded(self, tmp_path):
        """select_specs excludes specs whose labels do not match the selector."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        self._write_spec(fleet_dir / "staging-01.yaml", "staging-01", labels={"env": "staging"})
        self._write_spec(fleet_dir / "prod-01.yaml", "prod-01", labels={"env": "prod"})

        results = select_specs(str(fleet_dir), "env=staging")
        assert len(results) == 1
        assert "staging-01.yaml" in results[0][0]

    def test_multiple_matching_specs_returned(self, tmp_path):
        """select_specs returns all specs that match the selector."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        self._write_spec(fleet_dir / "worker-01.yaml", "worker-01", labels={"role": "worker"})
        self._write_spec(fleet_dir / "worker-02.yaml", "worker-02", labels={"role": "worker"})
        self._write_spec(fleet_dir / "control-01.yaml", "control-01", labels={"role": "control"})

        results = select_specs(str(fleet_dir), "role=worker")
        assert len(results) == 2
        paths = [r[0] for r in results]
        assert any("worker-01.yaml" in p for p in paths)
        assert any("worker-02.yaml" in p for p in paths)

    def test_results_in_lexicographic_order(self, tmp_path):
        """select_specs returns results in lexicographic (sorted) order."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        # Write in non-alphabetical insertion order
        for name in ("worker-03", "worker-01", "worker-02"):
            self._write_spec(
                fleet_dir / f"{name}.yaml", name, labels={"role": "worker"}
            )

        results = select_specs(str(fleet_dir), "role=worker")
        paths = [r[0] for r in results]
        assert paths == sorted(paths), "Results should be in lexicographic order"

    def test_scans_subdirectories_recursively(self, tmp_path):
        """select_specs scans subdirectories recursively and returns results."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()
        sub_dir = fleet_dir / "region-eu"
        sub_dir.mkdir()

        # Spec in root fleet dir
        self._write_spec(fleet_dir / "eu-root.yaml", "eu-root", labels={"env": "staging"})
        # Spec in subdirectory
        self._write_spec(sub_dir / "eu-sub.yaml", "eu-sub", labels={"env": "staging"})

        results = select_specs(str(fleet_dir), "env=staging")
        assert len(results) == 2
        paths = [r[0] for r in results]
        assert any("eu-root.yaml" in p for p in paths)
        assert any("eu-sub.yaml" in p for p in paths)

    def test_spec_without_labels_not_matched(self, tmp_path):
        """select_specs does not return specs that have no labels (cannot match a selector)."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        # Spec without any labels
        self._write_spec(fleet_dir / "no-labels.yaml", "no-labels")

        with pytest.raises(ValueError, match="No specs"):
            select_specs(str(fleet_dir), "env=staging")

    def test_malformed_selector_raises_value_error(self, tmp_path):
        """select_specs raises ValueError when the selector expression is malformed."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        self._write_spec(fleet_dir / "spec.yaml", "spec", labels={"env": "prod"})

        with pytest.raises(ValueError):
            select_specs(str(fleet_dir), "badformat")

    def test_subdirectory_results_also_lexicographic(self, tmp_path):
        """select_specs returns all recursive results in lexicographic order."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()
        subdir_a = fleet_dir / "a-region"
        subdir_a.mkdir()
        subdir_b = fleet_dir / "b-region"
        subdir_b.mkdir()

        self._write_spec(subdir_b / "worker-b.yaml", "worker-b", labels={"role": "worker"})
        self._write_spec(subdir_a / "worker-a.yaml", "worker-a", labels={"role": "worker"})
        self._write_spec(fleet_dir / "worker-root.yaml", "worker-root", labels={"role": "worker"})

        results = select_specs(str(fleet_dir), "role=worker")
        paths = [r[0] for r in results]
        assert paths == sorted(paths), "Recursive results must be in lexicographic order"
