"""
Tests for scripts/promote_rule.py

Tests cover:
- Severity promotion transitions (warn → error → fatal)
- Dry-run mode
- Error handling (file not found, rule not found, invalid YAML)
- Maximum severity detection
- YAML file reading/writing
"""

import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

# Add scripts directory to path for importing
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from promote_rule import (
    promote_rule,
    normalize_severity,
    get_next_severity,
    find_and_promote_rule,
    load_rules_file,
    save_rules_file
)


class TestNormalizeSeverity:
    """Test severity normalization."""

    def test_normalize_warn(self):
        """Test warn variants."""
        assert normalize_severity('warn') == 'warn'
        assert normalize_severity('warning') == 'warn'
        assert normalize_severity('WARNING') == 'warn'

    def test_normalize_error(self):
        """Test error variants."""
        assert normalize_severity('error') == 'error'
        assert normalize_severity('err') == 'error'
        assert normalize_severity('ERROR') == 'error'

    def test_normalize_fatal(self):
        """Test fatal variants."""
        assert normalize_severity('fatal') == 'fatal'
        assert normalize_severity('critical') == 'fatal'
        assert normalize_severity('FATAL') == 'fatal'

    def test_normalize_unknown_passthrough(self):
        """Unknown severities pass through."""
        assert normalize_severity('unknown') == 'unknown'


class TestGetNextSeverity:
    """Test severity promotion logic."""

    def test_promote_warn_to_error(self):
        """Warn promotes to error."""
        assert get_next_severity('warn') == 'error'

    def test_promote_error_to_fatal(self):
        """Error promotes to fatal."""
        assert get_next_severity('error') == 'fatal'

    def test_fatal_is_maximum(self):
        """Fatal cannot be promoted further."""
        assert get_next_severity('fatal') is None

    def test_promote_with_aliases(self):
        """Aliases work for promotion."""
        assert get_next_severity('warning') == 'error'
        assert get_next_severity('err') == 'fatal'
        assert get_next_severity('critical') is None

    def test_unknown_severity_raises(self):
        """Unknown severity raises ValueError."""
        with pytest.raises(ValueError, match="Unknown severity level"):
            get_next_severity('invalid')


class TestLoadSaveRulesFile:
    """Test YAML file operations."""

    def test_load_rules_file_success(self, tmp_path):
        """Successfully load valid YAML file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: warn
""", encoding='utf-8')

        rules = load_rules_file(rules_file)
        assert rules['version'] == 1
        assert len(rules['rules']) == 1
        assert rules['rules'][0]['id'] == 'TEST001'

    def test_load_rules_file_not_found(self, tmp_path):
        """Non-existent file raises FileNotFoundError."""
        rules_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Rules file not found"):
            load_rules_file(rules_file)

    def test_load_rules_file_invalid_yaml(self, tmp_path):
        """Malformed YAML raises YAMLError."""
        rules_file = tmp_path / "invalid.yaml"
        rules_file.write_text("invalid: yaml: content: [", encoding='utf-8')

        with pytest.raises(yaml.YAMLError, match="Invalid YAML"):
            load_rules_file(rules_file)

    def test_save_rules_file_preserves_structure(self, tmp_path):
        """Saved YAML maintains structure."""
        rules_file = tmp_path / "rules.yaml"
        original_rules = {
            'version': 1,
            'rules': [
                {'id': 'TEST001', 'severity': 'error', 'description': 'Test rule'}
            ]
        }

        save_rules_file(rules_file, original_rules)

        # Reload and verify
        loaded_rules = load_rules_file(rules_file)
        assert loaded_rules == original_rules


