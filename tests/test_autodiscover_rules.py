#!/usr/bin/env python3
"""
Unit tests for autodiscover rules.yaml (Step 6)
"""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import autodiscover_rules, guard


class TestAutodiscoverRules:
    """Test rules.yaml autodiscovery."""
    
    def test_autodiscover_crashlens_dir(self, tmp_path, monkeypatch):
        """Autodiscover .crashlens/rules.yaml (highest priority)."""
        monkeypatch.chdir(tmp_path)
        
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        (crashlens_dir / "rules.yaml").write_text("rules: []")
        
        discovered = autodiscover_rules()
        assert discovered == ".crashlens/rules.yaml"
    
    def test_autodiscover_github_dir(self, tmp_path, monkeypatch):
        """Autodiscover .github/crashlens/rules.yaml (second priority)."""
        monkeypatch.chdir(tmp_path)
        
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        (github_dir / "rules.yaml").write_text("rules: []")
        
        discovered = autodiscover_rules()
        assert discovered == ".github/crashlens/rules.yaml"
    
    def test_autodiscover_root(self, tmp_path, monkeypatch):
        """Autodiscover rules.yaml in root (lowest priority)."""
        monkeypatch.chdir(tmp_path)
        
        (tmp_path / "rules.yaml").write_text("rules: []")
        
        discovered = autodiscover_rules()
        assert discovered == "rules.yaml"
    
    def test_autodiscover_priority(self, tmp_path, monkeypatch):
        """Autodiscovery respects priority order."""
        monkeypatch.chdir(tmp_path)
        
        # Create all three locations
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        (crashlens_dir / "rules.yaml").write_text("rules: []")
        
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        (github_dir / "rules.yaml").write_text("rules: []")
        
        (tmp_path / "rules.yaml").write_text("rules: []")
        
        # Should discover .crashlens/ first
        discovered = autodiscover_rules()
        assert discovered == ".crashlens/rules.yaml"
    
    def test_autodiscover_none(self, tmp_path, monkeypatch):
        """Return None if no rules.yaml found."""
        monkeypatch.chdir(tmp_path)
        
        discovered = autodiscover_rules()
        assert discovered is None


class TestGuardWithAutodiscovery:
    """Test guard command with autodiscovery."""
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample logs."""
        logs_file = tmp_path / "logs.jsonl"
        logs_content = """{"traceId": "t1", "model": "gpt-4", "tokens": 1500}
{"traceId": "t2", "model": "gpt-3.5", "tokens": 500}
"""
        logs_file.write_text(logs_content)
        return logs_file
    
    @pytest.fixture
    def simple_rules(self):
        """Simple rules content."""
        return """
rules:
  - id: AUTO_001
    description: "Test rule"
    if:
      if_model: "gpt-4"
    action: warn
    severity: warning
"""
    
    def test_guard_autodiscovers_crashlens_dir(self, tmp_path, sample_logs, simple_rules):
        """Guard autodiscovers .crashlens/rules.yaml."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .crashlens/rules.yaml
            crashlens_dir = Path(".crashlens")
            crashlens_dir.mkdir()
            (crashlens_dir / "rules.yaml").write_text(simple_rules)
            
            # Copy logs
            Path("logs.jsonl").write_text(sample_logs.read_text())
            
            # Suppress deprecation warning for test output matching
            result = runner.invoke(guard, ["logs.jsonl", "--output", "json"], env={"CRASHLENS_QUIET": "1"})
            
            # Should autodiscover and run successfully
            assert result.exit_code in [0, 1]
            assert "Using rules: .crashlens/rules.yaml" in result.output or ".crashlens/rules.yaml" in result.output
    
    def test_guard_autodiscovers_github_dir(self, tmp_path, sample_logs, simple_rules):
        """Guard autodiscovers .github/crashlens/rules.yaml."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .github/crashlens/rules.yaml
            github_dir = Path(".github/crashlens")
            github_dir.mkdir(parents=True)
            (github_dir / "rules.yaml").write_text(simple_rules)
            
            Path("logs.jsonl").write_text(sample_logs.read_text())
            
            # Suppress deprecation warning for test output matching
            result = runner.invoke(guard, ["logs.jsonl", "--output", "json"], env={"CRASHLENS_QUIET": "1"})
            
            assert result.exit_code in [0, 1]
            assert "Using rules: .github/crashlens/rules.yaml" in result.output or ".github/crashlens/rules.yaml" in result.output
    
    def test_guard_autodiscovers_root(self, tmp_path, sample_logs, simple_rules):
        """Guard autodiscovers rules.yaml in root."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create rules.yaml in root
            Path("rules.yaml").write_text(simple_rules)
            Path("logs.jsonl").write_text(sample_logs.read_text())
            
            # Suppress deprecation warning for test output matching
            result = runner.invoke(guard, ["logs.jsonl", "--output", "json"], env={"CRASHLENS_QUIET": "1"})
            
            assert result.exit_code in [0, 1]
            assert "Using rules: rules.yaml" in result.output or "rules.yaml" in result.output
    
    def test_guard_explicit_rules_overrides(self, tmp_path, sample_logs, simple_rules):
        """Explicit --rules option overrides autodiscovery."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create both autodiscoverable and explicit rules
            crashlens_dir = Path(".crashlens")
            crashlens_dir.mkdir()
            (crashlens_dir / "rules.yaml").write_text(simple_rules)
            
            Path("custom-rules.yaml").write_text(simple_rules)
            Path("logs.jsonl").write_text(sample_logs.read_text())
            
            result = runner.invoke(guard, ["logs.jsonl", "--rules", "custom-rules.yaml", "--output", "json"])
            
            # Should NOT autodiscover (no message)
            assert "Autodiscovered" not in result.output
    
    def test_guard_no_rules_fails(self, tmp_path, sample_logs):
        """Guard fails with clear message if no rules found."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("logs.jsonl").write_text(sample_logs.read_text())
            
            result = runner.invoke(guard, ["logs.jsonl", "--output", "json"])
            
            assert result.exit_code != 0
            assert "No rules file found" in result.output
            assert ".crashlens/rules.yaml" in result.output
            assert ".github/crashlens/rules.yaml" in result.output


class TestAutodiscoveryPriority:
    """Test autodiscovery priority edge cases."""
    
    def test_github_wins_over_root(self, tmp_path, monkeypatch):
        """GitHub dir wins over root when .crashlens/ absent."""
        monkeypatch.chdir(tmp_path)
        
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        (github_dir / "rules.yaml").write_text("rules: []")
        
        (tmp_path / "rules.yaml").write_text("rules: []")
        
        discovered = autodiscover_rules()
        assert discovered == ".github/crashlens/rules.yaml"
    
    def test_crashlens_wins_over_github(self, tmp_path, monkeypatch):
        """Crashlens dir wins over GitHub when both present."""
        monkeypatch.chdir(tmp_path)
        
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        (crashlens_dir / "rules.yaml").write_text("rules: []")
        
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        (github_dir / "rules.yaml").write_text("rules: []")
        
        discovered = autodiscover_rules()
        assert discovered == ".crashlens/rules.yaml"
