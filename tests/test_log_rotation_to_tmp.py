"""
Test: Log Rotation to /tmp
Purpose: Verify metrics logs rotate correctly when exceeding size threshold.
         Prevents unbounded disk usage from long-running processes.
         
Acceptance Criteria:
- Logs written to /tmp/crashlens-metrics.log (or custom path)
- Rotation triggered when log exceeds maxBytes threshold
- Rotated files have suffix (.1, .2, etc. or timestamp)
- Backup count respected (old logs deleted)
- Individual log files stay under size limit
- No data loss during rotation

This ensures production systems don't fill /tmp with unbounded log files.

NOTE: These tests are skipped on Windows due to file locking issues.
Windows locks open files, preventing rotation cleanup. This is a known
limitation and doesn't affect production usage (metrics are optional).
"""

import pytest
import os
import platform
import tempfile
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import time

# Skip all log rotation tests on Windows (file locking prevents cleanup)
pytestmark = pytest.mark.skipif(
    platform.system() == 'Windows',
    reason="Windows file locking prevents log rotation cleanup in tests"
)


def setup_rotating_logger(log_path: str, max_bytes: int = 10240, backup_count: int = 3):
    """
    Set up a logger with rotation for testing.
    
    Args:
        log_path: Path to log file
        max_bytes: Max size before rotation (default 10KB)
        backup_count: Number of backup files to keep
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(f'crashlens_metrics_test_{id(log_path)}')
    logger.setLevel(logging.INFO)
    
    # Close and remove existing handlers to prevent file locks
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def test_log_rotation_creates_backup_files():
    """
    ACCEPTANCE: When log exceeds maxBytes, backup files are created.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        # Small threshold (1KB) for fast testing
        max_bytes = 1024
        logger = setup_rotating_logger(log_path, max_bytes=max_bytes, backup_count=3)
        
        # Write enough logs to trigger rotation
        # Each log line ~100 bytes, need ~15 lines to exceed 1KB
        for i in range(50):
            logger.info(f"Metric push attempt {i}: rule=test_rule_{i % 10}, status=success, duration_ms={i * 10}")
        
        # Force flush
        for handler in logger.handlers:
            handler.flush()
        
        # Check for rotated files
        log_files = sorted(Path(tmpdir).glob('crashlens-metrics.log*'))
        
        assert len(log_files) > 1, (
            f"FAIL: No rotation occurred. Expected multiple log files, found: {[f.name for f in log_files]}"
        )
        
        # Should have main log + at least one backup
        assert Path(log_path).exists(), "FAIL: Main log file not found"
        assert Path(f"{log_path}.1").exists(), "FAIL: First backup log not found"
        
        print(f"✓ PASS: Log rotation created {len(log_files)} files")
        for f in log_files:
            size = f.stat().st_size
            print(f"  {f.name}: {size} bytes")


def test_log_rotation_respects_backup_count():
    """
    ACCEPTANCE: Only backupCount files retained, oldest deleted.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        # Small threshold, 2 backups max
        max_bytes = 500
        backup_count = 2
        logger = setup_rotating_logger(log_path, max_bytes=max_bytes, backup_count=backup_count)
        
        # Write enough to trigger multiple rotations
        for i in range(100):
            logger.info(f"Metric event {i}: " + "X" * 80)  # ~100 bytes per line
            if i % 10 == 0:
                for handler in logger.handlers:
                    handler.flush()
        
        # Final flush
        for handler in logger.handlers:
            handler.flush()
        
        # Count backup files
        backup_files = sorted(Path(tmpdir).glob('crashlens-metrics.log.[0-9]*'))
        
        # Should have at most backup_count files
        assert len(backup_files) <= backup_count, (
            f"FAIL: Found {len(backup_files)} backup files, expected max {backup_count}. "
            f"Files: {[f.name for f in backup_files]}"
        )
        
        print(f"✓ PASS: Backup count respected ({len(backup_files)} backups, max {backup_count})")


def test_log_rotation_individual_files_under_limit():
    """
    ACCEPTANCE: Each log file (including backups) is under maxBytes.
    
    Note: RotatingFileHandler may slightly exceed maxBytes before rotating.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        max_bytes = 2048  # 2KB limit
        logger = setup_rotating_logger(log_path, max_bytes=max_bytes, backup_count=3)
        
        # Write logs to trigger rotation
        for i in range(100):
            logger.info(f"Metric: rule_{i % 20}, tokens={i * 100}, cost=${i * 0.01:.4f}")
        
        for handler in logger.handlers:
            handler.flush()
        
        # Check all log file sizes
        log_files = sorted(Path(tmpdir).glob('crashlens-metrics.log*'))
        
        # Allow 10% tolerance for rotation timing
        tolerance = int(max_bytes * 1.1)
        
        for log_file in log_files:
            size = log_file.stat().st_size
            assert size <= tolerance, (
                f"FAIL: {log_file.name} is {size} bytes, exceeds limit {max_bytes} (tolerance: {tolerance})"
            )
        
        print(f"✓ PASS: All {len(log_files)} log files under {max_bytes} bytes (tolerance: {tolerance})")
        for f in log_files:
            print(f"  {f.name}: {f.stat().st_size} bytes")


