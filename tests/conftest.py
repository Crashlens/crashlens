"""Pytest configuration for CrashLens test suite.

Configures test markers and collection behavior for proper test isolation.
"""

import pytest
import os


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly enabled.
    
    Integration tests are skipped by default to keep CI fast.
    Enable with: TEST_PROMETHEUS_INTEGRATION=true pytest
    """
    if not os.getenv('TEST_PROMETHEUS_INTEGRATION'):
        skip_integration = pytest.mark.skip(
            reason="Set TEST_PROMETHEUS_INTEGRATION=true to run integration tests"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# Optional: Add fixtures for common test setup
@pytest.fixture
def metrics_disabled():
    """Ensure metrics are disabled for test isolation."""
    import os
    original = os.environ.get('CRASHLENS_DISABLE_METRICS')
    os.environ['CRASHLENS_DISABLE_METRICS'] = 'true'
    yield
    if original:
        os.environ['CRASHLENS_DISABLE_METRICS'] = original
    else:
        os.environ.pop('CRASHLENS_DISABLE_METRICS', None)


@pytest.fixture
def temp_log_file(tmp_path):
    """Create temporary log file for testing."""
    log_file = tmp_path / "test-logs.jsonl"
    log_file.write_text('{"traceId": "test123", "status": "success"}\n')
    return log_file
