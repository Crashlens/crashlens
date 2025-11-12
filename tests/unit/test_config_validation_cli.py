"""
Unit tests for metrics config validation CLI commands.

Tests the validate-metrics-config and show-metrics-config commands.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Import CLI commands
from crashlens.cli import validate_metrics_config_legacy as validate_metrics_config, show_metrics_config


class TestValidateMetricsConfigCommand:
    """Test the validate-metrics-config CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Valid minimal config
        self.valid_config = """
metrics:
  enabled: true
  sampling:
    rate: 0.1
  pushgateway:
    url: "http://localhost:9091"
    job: "test"
"""
        
        # Invalid config (bad rate)
        self.invalid_config = """
metrics:
  enabled: true
  sampling:
    rate: 1.5  # Invalid: must be 0.0-1.0
  pushgateway:
    url: "http://localhost:9091"
    job: "test"
"""
        
        # Config with per-rule sampling
        self.per_rule_config = """
metrics:
  enabled: true
  sampling:
    rate: 0.1
    per_rule:
      high_frequency: 0.01
      critical: 1.0
      disabled: 0.0
  pushgateway:
    url: "http://localhost:9091"
    job: "test"
"""

    def test_validate_valid_config(self):
        """Test validation of a valid config file."""
        with self.runner.isolated_filesystem():
            # Create valid config file
            Path("valid.yaml").write_text(self.valid_config)
            
            # Run validation
            result = self.runner.invoke(validate_metrics_config, ['valid.yaml'])
            
            # Should succeed
            assert result.exit_code == 0
            assert "✅ VALIDATION PASSED" in result.output
            assert "Config file is valid" in result.output

    def test_validate_invalid_config(self):
        """Test validation of an invalid config file."""
        with self.runner.isolated_filesystem():
            # Create invalid config file
            Path("invalid.yaml").write_text(self.invalid_config)
            
            # Run validation
            result = self.runner.invoke(validate_metrics_config, ['invalid.yaml'])
            
            # Should fail
            assert result.exit_code == 1
            assert "❌ VALIDATION FAILED" in result.output

    def test_validate_with_verbose_flag(self):
        """Test validation with --verbose flag shows detailed summary."""
        with self.runner.isolated_filesystem():
            # Create config with per-rule sampling
            Path("config.yaml").write_text(self.per_rule_config)
            
            # Run validation with verbose
            result = self.runner.invoke(validate_metrics_config, ['config.yaml', '--verbose'])
            
            # Should succeed and show details
            assert result.exit_code == 0
            assert "✅ VALIDATION PASSED" in result.output
            assert "📊 Configuration Summary" in result.output
            assert "📋 Per-Rule Sampling" in result.output
            assert "high_frequency" in result.output
            assert "critical" in result.output

    def test_validate_nonexistent_file(self):
        """Test validation with non-existent file."""
        result = self.runner.invoke(validate_metrics_config, ['nonexistent.yaml'])
        
        # Click should handle file not found
        assert result.exit_code != 0

    def test_validate_malformed_yaml(self):
        """Test validation with malformed YAML."""
        with self.runner.isolated_filesystem():
            # Create malformed YAML
            Path("malformed.yaml").write_text("metrics:\n  bad indent\n not: aligned")
            
            # Run validation
            result = self.runner.invoke(validate_metrics_config, ['malformed.yaml'])
            
            # Should fail with YAML error
            assert result.exit_code == 1
            assert "❌ VALIDATION FAILED" in result.output

    def test_validate_shows_usage_instructions(self):
        """Test that validation shows usage instructions on success."""
        with self.runner.isolated_filesystem():
            Path("valid.yaml").write_text(self.valid_config)
            
            result = self.runner.invoke(validate_metrics_config, ['valid.yaml'])
            
            assert result.exit_code == 0
            assert "💡 Use with:" in result.output
            assert "crashlens scan" in result.output
            assert "--push-metrics" in result.output

    def test_validate_per_rule_emoji_indicators(self):
        """Test that per-rule sampling shows appropriate emoji indicators."""
        with self.runner.isolated_filesystem():
            Path("config.yaml").write_text(self.per_rule_config)
            
            result = self.runner.invoke(validate_metrics_config, ['config.yaml', '-v'])
            
            assert result.exit_code == 0
            # Should show emoji indicators for different rates
            assert "🔇" in result.output or "DISABLED" in result.output  # 0%
            assert "🔉" in result.output or "LOW" in result.output  # <5%
            assert "🚨" in result.output or "ALWAYS" in result.output  # 100%


