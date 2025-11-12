"""
Tests for file organization and report management.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil

from crashlens.reporters.file_organizer import FileOrganizer, ReportMetadata


class TestFileOrganizer:
    """Test cases for FileOrganizer."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.test_dir = Path("test_policy_violations")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        
        self.organizer = FileOrganizer(
            base_dir=self.test_dir,
            auto_readme=False  # Manual control in tests
        )
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_directory_initialization(self):
        """Test that subdirectories are created."""
        assert self.test_dir.exists()
        assert self.organizer.reports_dir.exists()
        assert self.organizer.traces_dir.exists()
        assert self.organizer.archives_dir.exists()
    
    def test_save_report(self):
        """Test saving report to reports/ directory."""
        content = "# Test Report\nThis is a test."
        metadata = ReportMetadata(
            file_path="test_report.md",
            timestamp=datetime.now().isoformat(),
            format="markdown",
            detections_count=5,
            severity_summary={"high": 2, "medium": 3},
            total_waste_cost=1.23,
            total_waste_tokens=1000,
            report_type="scan"
        )
        
        report_path = self.organizer.save_report(
            content=content,
            format="markdown",
            report_type="scan",
            metadata=metadata
        )
        
        assert report_path.exists()
        assert report_path.parent == self.organizer.reports_dir
        assert report_path.suffix == ".md"
        assert report_path.read_text() == content
    
    def test_save_trace(self):
        """Test saving trace to traces/ directory."""
        trace_id = "abc123"
        content = '{"traceId": "abc123", "model": "gpt-4"}'
        
        trace_path = self.organizer.save_trace(
            trace_id=trace_id,
            content=content
        )
        
        assert trace_path.exists()
        assert trace_path.parent == self.organizer.traces_dir
        assert trace_path.name == f"trace_{trace_id}.jsonl"
        assert trace_path.read_text() == content
    
    def test_archive_old_reports(self):
        """Test archiving reports older than threshold."""
        # Create old report
        old_report = self.organizer.reports_dir / "old_report.md"
        old_report.write_text("Old report")
        
        # Set modification time to 31 days ago
        old_time = (datetime.now() - timedelta(days=31)).timestamp()
        old_report.touch()
        import os
        os.utime(old_report, (old_time, old_time))
        
        # Create new report
        new_report = self.organizer.reports_dir / "new_report.md"
        new_report.write_text("New report")
        
        # Archive old reports (older than 30 days)
        archived = self.organizer.archive_old_reports(days=30)
        
        assert len(archived) == 1
        assert not old_report.exists()
        assert new_report.exists()
        assert archived[0].parent.parent == self.organizer.archives_dir
    
    def test_prune_archives(self):
        """Test pruning old archives."""
        # Create archive structure
        archive_month = self.organizer.archives_dir / "2024-01"
        archive_month.mkdir()
        
        old_archive = archive_month / "very_old_report.md"
        old_archive.write_text("Very old report")
        
        # Set modification time to 91 days ago
        old_time = (datetime.now() - timedelta(days=91)).timestamp()
        import os
        os.utime(old_archive, (old_time, old_time))
        
        # Prune archives older than 90 days
        pruned = self.organizer.prune_archives(days=90)
        
        assert len(pruned) == 1
        assert not old_archive.exists()
    
    def test_generate_readme(self):
        """Test README generation."""
        # Create some reports
        self.organizer.save_report(
            content="Report 1",
            format="markdown",
            report_type="scan"
        )
        self.organizer.save_report(
            content='{"detections": []}',
            format="json",
            report_type="guard"
        )
        
        readme_path = self.organizer.generate_readme()
        
        assert readme_path.exists()
        assert readme_path == self.test_dir / "README.md"
        
        readme_content = readme_path.read_text()
        assert "CrashLens Policy Violations" in readme_content
        assert "Total Reports: 2" in readme_content
        assert "scan_" in readme_content  # Report filename
    
    def test_metadata_tracking(self):
        """Test metadata persistence."""
        metadata = ReportMetadata(
            file_path="test_report.md",
            timestamp=datetime.now().isoformat(),
            format="markdown",
            detections_count=10,
            severity_summary={"critical": 1, "high": 5, "medium": 4},
            total_waste_cost=5.67,
            total_waste_tokens=5000,
            report_type="scan"
        )
        
        self.organizer.save_report(
            content="Test",
            format="markdown",
            report_type="scan",
            metadata=metadata
        )
        
        # Check metadata file exists
        assert self.organizer.metadata_file.exists()
        
        # Load and verify
        with open(self.organizer.metadata_file) as f:
            data = json.load(f)
        
        assert "reports" in data
        assert len(data["reports"]) == 1
        assert data["reports"][0]["detections_count"] == 10
    
    def test_auto_readme_flag(self):
        """Test auto-README generation flag."""
        # Create organizer with auto_readme=True
        auto_organizer = FileOrganizer(
            base_dir=self.test_dir,
            auto_readme=True
        )
        
        auto_organizer.save_report(
            content="Test",
            format="markdown",
            report_type="scan"
        )
        
        readme_path = self.test_dir / "README.md"
        assert readme_path.exists()  # Should auto-generate


class TestReportMetadata:
    """Test ReportMetadata dataclass."""
    
    def test_metadata_creation(self):
        """Test creating metadata."""
        metadata = ReportMetadata(
            file_path="report.json",
            timestamp="2025-01-25T14:30:00",
            format="json",
            detections_count=3,
            severity_summary={"high": 1, "medium": 2},
            total_waste_cost=2.5,
            total_waste_tokens=2000,
            report_type="guard"
        )
        
        assert metadata.file_path == "report.json"
        assert metadata.detections_count == 3
        assert metadata.report_type == "guard"
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dict."""
        from dataclasses import asdict
        
        metadata = ReportMetadata(
            file_path="report.md",
            timestamp="2025-01-25T15:00:00",
            format="markdown",
            detections_count=1,
            severity_summary={"low": 1},
            total_waste_cost=0.1,
            total_waste_tokens=100,
            report_type="scan"
        )
        
        data = asdict(metadata)
        
        assert isinstance(data, dict)
        assert data["file_path"] == "report.md"
        assert data["format"] == "markdown"
