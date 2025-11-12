"""
File organization system for CrashLens reports.

Implements subdirectory structure with automatic README generation:
- policy-violations/
  ├── reports/          # Formatted reports (markdown, HTML, JSON)
  ├── traces/           # Raw trace data (JSONL)
  ├── archives/         # Archived reports older than retention period
  └── README.md         # Auto-generated index

Features:
- Automatic subdirectory creation
- README.md generation with latest reports
- Archival logic (configurable retention period)
- Report metadata tracking
- Prune command for cleanup
"""

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportMetadata:
    """Metadata for a generated report."""

    file_path: str
    timestamp: str
    format: str  # markdown, json, html, slack
    detections_count: int
    severity_summary: Dict[str, int]
    total_waste_cost: float
    total_waste_tokens: int
    report_type: str  # scan, guard, policy-check


class FileOrganizer:
    """
    Organizes CrashLens reports into structured directories.

    Directory Structure:
        policy-violations/
        ├── reports/
        │   ├── scan_2025-01-25_14-30-00.md
        │   ├── guard_2025-01-25_15-45-00.json
        │   └── scan_2025-01-26_09-00-00.html
        ├── traces/
        │   ├── trace_abc123.jsonl
        │   └── trace_def456.jsonl
        ├── archives/
        │   └── 2025-01/
        │       ├── old_scan_2025-01-01.md
        │       └── old_guard_2025-01-05.json
        └── README.md

    Usage:
        organizer = FileOrganizer(base_dir=Path("policy-violations"))
        
        # Save report
        report_path = organizer.save_report(
            content="# Report...",
            format="markdown",
            report_type="scan",
            metadata=ReportMetadata(...)
        )
        
        # Save trace
        trace_path = organizer.save_trace(
            trace_id="abc123",
            content='{"traceId": "abc123", ...}'
        )
        
        # Archive old reports (older than 30 days)
        archived = organizer.archive_old_reports(days=30)
        
        # Prune archives (delete older than 90 days)
        pruned = organizer.prune_archives(days=90)
        
        # Generate README
        organizer.generate_readme()
    """

    def __init__(self, base_dir: Path, auto_readme: bool = True):
        """
        Initialize file organizer.

        Args:
            base_dir: Base directory for all reports (e.g., "policy-violations")
            auto_readme: Automatically regenerate README.md after each operation
        """
        self.base_dir = base_dir
        self.auto_readme = auto_readme

        # Define subdirectories
        self.reports_dir = self.base_dir / "reports"
        self.traces_dir = self.base_dir / "traces"
        self.archives_dir = self.base_dir / "archives"

        # Metadata tracking file
        self.metadata_file = self.base_dir / ".metadata.json"

        # Create directory structure
        self._initialize_directories()

    def _initialize_directories(self) -> None:
        """Create directory structure if it doesn't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.traces_dir.mkdir(exist_ok=True)
        self.archives_dir.mkdir(exist_ok=True)

        logger.debug(
            f"Initialized directory structure at {self.base_dir.absolute()}"
        )

    def save_report(
        self,
        content: str,
        format: str,
        report_type: str,
        metadata: Optional[ReportMetadata] = None,
    ) -> Path:
        """
        Save report to reports/ subdirectory.

        Args:
            content: Report content
            format: Format (markdown, json, html, slack)
            report_type: Type of report (scan, guard, policy-check)
            metadata: Optional metadata to track

        Returns:
            Path to saved report file
        """
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        extension = self._get_extension(format)
        filename = f"{report_type}_{timestamp}.{extension}"
        file_path = self.reports_dir / filename

        # Write content
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved report: {file_path.relative_to(self.base_dir)}")

        # Track metadata if provided
        if metadata:
            self._save_metadata(metadata)

        # Regenerate README
        if self.auto_readme:
            self.generate_readme()

        return file_path

    def save_trace(self, trace_id: str, content: str) -> Path:
        """
        Save raw trace data to traces/ subdirectory.

        Args:
            trace_id: Trace identifier
            content: Trace content (typically JSONL format)

        Returns:
            Path to saved trace file
        """
        filename = f"trace_{trace_id}.jsonl"
        file_path = self.traces_dir / filename

        # Write content
        file_path.write_text(content, encoding="utf-8")
        logger.debug(f"Saved trace: {file_path.relative_to(self.base_dir)}")

        return file_path

    def archive_old_reports(self, days: int = 30) -> List[Path]:
        """
        Move reports older than specified days to archives/.

        Args:
            days: Archive reports older than this many days

        Returns:
            List of archived file paths
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        archived_files = []

        for report_file in self.reports_dir.iterdir():
            if not report_file.is_file():
                continue

            # Check file modification time
            mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
            if mtime < cutoff_date:
                # Create archive subdirectory by month
                archive_month = mtime.strftime("%Y-%m")
                archive_subdir = self.archives_dir / archive_month
                archive_subdir.mkdir(exist_ok=True)

                # Move file to archive
                dest_path = archive_subdir / report_file.name
                shutil.move(str(report_file), str(dest_path))
                archived_files.append(dest_path)
                logger.info(
                    f"Archived: {report_file.name} → {dest_path.relative_to(self.base_dir)}"
                )

        # Regenerate README after archiving
        if archived_files and self.auto_readme:
            self.generate_readme()

        return archived_files

    def prune_archives(self, days: int = 90) -> List[Path]:
        """
        Delete archived reports older than specified days.

        Args:
            days: Delete archives older than this many days

        Returns:
            List of pruned file paths
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        pruned_files = []

        for archive_file in self.archives_dir.rglob("*"):
            if not archive_file.is_file():
                continue

            # Check file modification time
            mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
            if mtime < cutoff_date:
                archive_file.unlink()
                pruned_files.append(archive_file)
                logger.info(f"Pruned: {archive_file.relative_to(self.base_dir)}")

        return pruned_files

    def generate_readme(self) -> Path:
        """
        Generate README.md with index of reports.

        Returns:
            Path to generated README.md
        """
        readme_path = self.base_dir / "README.md"

        # Collect report metadata
        recent_reports = self._get_recent_reports(limit=10)
        stats = self._calculate_statistics()

        # Generate markdown content
        content = self._build_readme_content(recent_reports, stats)

        # Write README
        readme_path.write_text(content, encoding="utf-8")
        logger.debug(f"Generated README: {readme_path}")

        return readme_path

    def _get_extension(self, format: str) -> str:
        """Map format to file extension."""
        extensions = {
            "markdown": "md",
            "json": "json",
            "html": "html",
            "slack": "txt",
        }
        return extensions.get(format, "txt")

    def _save_metadata(self, metadata: ReportMetadata) -> None:
        """Save metadata to tracking file."""
        # Load existing metadata
        if self.metadata_file.exists():
            existing = json.loads(self.metadata_file.read_text())
        else:
            existing = {"reports": []}

        # Add new metadata
        existing["reports"].append(asdict(metadata))

        # Keep only last 100 entries
        existing["reports"] = existing["reports"][-100:]

        # Write back
        self.metadata_file.write_text(
            json.dumps(existing, indent=2), encoding="utf-8"
        )

    def _get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent reports with metadata."""
        reports = []

        for report_file in sorted(
            self.reports_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True
        ):
            if not report_file.is_file():
                continue

            mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
            reports.append(
                {
                    "name": report_file.name,
                    "path": str(report_file.relative_to(self.base_dir)),
                    "size": report_file.stat().st_size,
                    "modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            if len(reports) >= limit:
                break

        return reports

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics about reports."""
        total_reports = sum(1 for _ in self.reports_dir.iterdir())
        total_traces = sum(1 for _ in self.traces_dir.iterdir())
        total_archives = sum(1 for _ in self.archives_dir.rglob("*") if _.is_file())

        return {
            "total_reports": total_reports,
            "total_traces": total_traces,
            "total_archives": total_archives,
        }

    def _build_readme_content(
        self, recent_reports: List[Dict[str, Any]], stats: Dict[str, Any]
    ) -> str:
        """Build README.md content."""
        content = f"""# CrashLens Policy Violations

This directory contains organized reports from CrashLens token waste detection.

## Directory Structure

- **reports/** - Formatted reports (Markdown, JSON, HTML)
- **traces/** - Raw trace data (JSONL format)
- **archives/** - Archived reports (organized by month)

## Statistics

- Total Reports: {stats['total_reports']}
- Total Traces: {stats['total_traces']}
- Archived Reports: {stats['total_archives']}

## Recent Reports

"""

        if recent_reports:
            for report in recent_reports:
                size_kb = report["size"] / 1024
                content += f"- **{report['name']}** ({size_kb:.1f} KB) - {report['modified']}\n"
        else:
            content += "*No reports generated yet.*\n"

        content += f"""

## Maintenance

### Archive Old Reports
```bash
crashlens reports archive --days 30
```

### Prune Archives
```bash
crashlens reports prune --days 90
```

### Regenerate This README
```bash
crashlens reports readme
```

---

*Generated by CrashLens File Organizer*  
*Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return content
