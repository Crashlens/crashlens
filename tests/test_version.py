"""
Tests for version consistency across CHANGELOG, pyproject.toml, and __init__.py.

Verifies that:
1. crashlens --version outputs the expected version
2. __version__ in crashlens/__init__.py matches expected version
3. version in pyproject.toml matches expected version
4. CHANGELOG.md has an entry for the current version
"""

import re
import tomllib  # Python 3.11+ built-in TOML parser
from pathlib import Path
from click.testing import CliRunner
import pytest

from crashlens import __version__
from crashlens.cli import cli


# Expected version for v3.0.0 release
EXPECTED_VERSION = "3.0.0"


class TestVersionConsistency:
    """Test version consistency across all version sources."""

    def test_init_version_matches_expected(self):
        """Verify __version__ in crashlens/__init__.py matches expected."""
        assert __version__ == EXPECTED_VERSION, (
            f"__version__ in crashlens/__init__.py is '{__version__}', "
            f"expected '{EXPECTED_VERSION}'"
        )

    def test_pyproject_version_matches_expected(self):
        """Verify version in pyproject.toml matches expected."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        version = pyproject_data.get("tool", {}).get("poetry", {}).get("version")
        assert version == EXPECTED_VERSION, (
            f"version in pyproject.toml is '{version}', "
            f"expected '{EXPECTED_VERSION}'"
        )

    def test_changelog_has_version_entry(self):
        """Verify CHANGELOG.md has an entry for the current version."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        assert changelog_path.exists(), "CHANGELOG.md not found"

        with open(changelog_path, "r") as f:
            changelog_content = f.read()

        # Look for version entry in format: ## [2.9.21] - YYYY-MM-DD
        version_pattern = rf"## \[{re.escape(EXPECTED_VERSION)}\]"
        assert re.search(version_pattern, changelog_content), (
            f"CHANGELOG.md does not contain entry for version {EXPECTED_VERSION}. "
            f"Expected pattern: '## [{EXPECTED_VERSION}] - YYYY-MM-DD'"
        )

    def test_cli_version_flag(self):
        """Verify crashlens --version outputs the expected version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0, (
            f"crashlens --version failed with exit code {result.exit_code}. "
            f"Output: {result.output}"
        )

        # Click's version_option outputs: "cli, version X.Y.Z"
        # We need to extract the version from this output
        output = result.output.strip()
        
        # Expected format: "cli, version 2.9.21" or similar
        # Extract version using regex
        version_match = re.search(r"version\s+(\S+)", output)
        assert version_match, (
            f"Could not parse version from --version output: '{output}'"
        )

        cli_version = version_match.group(1)
        assert cli_version == EXPECTED_VERSION, (
            f"crashlens --version reports '{cli_version}', "
            f"expected '{EXPECTED_VERSION}'"
        )

    def test_all_versions_consistent(self):
        """Verify all version sources are consistent with each other."""
        # Read all version sources
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        pyproject_version = pyproject_data.get("tool", {}).get("poetry", {}).get("version")

        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        with open(changelog_path, "r") as f:
            changelog_content = f.read()

        # Extract first version entry from CHANGELOG (most recent)
        changelog_version_match = re.search(r"## \[(\d+\.\d+\.\d+)\]", changelog_content)
        assert changelog_version_match, "Could not find version in CHANGELOG.md"
        changelog_version = changelog_version_match.group(1)

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        version_match = re.search(r"version\s+(\S+)", result.output.strip())
        assert version_match, f"Could not parse version from --version output"
        cli_version = version_match.group(1)

        # All versions should match
        versions = {
            "__init__.py": __version__,
            "pyproject.toml": pyproject_version,
            "CHANGELOG.md": changelog_version,
            "--version flag": cli_version,
        }

        # Check all are equal
        unique_versions = set(versions.values())
        assert len(unique_versions) == 1, (
            f"Version mismatch detected:\n"
            + "\n".join(f"  {source}: {version}" for source, version in versions.items())
        )


class TestVersionFormat:
    """Test version format follows semantic versioning."""

    def test_version_follows_semver(self):
        """Verify version follows semantic versioning format (X.Y.Z)."""
        # Semantic versioning: MAJOR.MINOR.PATCH
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, __version__), (
            f"Version '{__version__}' does not follow semantic versioning format (X.Y.Z)"
        )

    def test_version_components_are_integers(self):
        """Verify version components (major, minor, patch) are valid integers."""
        parts = __version__.split(".")
        assert len(parts) == 3, f"Version should have 3 components, got {len(parts)}"

        for i, part in enumerate(parts):
            try:
                int(part)
            except ValueError:
                pytest.fail(
                    f"Version component {i} ('{part}') is not a valid integer. "
                    f"Full version: {__version__}"
                )


class TestChangelogFormat:
    """Test CHANGELOG.md format and structure."""

    def test_changelog_follows_keepachangelog_format(self):
        """Verify CHANGELOG.md follows Keep a Changelog format."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        with open(changelog_path, "r") as f:
            changelog_content = f.read()

        # Check for required sections
        required_headers = [
            "# Changelog",
            "## [Unreleased]",
        ]

        for header in required_headers:
            assert header in changelog_content, (
                f"CHANGELOG.md missing required header: '{header}'"
            )

    def test_changelog_version_entry_has_date(self):
        """Verify version entry in CHANGELOG.md has a date."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        with open(changelog_path, "r") as f:
            changelog_content = f.read()

        # Look for version entry with date: ## [2.9.21] - YYYY-MM-DD
        version_entry_pattern = rf"## \[{re.escape(EXPECTED_VERSION)}\]\s*-\s*\d{{4}}-\d{{2}}-\d{{2}}"
        match = re.search(version_entry_pattern, changelog_content)
        
        assert match, (
            f"CHANGELOG.md version entry for {EXPECTED_VERSION} is missing a date. "
            f"Expected format: '## [{EXPECTED_VERSION}] - YYYY-MM-DD'"
        )

    def test_changelog_version_entry_has_changes(self):
        """Verify version entry in CHANGELOG.md has change descriptions."""
        changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
        with open(changelog_path, "r") as f:
            changelog_content = f.read()

        # Extract section for current version
        version_pattern = rf"## \[{re.escape(EXPECTED_VERSION)}\].*?(?=## \[|\Z)"
        version_section_match = re.search(version_pattern, changelog_content, re.DOTALL)
        
        assert version_section_match, (
            f"Could not find section for version {EXPECTED_VERSION} in CHANGELOG.md"
        )

        version_section = version_section_match.group(0)

        # Check for standard Keep a Changelog subsections
        # At least one of these should be present
        changelog_subsections = [
            "### Added",
            "### Changed",
            "### Deprecated",
            "### Removed",
            "### Fixed",
            "### Security",
        ]

        has_subsection = any(subsection in version_section for subsection in changelog_subsections)
        assert has_subsection, (
            f"CHANGELOG.md version {EXPECTED_VERSION} section has no change subsections. "
            f"Expected at least one of: {', '.join(changelog_subsections)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
