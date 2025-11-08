"""
Preflight checks for CrashLens guard/guard merge.

This test suite verifies that all required files and directories
exist before beginning the migration.
"""

import pytest
from pathlib import Path


# Required files for the migration
REQUIRED_FILES = [
    "crashlens/guard.py",
    "crashlens/cli.py",
    "crashlens/policy/engine.py",
    "crashlens/parsers/langfuse.py",
    ".crashlens/rules.yaml",
    "docs/GUARD.md",
    "docs/COMMAND-REFERENCE.md",
    "crashlens/utils/feature_flags.py",
    "docs/migration_teardown.md",
]

REQUIRED_DIRS = [
    "crashlens/detectors",
    "crashlens/policy",
    "crashlens/parsers",
    "crashlens/formatters",
    "tests",
]


def test_required_files_exist():
    """Verify all required files exist in the repository."""
    repo_root = Path(__file__).parent.parent
    missing_files = []
    
    for file_path in REQUIRED_FILES:
        full_path = repo_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        pytest.fail(
            f"Missing required files:\n" + 
            "\n".join(f"  - {f}" for f in missing_files) +
            "\n\nPlease ensure all required files exist before proceeding."
        )


def test_required_directories_exist():
    """Verify all required directories exist in the repository."""
    repo_root = Path(__file__).parent.parent
    missing_dirs = []
    
    for dir_path in REQUIRED_DIRS:
        full_path = repo_root / dir_path
        if not full_path.is_dir():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        pytest.fail(
            f"Missing required directories:\n" + 
            "\n".join(f"  - {d}" for d in missing_dirs) +
            "\n\nPlease ensure all required directories exist before proceeding."
        )


def test_feature_flags_module():
    """Verify feature flags module is importable and functional."""
    try:
        from crashlens.utils.feature_flags import is_unified_enabled, set_unified_enabled
        
        # Test default state
        set_unified_enabled(False)
        assert not is_unified_enabled()
        
        # Test enabled state
        set_unified_enabled(True)
        assert is_unified_enabled()
        
        # Reset to default
        set_unified_enabled(False)
        
    except ImportError as e:
        pytest.fail(f"Cannot import feature_flags module: {e}")


def test_guard_module_importable():
    """Verify guard module can be imported."""
    try:
        import crashlens.guard
    except ImportError as e:
        pytest.fail(f"Cannot import guard module: {e}")


def test_policy_engine_importable():
    """Verify policy engine can be imported."""
    try:
        from crashlens.policy.engine import PolicyEngine
    except ImportError as e:
        pytest.fail(f"Cannot import PolicyEngine: {e}")


def test_langfuse_parser_importable():
    """Verify Langfuse parser can be imported."""
    try:
        from crashlens.parsers.langfuse import LangfuseParser
    except ImportError as e:
        pytest.fail(f"Cannot import LangfuseParser: {e}")


def test_detectors_importable():
    """Verify detector modules can be imported."""
    repo_root = Path(__file__).parent.parent
    detectors_dir = repo_root / "crashlens" / "detectors"
    
    if not detectors_dir.exists():
        pytest.fail(f"Detectors directory does not exist: {detectors_dir}")
    
    # Check that at least some detector files exist
    detector_files = list(detectors_dir.glob("*.py"))
    detector_files = [f for f in detector_files if f.name != "__init__.py"]
    
    if not detector_files:
        pytest.fail(f"No detector files found in {detectors_dir}")
    
    # Try importing at least one detector
    try:
        from crashlens.detectors.retry_loops import RetryLoopDetector
    except ImportError as e:
        pytest.fail(f"Cannot import RetryLoopDetector: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