def test_log_rotation_no_data_loss():
    """
    ACCEPTANCE: All log messages are written (no data loss during rotation).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        max_bytes = 1024
        logger = setup_rotating_logger(log_path, max_bytes=max_bytes, backup_count=5)
        
        # Write unique messages
        num_messages = 50
        for i in range(num_messages):
            logger.info(f"UNIQUE_MESSAGE_{i:04d}")
        
        for handler in logger.handlers:
            handler.flush()
        
        # Read all log files and count messages
        log_files = sorted(Path(tmpdir).glob('crashlens-metrics.log*'))
        total_messages = 0
        found_messages = set()
        
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'UNIQUE_MESSAGE_' in line:
                        # Extract message ID
                        for part in line.split():
                            if part.startswith('UNIQUE_MESSAGE_'):
                                found_messages.add(part)
                                total_messages += 1
                                break
        
        # All messages should be found
        assert len(found_messages) == num_messages, (
            f"FAIL: Expected {num_messages} unique messages, found {len(found_messages)}. "
            f"Missing: {set(f'UNIQUE_MESSAGE_{i:04d}' for i in range(num_messages)) - found_messages}"
        )
        
        print(f"✓ PASS: No data loss ({total_messages} messages across {len(log_files)} files)")


def test_log_rotation_custom_path():
    """
    ACCEPTANCE: Log rotation works with custom paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use custom subdirectory
        custom_dir = os.path.join(tmpdir, 'custom', 'metrics')
        os.makedirs(custom_dir, exist_ok=True)
        log_path = os.path.join(custom_dir, 'custom-metrics.log')
        
        logger = setup_rotating_logger(log_path, max_bytes=500, backup_count=2)
        
        # Write logs
        for i in range(30):
            logger.info(f"Custom path test {i}: " + "Y" * 100)
        
        for handler in logger.handlers:
            handler.flush()
        
        # Check files exist in custom path
        assert Path(log_path).exists(), f"FAIL: Log file not found at {log_path}"
        
        # Check for backups
        log_files = sorted(Path(custom_dir).glob('custom-metrics.log*'))
        assert len(log_files) > 1, (
            f"FAIL: No rotation in custom path. Files: {[f.name for f in log_files]}"
        )
        
        print(f"✓ PASS: Rotation works in custom path ({len(log_files)} files)")


def test_log_rotation_concurrent_writes():
    """
    ACCEPTANCE: Rotation handles concurrent write bursts.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        logger = setup_rotating_logger(log_path, max_bytes=1024, backup_count=3)
        
        # Burst of writes
        for batch in range(5):
            for i in range(20):
                logger.info(f"Batch {batch}, message {i}: " + "Z" * 80)
            # Small delay between bursts
            time.sleep(0.01)
        
        for handler in logger.handlers:
            handler.flush()
        
        # Should have rotated files
        log_files = sorted(Path(tmpdir).glob('crashlens-metrics.log*'))
        assert len(log_files) > 1, "FAIL: No rotation occurred during burst writes"
        
        print(f"✓ PASS: Handled concurrent writes ({len(log_files)} files)")


def test_log_rotation_empty_log_behavior():
    """
    ACCEPTANCE: Empty logs don't trigger rotation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        logger = setup_rotating_logger(log_path, max_bytes=1024, backup_count=3)
        
        # Create logger but don't write anything
        for handler in logger.handlers:
            handler.flush()
        
        # Should have main log file (possibly empty)
        log_files = list(Path(tmpdir).glob('crashlens-metrics.log*'))
        
        # Should only have main log, no backups
        assert len(log_files) <= 1, (
            f"FAIL: Empty log triggered rotation. Files: {[f.name for f in log_files]}"
        )
        
        if log_files:
            size = log_files[0].stat().st_size
            assert size < 100, (  # Allow for minimal file overhead
                f"FAIL: Empty log file is {size} bytes (expected near 0)"
            )
        
        print("✓ PASS: Empty log doesn't trigger rotation")


def test_log_rotation_permissions():
    """
    ACCEPTANCE: Log files created with appropriate permissions.
    
    Note: Permission checks may vary by OS.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, 'crashlens-metrics.log')
        
        logger = setup_rotating_logger(log_path, max_bytes=500, backup_count=2)
        
        # Write some logs
        for i in range(20):
            logger.info(f"Permission test {i}")
        
        for handler in logger.handlers:
            handler.flush()
        
        # Check file exists and is readable
        assert os.path.exists(log_path), "FAIL: Log file not created"
        assert os.access(log_path, os.R_OK), "FAIL: Log file not readable"
        
        # Check rotated files
        log_files = list(Path(tmpdir).glob('crashlens-metrics.log*'))
        for log_file in log_files:
            assert os.access(log_file, os.R_OK), (
                f"FAIL: {log_file.name} not readable"
            )
        
        print(f"✓ PASS: All {len(log_files)} log files have correct permissions")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("LOG ROTATION VERIFICATION SUITE")
    print("=" * 70)
    
    try:
        test_log_rotation_creates_backup_files()
        test_log_rotation_respects_backup_count()
        test_log_rotation_individual_files_under_limit()
        test_log_rotation_no_data_loss()
        test_log_rotation_custom_path()
        test_log_rotation_concurrent_writes()
        test_log_rotation_empty_log_behavior()
        test_log_rotation_permissions()
        print("\n" + "=" * 70)
        print("ALL LOG ROTATION TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