class TestFindAndPromoteRule:
    """Test rule finding and promotion logic."""

    def test_find_and_promote_success(self):
        """Successfully find and promote rule."""
        rules = {
            'rules': [
                {'id': 'TEST001', 'severity': 'warn'},
                {'id': 'TEST002', 'severity': 'error'}
            ]
        }

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=False)

        assert success is True
        assert old == 'warn'
        assert new == 'error'
        assert rules['rules'][0]['severity'] == 'error'

    def test_find_and_promote_dry_run(self):
        """Dry-run doesn't modify rules."""
        rules = {
            'rules': [
                {'id': 'TEST001', 'severity': 'warn'}
            ]
        }

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=True)

        assert success is True
        assert old == 'warn'
        assert new == 'error'
        # Original severity unchanged
        assert rules['rules'][0]['severity'] == 'warn'

    def test_find_and_promote_rule_not_found(self):
        """Rule not found returns (False, None, None)."""
        rules = {
            'rules': [
                {'id': 'TEST001', 'severity': 'warn'}
            ]
        }

        success, old, new = find_and_promote_rule(rules, 'NONEXISTENT', dry_run=False)

        assert success is False
        assert old is None
        assert new is None

    def test_find_and_promote_already_max_severity(self):
        """Rule at max severity returns (False, severity, None)."""
        rules = {
            'rules': [
                {'id': 'TEST001', 'severity': 'fatal'}
            ]
        }

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=False)

        assert success is False
        assert old == 'fatal'
        assert new is None

    def test_find_and_promote_missing_severity_field(self):
        """Rule without severity field returns (False, None, None)."""
        rules = {
            'rules': [
                {'id': 'TEST001'}  # No severity field
            ]
        }

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=False)

        assert success is False
        assert old is None
        assert new is None

    def test_find_and_promote_no_rules_key(self):
        """Missing 'rules' key returns (False, None, None)."""
        rules = {'version': 1}  # No 'rules' key

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=False)

        assert success is False
        assert old is None
        assert new is None

    def test_find_and_promote_non_list_rules(self):
        """Non-list 'rules' value returns (False, None, None)."""
        rules = {'rules': 'not-a-list'}

        success, old, new = find_and_promote_rule(rules, 'TEST001', dry_run=False)

        assert success is False
        assert old is None
        assert new is None


class TestPromoteRuleCommand:
    """Test the Click command interface."""

    def test_promote_rule_success(self, tmp_path):
        """Successfully promote rule severity."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    description: "Test rule"
    severity: warn
    action: fail
""", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])

        assert result.exit_code == 0
        assert "Promoted 'TEST001': warn → error" in result.output
        assert "✅" in result.output

        # Verify file was modified
        with rules_file.open('r') as f:
            updated_rules = yaml.safe_load(f)
        assert updated_rules['rules'][0]['severity'] == 'error'

    def test_promote_rule_dry_run(self, tmp_path):
        """Dry-run mode doesn't modify file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: warn
""", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [
            str(rules_file),
            'TEST001',
            '--dry-run'
        ])

        assert result.exit_code == 0
        assert "[DRY RUN] Would promote 'TEST001': warn → error" in result.output
        assert "(No changes made)" in result.output

        # Verify file was NOT modified
        with rules_file.open('r') as f:
            updated_rules = yaml.safe_load(f)
        assert updated_rules['rules'][0]['severity'] == 'warn'

    def test_promote_rule_not_found(self, tmp_path):
        """Rule not found exits with error."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: warn
""", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'NONEXISTENT'])

        assert result.exit_code == 1
        assert "❌ Rule 'NONEXISTENT' not found" in result.output

    def test_promote_rule_already_max_severity(self, tmp_path):
        """Rule at max severity exits with warning."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: fatal
""", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])

        assert result.exit_code == 0
        assert "⚠️  Rule 'TEST001' already at maximum severity: fatal" in result.output

    def test_promote_rule_file_not_found(self, tmp_path):
        """Non-existent file exits with error."""
        rules_file = tmp_path / "nonexistent.yaml"

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])

        # Click exits with 2 for argument errors (file doesn't exist)
        assert result.exit_code in [1, 2]
        # Error message varies by Click version
        assert "does not exist" in result.output or "Error" in result.output

    def test_promote_rule_invalid_yaml(self, tmp_path):
        """Invalid YAML exits with error."""
        rules_file = tmp_path / "invalid.yaml"
        rules_file.write_text("invalid: yaml: [", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])

        assert result.exit_code == 1
        assert "❌" in result.output
        assert "YAML Error" in result.output or "Invalid YAML" in result.output

    def test_promote_rule_multiple_promotions(self, tmp_path):
        """Multiple promotions work correctly."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: warn
""", encoding='utf-8')

        runner = CliRunner()

        # First promotion: warn → error
        result1 = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])
        assert result1.exit_code == 0
        assert "warn → error" in result1.output

        # Second promotion: error → fatal
        result2 = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])
        assert result2.exit_code == 0
        assert "error → fatal" in result2.output

        # Third attempt: already at max
        result3 = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])
        assert result3.exit_code == 0
        assert "already at maximum severity" in result3.output

    def test_promote_rule_preserves_other_rules(self, tmp_path):
        """Promoting one rule doesn't affect others."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: TEST001
    severity: warn
  - id: TEST002
    severity: error
  - id: TEST003
    severity: fatal
""", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(promote_rule, [str(rules_file), 'TEST001'])

        assert result.exit_code == 0

        # Verify only TEST001 changed
        with rules_file.open('r') as f:
            updated_rules = yaml.safe_load(f)

        assert updated_rules['rules'][0]['severity'] == 'error'  # TEST001 promoted
        assert updated_rules['rules'][1]['severity'] == 'error'  # TEST002 unchanged
        assert updated_rules['rules'][2]['severity'] == 'fatal'  # TEST003 unchanged