class TestShowMetricsConfigCommand:
    """Test the show-metrics-config CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        self.test_config = """
metrics:
  enabled: true
  sampling:
    rate: 0.2
    per_rule:
      test_rule: 0.5
  pushgateway:
    url: "http://localhost:9091"
    job: "show-test"
"""

    def test_show_config_with_file(self):
        """Test showing config from specified file."""
        with self.runner.isolated_filesystem():
            Path("config.yaml").write_text(self.test_config)
            
            result = self.runner.invoke(show_metrics_config, ['--config', 'config.yaml'])
            
            assert result.exit_code == 0
            assert "🔍 Loading metrics configuration" in result.output
            assert "📁 Config file:" in result.output
            assert "Metrics Configuration:" in result.output
            assert "Enabled: True" in result.output

    def test_show_config_auto_search(self):
        """Test showing config with auto-search (no file specified)."""
        with self.runner.isolated_filesystem():
            # Create config in searchable location
            Path(".crashlens").mkdir()
            Path(".crashlens/metrics.yaml").write_text(self.test_config)
            
            result = self.runner.invoke(show_metrics_config, [])
            
            # Should find and load config
            assert result.exit_code == 0
            assert "🔍 Loading metrics configuration" in result.output

    def test_show_config_not_found(self):
        """Test showing config when no config file exists."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(show_metrics_config, [])
            
            # Should succeed with defaults (no config file found)
            assert result.exit_code == 0
            assert "🔍 Loading metrics configuration" in result.output
            assert "None found (using defaults)" in result.output or "📁 Config file:" in result.output

    def test_show_config_displays_summary(self):
        """Test that show-config displays configuration summary."""
        with self.runner.isolated_filesystem():
            Path("config.yaml").write_text(self.test_config)
            
            result = self.runner.invoke(show_metrics_config, ['-c', 'config.yaml'])
            
            assert result.exit_code == 0
            assert "Global Sampling:" in result.output
            assert "Pushgateway URL:" in result.output
            assert "Job Name:" in result.output


class TestConfigValidationIntegration:
    """Integration tests for config validation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_validate_then_show_workflow(self):
        """Test typical workflow: validate config, then show it."""
        with self.runner.isolated_filesystem():
            # Create config
            config_content = """
metrics:
  enabled: true
  sampling:
    rate: 0.15
  pushgateway:
    url: "http://localhost:9091"
    job: "integration-test"
"""
            Path("config.yaml").write_text(config_content)
            
            # Step 1: Validate
            validate_result = self.runner.invoke(
                validate_metrics_config, 
                ['config.yaml']
            )
            assert validate_result.exit_code == 0
            assert "✅ VALIDATION PASSED" in validate_result.output
            
            # Step 2: Show
            show_result = self.runner.invoke(
                show_metrics_config, 
                ['--config', 'config.yaml']
            )
            assert show_result.exit_code == 0
            assert "Metrics Configuration:" in show_result.output

    def test_validate_catches_errors_before_use(self):
        """Test that validation catches errors before attempting to use config."""
        with self.runner.isolated_filesystem():
            # Create invalid config
            invalid_config = """
metrics:
  enabled: true
  sampling:
    rate: 2.0  # Invalid!
  pushgateway:
    url: "invalid"
    job: "test"
"""
            Path("bad.yaml").write_text(invalid_config)
            
            # Validation should fail
            result = self.runner.invoke(validate_metrics_config, ['bad.yaml'])
            assert result.exit_code == 1
            assert "❌ VALIDATION FAILED" in result.output
