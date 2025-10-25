"""
Unit tests for autodiscovery and input source resolution.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from crashlens.guard import find_rules_path, resolve_log_sources, guard


class TestFindRulesPath:
    """Test rules file autodiscovery."""
    
    def test_provided_path_exists(self, tmp_path, monkeypatch):
        """Returns provided path if it exists."""
        monkeypatch.chdir(tmp_path)
        rules_file = tmp_path / "custom-rules.yaml"
        rules_file.write_text("version: 1\nrules: []\n")
        
        result = find_rules_path(str(rules_file))
        assert result == str(rules_file)
    
    def test_provided_path_not_exists(self, tmp_path, monkeypatch):
        """Returns None if provided path doesn't exist."""
        monkeypatch.chdir(tmp_path)
        result = find_rules_path("nonexistent.yaml")
        assert result is None
    
    def test_autodiscover_crashlens_rules(self, tmp_path, monkeypatch):
        """Autodiscovers .crashlens/rules.yaml."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        rules_file = crashlens_dir / "rules.yaml"
        rules_file.write_text("version: 1\nrules: []\n")
        
        result = find_rules_path()
        assert result == ".crashlens/rules.yaml"
    
    def test_autodiscover_github_rules(self, tmp_path, monkeypatch):
        """Autodiscovers .github/crashlens/rules.yaml."""
        monkeypatch.chdir(tmp_path)
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        rules_file = github_dir / "rules.yaml"
        rules_file.write_text("version: 1\nrules: []\n")
        
        result = find_rules_path()
        assert result == ".github/crashlens/rules.yaml"
    
    def test_autodiscover_root_rules(self, tmp_path, monkeypatch):
        """Autodiscovers rules.yaml in root."""
        monkeypatch.chdir(tmp_path)
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("version: 1\nrules: []\n")
        
        result = find_rules_path()
        assert result == "rules.yaml"
    
    def test_autodiscover_priority_order(self, tmp_path, monkeypatch):
        """Respects priority: .crashlens > .github > root."""
        monkeypatch.chdir(tmp_path)
        
        # Create all three
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        (crashlens_dir / "rules.yaml").write_text("version: 1\nrules: []\n")
        
        github_dir = tmp_path / ".github" / "crashlens"
        github_dir.mkdir(parents=True)
        (github_dir / "rules.yaml").write_text("version: 1\nrules: []\n")
        
        (tmp_path / "rules.yaml").write_text("version: 1\nrules: []\n")
        
        # Should pick .crashlens first
        result = find_rules_path()
        assert result == ".crashlens/rules.yaml"
    
    def test_autodiscover_not_found(self, tmp_path, monkeypatch):
        """Returns None if no rules found."""
        monkeypatch.chdir(tmp_path)
        result = find_rules_path()
        assert result is None


class TestResolveLogSources:
    """Test log source resolution (file, dir, glob, stdin)."""
    
    def test_resolve_single_file(self, tmp_path, monkeypatch):
        """Resolves single file path."""
        monkeypatch.chdir(tmp_path)
        log_file = tmp_path / "logs.jsonl"
        log_file.write_text('{"model": "gpt-4"}\n')
        
        result = resolve_log_sources(str(log_file))
        assert len(result) == 1
        assert result[0] == log_file
    
    def test_resolve_directory(self, tmp_path, monkeypatch):
        """Resolves directory to all *.jsonl files."""
        monkeypatch.chdir(tmp_path)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        
        (logs_dir / "log1.jsonl").write_text('{"model": "gpt-4"}\n')
        (logs_dir / "log2.jsonl").write_text('{"model": "gpt-3.5"}\n')
        (logs_dir / "readme.txt").write_text("Not a log file")
        
        result = resolve_log_sources(str(logs_dir))
        assert len(result) == 2
        assert all(p.suffix == '.jsonl' for p in result)
        assert sorted([p.name for p in result]) == ['log1.jsonl', 'log2.jsonl']
    
    def test_resolve_directory_no_jsonl(self, tmp_path, monkeypatch):
        """Raises error if directory has no *.jsonl files."""
        monkeypatch.chdir(tmp_path)
        logs_dir = tmp_path / "empty"
        logs_dir.mkdir()
        
        with pytest.raises(Exception, match="No .*.jsonl files found"):
            resolve_log_sources(str(logs_dir))
    
    def test_resolve_glob_pattern(self, tmp_path, monkeypatch):
        """Resolves glob pattern."""
        monkeypatch.chdir(tmp_path)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        
        (logs_dir / "test1.jsonl").write_text('{"model": "gpt-4"}\n')
        (logs_dir / "test2.jsonl").write_text('{"model": "gpt-3.5"}\n')
        (logs_dir / "prod.jsonl").write_text('{"model": "gpt-4"}\n')
        
        result = resolve_log_sources("logs/test*.jsonl")
        assert len(result) == 2
        assert all('test' in p.name for p in result)
    
    def test_resolve_glob_no_matches(self, tmp_path, monkeypatch):
        """Raises error if glob has no matches."""
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(Exception, match="No files match glob pattern"):
            resolve_log_sources("nonexistent/*.jsonl")
    
    def test_resolve_stdin_dash(self, tmp_path, monkeypatch):
        """Resolves '-' to stdin."""
        monkeypatch.chdir(tmp_path)
        result = resolve_log_sources('-')
        assert len(result) == 1
        assert str(result[0]) == '-'
    
    def test_resolve_stdin_none(self, tmp_path, monkeypatch):
        """Resolves None to stdin."""
        monkeypatch.chdir(tmp_path)
        result = resolve_log_sources(None)
        assert len(result) == 1
        assert str(result[0]) == '-'
    
    def test_resolve_nonexistent_file(self, tmp_path, monkeypatch):
        """Raises error for nonexistent file."""
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(Exception, match="Log source not found"):
            resolve_log_sources("nonexistent.jsonl")


class TestGuardWithMultipleSources:
    """Test guard command with multiple input sources."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_guard_with_directory(self):
        """Guard processes directory of JSONL files."""
        with self.runner.isolated_filesystem():
            # Create rules
            Path(".crashlens").mkdir()
            Path(".crashlens/rules.yaml").write_text(
                "version: 1\n"
                "rules:\n"
                "  - id: EXPENSIVE_MODEL\n"
                "    description: Expensive model usage\n"
                "    if: {model: 'gpt-4'}\n"
                "    action: warn\n"
                "    severity: warn\n"
            )
            
            # Create logs directory
            Path("logs").mkdir()
            Path("logs/log1.jsonl").write_text('{"model": "gpt-4"}\n')
            Path("logs/log2.jsonl").write_text('{"model": "gpt-3.5-turbo"}\n')
            
            result = self.runner.invoke(guard, ['logs'])
            assert result.exit_code == 0
            assert "Processing 2 log source(s)" in result.output
    
    def test_guard_with_glob_pattern(self):
        """Guard processes glob pattern."""
        with self.runner.isolated_filesystem():
            # Create rules
            Path(".crashlens").mkdir()
            Path(".crashlens/rules.yaml").write_text(
                "version: 1\n"
                "rules:\n"
                "  - id: ANY_MODEL\n"
                "    description: Any model\n"
                "    if: {model: '*'}\n"
                "    action: warn\n"
                "    severity: warn\n"
            )
            
            # Create logs
            Path("test1.jsonl").write_text('{"model": "gpt-4"}\n')
            Path("test2.jsonl").write_text('{"model": "gpt-3.5"}\n')
            Path("prod.jsonl").write_text('{"model": "claude"}\n')
            
            result = self.runner.invoke(guard, ['test*.jsonl'])
            assert result.exit_code == 0
    
    def test_guard_with_stdin(self):
        """Guard reads from stdin."""
        with self.runner.isolated_filesystem():
            # Create rules
            Path(".crashlens").mkdir()
            Path(".crashlens/rules.yaml").write_text(
                "version: 1\n"
                "rules:\n"
                "  - id: GPT4\n"
                "    description: GPT-4 usage\n"
                "    if: {model: 'gpt-4'}\n"
                "    action: warn\n"
                "    severity: warn\n"
            )
            
            stdin_data = '{"model": "gpt-4"}\n{"model": "gpt-3.5"}\n'
            result = self.runner.invoke(guard, ['-'], input=stdin_data)
            
            # Debug output
            if result.exit_code != 0:
                print("\n=== STDOUT ===")
                print(result.output)
                if result.exception:
                    print("\n=== EXCEPTION ===")
                    import traceback
                    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
            
            assert result.exit_code == 0
            assert "Reading from stdin" in result.output
    
    def test_guard_autodiscovers_rules(self):
        """Guard autodiscovers rules when not specified."""
        with self.runner.isolated_filesystem():
            # Create rules in .crashlens
            Path(".crashlens").mkdir()
            Path(".crashlens/rules.yaml").write_text(
                "version: 1\n"
                "rules:\n"
                "  - id: TEST\n"
                "    description: Test rule\n"
                "    if: {model: 'test'}\n"
                "    action: warn\n"
                "    severity: warn\n"
            )
            
            # Create log file
            Path("logs.jsonl").write_text('{"model": "test"}\n')
            
            result = self.runner.invoke(guard, ['logs.jsonl'])
            assert result.exit_code == 0
            # Should not say "autodiscovered" since we provided logfile
    
    def test_guard_no_rules_found_error(self):
        """Guard errors when no rules found."""
        with self.runner.isolated_filesystem():
            Path("logs.jsonl").write_text('{"model": "gpt-4"}\n')
            
            result = self.runner.invoke(guard, ['logs.jsonl'])
            assert result.exit_code != 0
            assert "No rules file found" in result.output
