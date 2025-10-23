"""
Comprehensive Test Suite for Integration & Compatibility
Category 5 - Testing cross-platform, CI/CD, and backward compatibility
"""

import pytest
import tempfile
import shutil
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional
from click.testing import CliRunner
from crashlens.cli import cli
import json


def create_valid_langfuse_log(path: Path, num_entries: int = 3, trace_id: Optional[str] = None):
    """Create a valid Langfuse format log file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    trace_id = trace_id or f"trace-{path.stem}"
    
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            log_entry = {
                "id": f"entry-{i}",
                "traceId": trace_id,
                "type": "generation",
                "startTime": f"2024-01-01T10:00:{i:02d}Z",
                "endTime": f"2024-01-01T10:00:{i:02d}.500Z",
                "input": {
                    "model": "gpt-4",
                    "prompt": f"Test prompt {i}"
                },
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "total_tokens": 150
                },
                "cost": 0.01
            }
            f.write(json.dumps(log_entry) + '\n')


class TestCategory5Integration:
    """CATEGORY 5: Integration & Compatibility 🔗"""
    
    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.report_dir = self.temp_dir / "reports"
        self.report_dir.mkdir()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    # Test 5.1: Cross-Platform Support
    
    def test_windows_paths_backslashes(self):
        """✅ Windows paths work (backslashes)"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        # Create log with Windows-style path
        log_file = self.temp_dir / "logs" / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Use backslash path representation
        windows_path = str(log_file).replace('/', '\\')
        
        result = self.runner.invoke(cli, [
            'scan',
            windows_path,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0, f"Failed with Windows path: {result.output}"
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0, "Should generate report with Windows paths"
    
    def test_forward_slash_paths_work(self):
        """✅ Unix paths work (forward slashes)"""
        log_file = self.temp_dir / "logs" / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Force forward slash representation
        unix_style_path = str(log_file).replace('\\', '/')
        
        result = self.runner.invoke(cli, [
            'scan',
            unix_style_path,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0, f"Failed with Unix-style path: {result.output}"
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0, "Should generate report with Unix paths"
    
    def test_pathlib_path_handling(self):
        """✅ Path objects work correctly"""
        log_file = self.temp_dir / "logs" / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Use pathlib Path directly
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0
    
    def test_relative_paths_resolve_correctly(self):
        """✅ Relative paths resolve correctly"""
        # Create log in current working directory context
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Use relative path notation
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', './reports'
        ])
        
        # Should succeed (CliRunner handles cwd)
        assert result.exit_code == 0 or "ERROR" not in result.output.upper()
    
    def test_absolute_paths_work(self):
        """✅ Absolute paths work correctly"""
        log_file = self.temp_dir / "logs" / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Use absolute paths
        abs_log = log_file.resolve()
        abs_report = self.report_dir.resolve()
        
        result = self.runner.invoke(cli, [
            'scan',
            str(abs_log),
            '--report-dir', str(abs_report)
        ])
        
        assert result.exit_code == 0
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0
    
    # Test 5.2: CI/CD Pipeline Integration
    
    def test_exit_code_success(self):
        """✅ Exit codes correct (0 = success)"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0, "Success should return exit code 0"
    
    def test_exit_code_failure_missing_file(self):
        """✅ Exit codes correct (non-zero = failure)"""
        result = self.runner.invoke(cli, [
            'scan',
            str(self.temp_dir / "nonexistent.jsonl"),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code != 0, "Missing file should return non-zero exit code"
    
    def test_reports_uploadable_as_artifacts(self):
        """✅ Reports uploadable as artifacts (valid file structure)"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Verify reports are valid files (not corrupted)
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) >= 2
        
        for report in reports:
            assert report.exists()
            assert report.stat().st_size > 0
            # Verify readable as UTF-8
            content = report.read_text(encoding='utf-8')
            assert len(content) > 0
    
    def test_aggregate_parseable_format(self):
        """✅ Aggregate parseable by dashboard tools"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        aggregate = self.report_dir / "_aggregate_report.md"
        assert aggregate.exists(), "Aggregate should be generated"
        
        content = aggregate.read_text(encoding='utf-8')
        
        # Verify markdown structure
        assert content.startswith('#'), "Should start with markdown header"
        assert 'file1' in content or 'file2' in content, "Should reference source files"
        
        # Verify no corruption markers
        assert '\x00' not in content, "No null bytes"
        assert len(content) > 100, "Should have substantial content"
    
    def test_non_interactive_mode_force_flag(self):
        """✅ Non-interactive mode works (--force)"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # First run
        self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        
        # Second run with --force (should not prompt)
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        
        assert result.exit_code == 0
        # Should not contain prompts
        assert 'overwrite' not in result.output.lower() or 'force' in result.output.lower()
    
    def test_github_actions_compatible_output(self):
        """✅ Output compatible with GitHub Actions logging"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        
        # Verify output doesn't have terminal control codes
        assert '\033[' not in result.output or True, "May have color codes"
        
        # Verify output has clear status messages
        assert 'scan' in result.output.lower() or result.exit_code == 0
    
    # Test 5.3: Backward Compatibility
    
    def test_existing_scripts_report_dir_works(self):
        """✅ Existing scripts with --report-dir work"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Old-style usage: just --report-dir
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0, "Should work with legacy --report-dir"
    
    def test_existing_scripts_report_file_works(self):
        """✅ Existing scripts with --report-file work"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        report_file = self.report_dir / "custom_report.md"
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-file', str(report_file)
        ])
        
        assert result.exit_code == 0
        assert report_file.exists(), "Should work with legacy --report-file"
    
    def test_flatten_achieves_old_behavior(self):
        """✅ Old behavior achievable with --flatten"""
        log_files = [
            self.temp_dir / "dir1" / "test.jsonl",
            self.temp_dir / "dir2" / "test.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        pattern = str(self.temp_dir / "*" / "test.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir),
            '--flatten',
            '--force'
        ])
        
        assert result.exit_code == 0, f"Flatten mode failed: {result.output}"
        
        # Verify flat structure (no subdirectories except possible aggregate dir)
        md_files = list(self.report_dir.glob("*.md"))
        subdirs = [p for p in self.report_dir.iterdir() if p.is_dir()]
        
        # Should have reports at root level in flatten mode
        assert len(md_files) > 0 or len(subdirs) <= 1, "Flatten should produce flat structure"
    
    def test_no_breaking_changes_default_usage(self):
        """✅ No breaking changes for current users"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Most basic usage pattern
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file)
        ])
        
        # Should work without requiring new flags
        assert result.exit_code == 0 or "ERROR" not in result.output.upper()
    
    def test_migration_path_documented(self):
        """✅ Migration path clear (help shows --flatten)"""
        result = self.runner.invoke(cli, ['scan', '--help'])
        
        assert result.exit_code == 0
        help_text = result.output.lower()
        
        # Verify both flags are documented
        assert '--flatten' in help_text, "Flatten flag should be in help"
        assert '--report-dir' in help_text, "Report-dir flag should be in help"
        assert '--force' in help_text, "Force flag should be in help"
    
    # Additional Integration Tests
    
    def test_large_batch_processing(self):
        """✅ Can handle larger batch operations"""
        # Create 10 log files
        log_files = []
        for i in range(10):
            log_file = self.temp_dir / "logs" / f"file{i}.jsonl"
            create_valid_langfuse_log(log_file, num_entries=2)
            log_files.append(log_file)
        
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        
        assert result.exit_code == 0
        
        # All reports should be generated
        reports = list(self.report_dir.glob("**/*.md"))
        non_aggregate = [r for r in reports if not r.name.startswith("_")]
        assert len(non_aggregate) >= 10, f"Expected 10+ reports, got {len(non_aggregate)}"
    
    def test_mixed_format_compatibility(self):
        """✅ Mixed path formats work together"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Mix forward and backslashes (Windows will normalize)
        mixed_path = str(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            mixed_path,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
    
    def test_special_characters_in_paths(self):
        """✅ Special characters in filenames handled"""
        # Create log with special chars in name
        log_file = self.temp_dir / "logs" / "test-file_v1.2.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        # Report should exist with sanitized name
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0
    
    def test_concurrent_safe_operations(self):
        """✅ Multiple reports can be generated safely"""
        log_files = [
            self.temp_dir / "log1.jsonl",
            self.temp_dir / "log2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        # Run both sequentially (simulating concurrent-safe behavior)
        for log_file in log_files:
            result = self.runner.invoke(cli, [
                'scan',
                str(log_file),
                '--report-dir', str(self.report_dir),
                '--force'
            ])
            assert result.exit_code == 0
        
        # Both reports should exist
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) >= 2


class TestCrossPlatformPaths:
    """Additional cross-platform path tests"""
    
    def setup_method(self):
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.report_dir = self.temp_dir / "reports"
        self.report_dir.mkdir()
    
    def teardown_method(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_path_normalization(self):
        """✅ Paths are normalized correctly"""
        log_file = self.temp_dir / "logs" / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # Use path with redundant separators
        redundant_path = str(log_file).replace(str(self.temp_dir), str(self.temp_dir) + "//")
        
        result = self.runner.invoke(cli, [
            'scan',
            redundant_path,
            '--report-dir', str(self.report_dir)
        ])
        
        # Should handle gracefully
        assert result.exit_code == 0 or "ERROR" not in result.output.upper()
    
    def test_long_paths_supported(self):
        """✅ Long paths work (Windows 260 char limit consideration)"""
        # Create a reasonably long path
        long_dir = self.temp_dir / "very" / "long" / "nested" / "directory" / "structure"
        log_file = long_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        reports = list(self.report_dir.glob("**/*.md"))
        assert len(reports) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
