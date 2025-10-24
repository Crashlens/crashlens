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
    config.addinivalue_line(
        "markers",
        "requires_prometheus: mark test as requiring prometheus_client"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (deselect with '-m \"not slow\"')"
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


# ============================================================================
# Prometheus Integration Test Fixtures
# ============================================================================

# Check if prometheus_client is available
try:
    from prometheus_client import CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@pytest.fixture
def reset_modules():
    """
    Clean sys.modules to remove crashlens and prometheus_client imports.
    
    Use this fixture to test lazy loading behavior from a clean slate.
    
    Usage:
        def test_lazy_loading(reset_modules):
            reset_modules(['crashlens', 'prometheus_client'])
            import crashlens.cli
            # Assert prometheus_client not in sys.modules
    
    Yields:
        Function that accepts list of module prefixes to remove
    """
    import sys
    original_modules = dict(sys.modules)
    
    def _reset(prefixes: list):
        """Remove modules matching any of the prefixes."""
        modules_to_remove = [
            name for name in sys.modules.keys()
            if any(name.startswith(prefix) for prefix in prefixes)
        ]
        for name in modules_to_remove:
            del sys.modules[name]
    
    yield _reset
    
    # Restore original modules after test
    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.fixture
def mock_push_to_gateway():
    """
    Mock prometheus_client.push_to_gateway for testing.
    
    Usage:
        def test_push(mock_push_to_gateway):
            with mock_push_to_gateway() as mock:
                mock.return_value = None  # Success
                # ... call push logic
                assert mock.call_count == 1
    
    Yields:
        Context manager that patches push_to_gateway
    """
    from unittest.mock import patch
    
    def _mock_push():
        return patch('prometheus_client.push_to_gateway', return_value=None)
    
    return _mock_push


@pytest.fixture
def mock_registry():
    """
    Provide a fresh CollectorRegistry for each test.
    
    Usage:
        def test_metrics(mock_registry):
            counter = Counter('test', 'Test counter', registry=mock_registry)
            counter.inc()
            # Assert metrics in registry
    
    Returns:
        CollectorRegistry instance (or None if prometheus_client not available)
    """
    if PROMETHEUS_AVAILABLE:
        return CollectorRegistry()
    else:
        pytest.skip("prometheus_client not installed")


@pytest.fixture
def clean_env():
    """
    Provide a clean environment for testing env var behavior.
    
    Usage:
        def test_env_var(clean_env):
            with clean_env:
                os.environ['CRASHLENS_ENABLE_METRICS'] = '1'
                # ... test logic
            # Env restored after with block
    
    Yields:
        Context manager for environment cleanup
    """
    class EnvManager:
        def __enter__(self):
            self.original_env = dict(os.environ)
            # Clear specific crashlens env vars
            for key in list(os.environ.keys()):
                if key.startswith('CRASHLENS_'):
                    del os.environ[key]
            return self
        
        def __exit__(self, *args):
            # Restore original environment
            os.environ.clear()
            os.environ.update(self.original_env)
    
    return EnvManager()


@pytest.fixture
def sample_traces():
    """
    Generate sample Langfuse trace data for testing.
    
    Usage:
        def test_detector(sample_traces):
            traces = sample_traces(count=10)
            # ... run detector
    
    Returns:
        Function that generates N traces
    """
    def _generate_traces(count: int = 10):
        traces = {}
        for i in range(count):
            trace_id = f"trace_{i:04d}"
            traces[trace_id] = [{
                'traceId': trace_id,
                'model': 'gpt-4' if i % 3 == 0 else 'gpt-3.5-turbo',
                'prompt_tokens': 100 + (i * 10),
                'completion_tokens': 50 + (i * 5),
                'cost': (100 + i * 10) * 0.00003 + (50 + i * 5) * 0.00006,
                'startTime': '2024-01-15T10:00:00Z',
                'endTime': '2024-01-15T10:00:05Z',
                'metadata': {
                    'route': f'route_{i % 3}',
                    'team': f'team_{i % 2}'
                }
            }]
        return traces
    
    return _generate_traces


@pytest.fixture
def sample_policies():
    """
    Generate sample policy rules for testing.
    
    Usage:
        def test_policy_engine(sample_policies):
            policies = sample_policies(count=5)
            # ... run policy check
    
    Returns:
        Function that generates N policy rules
    """
    def _generate_policies(count: int = 5):
        policies = []
        for i in range(count):
            policies.append({
                'id': f'policy_{i:03d}',
                'description': f'Test policy {i}',
                'match': {
                    'model': 'gpt-4' if i % 2 == 0 else 'gpt-3.5-turbo',
                    'cost': f'> {i * 0.1}'
                },
                'action': 'warn',
                'severity': 'medium',
                'suggestion': f'Suggestion for policy {i}'
            })
        return policies
    
    return _generate_policies
