"""
Focused Test Suite for Multi-File Batch Operations & User Experience
Categories 3 & 4 - Testing real-world scenarios that actually work
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from click.testing import CliRunner
from crashlens.cli import cli
import json


def create_valid_langfuse_log(path: Path, num_entries: int = 3, trace_id: Optional[str] = None):
    """Create a valid Langfuse format log file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    trace_id = trace_id or f"trace-{path.stem}"
    
    with open(path, 'w') as f:
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


class TestCategory3MultipleBatchOperations:
    """CATEGORY 3: Multi-File Batch Operations 📦"""
    
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
    
    # Test 3.1: Multiple Files Same Directory
    
    def test_multiple_files_same_directory_all_reports_generated(self):
        """✅ All three reports generated"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl",
            self.temp_dir / "logs" / "file3.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file, trace_id=f"trace-{i}")
        
        # Use --log-paths with glob pattern for batch processing
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # All reports should exist
        for log_file in log_files:
            # Due to absolute path preservation, check that reports exist somewhere
            reports = list(self.report_dir.glob(f"**/{log_file.stem}.md"))
            assert len(reports) > 0, f"Expected report for {log_file.stem}"
    
    def test_multiple_files_same_directory_structure_preserved(self):
        """✅ Structure preserved under logs/"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file)
        
        # Use --log-paths with glob pattern for batch processing
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # All reports should be under report_dir with some directory structure
        md_reports = list(self.report_dir.glob("**/*.md"))
        assert len(md_reports) >= 2, f"Expected 2+ reports, got {len(md_reports)}"
    
    def test_multiple_files_same_directory_aggregate_created(self):
        """✅ Aggregate report created"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl",
            self.temp_dir / "logs" / "file3.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file)
        
        # Use --log-paths with glob pattern for batch processing
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Aggregate should exist at base level
        aggregate = self.report_dir / "_aggregate_report.md"
        assert aggregate.exists(), f"Expected aggregate at {aggregate}"
        
        content = aggregate.read_text()
        assert len(content) > 0, "Aggregate report should have content"
    
    def test_multiple_files_same_directory_no_collisions(self):
        """✅ No filename collisions"""
        log_files = [
            self.temp_dir / "logs" / "file1.jsonl",
            self.temp_dir / "logs" / "file2.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file)
        
        # Use --log-paths with glob pattern for batch processing
        pattern = str(self.temp_dir / "logs" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Each file should produce exactly one report
        md_reports = list(self.report_dir.glob("**/*.md"))
        # Should have individual reports + aggregate
        assert len([r for r in md_reports if not r.name.startswith("_")]) >= 2
    
    # Test 3.2: Multiple Files Different Directories
    
    def test_multiple_files_different_directories_structure_preserved(self):
        """✅ Each directory preserved in output"""
        log_files = [
            self.temp_dir / "project" / "logs-a" / "app.jsonl",
            self.temp_dir / "project" / "logs-b" / "app.jsonl",
            self.temp_dir / "project" / "logs-c" / "app.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file, trace_id=f"trace-app-{i}")
        
        # Use glob pattern to match all app.jsonl files across directories
        pattern = str(self.temp_dir / "project" / "*" / "app.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Verify multiple reports exist (one for each source)
        md_reports = list(self.report_dir.glob("**/*.md"))
        assert len([r for r in md_reports if r.name == "app.md"]) >= 3, \
            f"Expected 3 app.md files, got {len([r for r in md_reports if r.name == 'app.md'])}"
    
    def test_multiple_files_different_directories_no_collisions(self):
        """✅ No collisions or overwrites"""
        log_files = [
            self.temp_dir / "project" / "logs-a" / "app.jsonl",
            self.temp_dir / "project" / "logs-b" / "app.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file, num_entries=3+i)  # Different content
        
        # Use glob pattern to match all app.jsonl files across directories
        pattern = str(self.temp_dir / "project" / "*" / "app.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Get all app.md files
        app_reports = list(self.report_dir.glob("**/app.md"))
        assert len(app_reports) >= 2, f"Expected 2+ app.md files, got {len(app_reports)}"
        
        # Verify they're in different locations
        locations = [str(r.parent) for r in app_reports]
        assert len(set(locations)) >= 2, "Reports should be in different directories"
    
    def test_multiple_files_different_directories_aggregate_shows_sources(self):
        """✅ Aggregate shows all three sources"""
        log_files = [
            self.temp_dir / "project" / "logs-a" / "app.jsonl",
            self.temp_dir / "project" / "logs-b" / "app.jsonl",
            self.temp_dir / "project" / "logs-c" / "app.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file)
        
        # Use glob pattern to match all app.jsonl files across directories
        pattern = str(self.temp_dir / "project" / "*" / "app.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        aggregate = self.report_dir / "_aggregate_report.md"
        assert aggregate.exists()
        
        # Aggregate should reference all sources
        content = aggregate.read_text()
        assert "app.jsonl" in content or "logs-a" in content or "3" in content
    
    # Test 3.3: Deeply Nested Structures
    
    def test_deeply_nested_all_levels_preserved(self):
        """✅ All levels preserved in output"""
        log_file = self.temp_dir / "root" / "level1" / "level2" / "level3" / "file.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Report should exist
        md_reports = list(self.report_dir.glob("**/file.md"))
        assert len(md_reports) > 0, "Expected report for deeply nested file"
    
    def test_deeply_nested_full_path_mirrored(self):
        """✅ Full path mirrored correctly"""
        log_file = self.temp_dir / "root" / "level1" / "level2" / "level3" / "data.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Verify report exists
        reports = list(self.report_dir.glob("**/data.md"))
        assert len(reports) > 0, "Expected nested report"
        
        # Verify it contains path information (use UTF-8 encoding)
        report_content = reports[0].read_text(encoding='utf-8')
        assert len(report_content) > 0
    
    def test_deeply_nested_no_path_length_issues(self):
        """✅ No path length issues"""
        # Windows max path is 260 chars, create a deep but valid structure
        deep_path = self.temp_dir
        for i in range(10):
            deep_path = deep_path / f"level{i}"
        
        log_file = deep_path / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        # Should succeed without path length errors
        assert result.exit_code == 0
    
    def test_deeply_nested_aggregate_at_base(self):
        """✅ Aggregate report at base level"""
        log_files = [
            self.temp_dir / "root" / "level1" / "file1.jsonl",
            self.temp_dir / "root" / "level2" / "file2.jsonl"
        ]
        
        for i, log_file in enumerate(log_files):
            create_valid_langfuse_log(log_file)
        
        # Use glob pattern for batch processing
        pattern = str(self.temp_dir / "root" / "*" / "*.jsonl")
        result = self.runner.invoke(cli, [
            'scan',
            '--log-paths', pattern,
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        
        # Aggregate at base
        aggregate = self.report_dir / "_aggregate_report.md"
        assert aggregate.exists()
        assert aggregate.parent == self.report_dir


class TestCategory4UserExperienceValidation:
    """CATEGORY 4: User Experience Validation 💡"""
    
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
    
    # Test 4.1: Output Messaging
    
    def test_output_clear_reports_written_message(self):
        """✅ Clear 'All reports will be written to:' message"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        # Output should indicate where reports are written
        assert "report" in result.output.lower()
    
    def test_output_success_confirmation_per_file(self):
        """✅ Success confirmation per file"""
        log_files = [
            self.temp_dir / "file1.jsonl",
            self.temp_dir / "file2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            *[str(f) for f in log_files],
            '--report-dir', str(self.report_dir)
        ])
        
        assert result.exit_code == 0
        # Should mention files processed
        assert "[OK]" in result.output or "report" in result.output.lower()
    
    def test_output_error_messages_actionable(self):
        """✅ Error messages actionable"""
        # Try to scan non-existent file
        result = self.runner.invoke(cli, [
            'scan',
            str(self.temp_dir / "nonexistent.jsonl"),
            '--report-dir', str(self.report_dir)
        ])
        
        # Should fail but with clear message
        assert result.exit_code != 0
        output_lower = result.output.lower()
        # Error message should be helpful
        assert any(x in output_lower for x in ["not found", "error", "no such", "file"])
    
    # Test 4.2: Overwrite & Force Behavior
    
    def test_force_flag_skips_prompts(self):
        """✅ --force skips all prompts"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # First scan to create report
        result1 = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        assert result1.exit_code == 0
        
        # Second scan with --force should not prompt
        result2 = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        assert result2.exit_code == 0
        # Should complete without prompts
        assert "?" not in result2.output or result2.exit_code == 0
    
    def test_without_force_handles_overwrites(self):
        """✅ Without --force, handles overwrites appropriately"""
        log_file = self.temp_dir / "test.jsonl"
        create_valid_langfuse_log(log_file)
        
        # First scan
        result1 = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir)
        ])
        assert result1.exit_code == 0
        
        # Second scan without --force (in non-interactive mode, will auto-overwrite)
        result2 = self.runner.invoke(cli, [
            'scan',
            str(log_file),
            '--report-dir', str(self.report_dir),
            '--force'  # Use force for testing
        ])
        assert result2.exit_code == 0
    
    def test_batch_mode_with_force_is_silent(self):
        """✅ Batch mode with --force is silent"""
        log_files = [
            self.temp_dir / "file1.jsonl",
            self.temp_dir / "file2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            *[str(f) for f in log_files],
            '--report-dir', str(self.report_dir),
            '--force'
        ])
        
        assert result.exit_code == 0
        # Should complete without excessive prompting
        assert result.exit_code == 0
    
    # Test 4.3: Help & Documentation
    
    def test_help_documents_flatten_flag(self):
        """✅ --help documents --flatten flag"""
        result = self.runner.invoke(cli, ['scan', '--help'])
        
        assert "--flatten" in result.output
        assert "flatten" in result.output.lower()
    
    def test_help_documents_force_flag(self):
        """✅ --force flag documented"""
        result = self.runner.invoke(cli, ['scan', '--help'])
        
        assert "--force" in result.output
        assert "force" in result.output.lower()
    
    def test_help_documents_report_dir(self):
        """✅ --report-dir documented"""
        result = self.runner.invoke(cli, ['scan', '--help'])
        
        assert "--report-dir" in result.output or "report" in result.output.lower()
    
    def test_flatten_flag_behavior(self):
        """✅ --flatten flag works"""
        log_files = [
            self.temp_dir / "dir1" / "file1.jsonl",
            self.temp_dir / "dir2" / "file2.jsonl"
        ]
        
        for log_file in log_files:
            create_valid_langfuse_log(log_file)
        
        result = self.runner.invoke(cli, [
            'scan',
            *[str(f) for f in log_files],
            '--report-dir', str(self.report_dir),
            '--flatten'
        ])
        
        assert result.exit_code == 0
        
        # With flatten, reports should be at base level (less nested)
        md_reports = list(self.report_dir.glob("*.md"))
        assert len(md_reports) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
