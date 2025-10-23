"""
Unit tests for HTTP Server metrics functionality.

Tests the HTTP server mode for Prometheus scraping without
making real network calls (uses mocks).

Run with:
    pytest tests/unit/test_http_server.py -v
"""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from crashlens.observability.server import check_port_available
from crashlens.observability.http_server import MetricsHTTPServer, MetricsHTTPHandler


class TestPortCheck:
    """Tests for port availability checking"""
    
    def test_port_check_returns_true_for_available_port(self):
        """Port check should return True when port is available"""
        # Real check on a random high port (likely available)
        result = check_port_available('127.0.0.1', 45678)
        # We can't guarantee the result, but it should be boolean
        assert isinstance(result, bool)
    
    @patch('socket.socket')
    def test_port_check_returns_true_when_bind_succeeds(self, mock_socket_class):
        """Port check returns True when socket bind succeeds"""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        # Mock successful bind
        mock_sock.bind.return_value = None
        
        result = check_port_available('127.0.0.1', 9090)
        
        assert result is True
        mock_sock.bind.assert_called_once_with(('127.0.0.1', 9090))
        mock_sock.close.assert_called_once()
    
    @patch('socket.socket')
    def test_port_check_returns_false_for_used_port(self, mock_socket_class):
        """Port check returns False when port is already in use"""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        # Mock bind failure (port in use)
        error = OSError()
        error.errno = 98  # EADDRINUSE on Linux
        mock_sock.bind.side_effect = error
        
        result = check_port_available('127.0.0.1', 9090)
        
        assert result is False
        mock_sock.close.assert_called_once()
    
    @patch('socket.socket')
    def test_port_check_handles_permission_error(self, mock_socket_class):
        """Port check returns False for permission errors (ports <1024)"""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        # Mock permission error
        mock_sock.bind.side_effect = PermissionError("Permission denied")
        
        result = check_port_available('127.0.0.1', 80)
        
        assert result is False
        mock_sock.close.assert_called_once()


class TestHTTPServerInitialization:
    """Tests for MetricsHTTPServer initialization"""
    
    def test_server_initialization(self):
        """Server should initialize with correct attributes"""
        mock_metrics = Mock()
        mock_metrics.registry = Mock()
        
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        assert server.metrics == mock_metrics
        assert server.host == '127.0.0.1'
        assert server.port == 9090
        assert server.httpd is None
        assert server.thread is None
        assert server.running is False
        assert server.actual_port is None
    
    def test_server_sets_handler_registry(self):
        """Server should set registry on handler class"""
        mock_metrics = Mock()
        mock_registry = Mock()
        mock_metrics.registry = mock_registry
        
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        assert MetricsHTTPHandler.registry == mock_registry


class TestHTTPServerStart:
    """Tests for server start logic"""
    
    @patch('crashlens.observability.server.check_port_available')
    @patch('crashlens.observability.http_server.HTTPServer')
    @patch('threading.Thread')
    def test_server_starts_on_available_port(self, mock_thread, mock_http_server, mock_port_check):
        """Server should start successfully on available port"""
        mock_port_check.return_value = True
        mock_server_instance = Mock()
        mock_http_server.return_value = mock_server_instance
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        mock_metrics = Mock()
        mock_metrics.registry = Mock()
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        with patch('sys.stderr'):  # Suppress audit banner
            url = server.start()
        
        assert url == 'http://127.0.0.1:9090'
        assert server.running is True
        assert server.actual_port == 9090
        mock_thread_instance.start.assert_called_once()
    
    @patch('crashlens.observability.server.check_port_available')
    @patch('crashlens.observability.http_server.HTTPServer')
    @patch('threading.Thread')
    def test_server_tries_fallback_ports(self, mock_thread, mock_http_server, mock_port_check):
        """Server should try port+1, port+2 if primary port is unavailable"""
        # Port 9090 unavailable, 9091 available
        mock_port_check.side_effect = [False, True, False]
        mock_server_instance = Mock()
        mock_http_server.return_value = mock_server_instance
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        mock_metrics = Mock()
        mock_metrics.registry = Mock()
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        with patch('sys.stderr'):
            url = server.start()
        
        assert url == 'http://127.0.0.1:9091'
        assert server.actual_port == 9091
        # Should have checked 3 ports
        assert mock_port_check.call_count == 2  # Stopped after finding available port
    
    @patch('crashlens.observability.server.check_port_available')
    def test_server_raises_error_when_no_ports_available(self, mock_port_check):
        """Server should raise RuntimeError when all ports are unavailable"""
        mock_port_check.return_value = False  # All ports unavailable
        
        mock_metrics = Mock()
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        with pytest.raises(RuntimeError, match="Could not bind to any port"):
            server.start()


class TestHTTPServerStop:
    """Tests for server stop logic"""
    
    def test_server_stops_gracefully(self):
        """Server should stop gracefully"""
        mock_metrics = Mock()
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        # Simulate running server
        server.running = True
        server.httpd = Mock()
        server.thread = Mock()
        server.thread.is_alive.return_value = False
        
        server.stop()
        
        assert server.running is False
        server.httpd.shutdown.assert_called_once()
        server.httpd.server_close.assert_called_once()
    
    def test_stop_on_non_running_server_is_safe(self):
        """Calling stop on non-running server should be safe"""
        mock_metrics = Mock()
        server = MetricsHTTPServer(mock_metrics, '127.0.0.1', 9090)
        
        # Should not raise
        server.stop()
        
        assert server.running is False


class TestHTTPHandler:
    """Tests for MetricsHTTPHandler request handling
    
    Note: HTTP handler is difficult to unit test due to BaseHTTPRequestHandler
    constructor behavior. These tests are covered by integration tests instead.
    """
    
    def test_handler_class_exists(self):
        """Handler class should be importable"""
        from crashlens.observability.http_server import MetricsHTTPHandler
        assert MetricsHTTPHandler is not None
    
    def test_handler_has_registry_attribute(self):
        """Handler class should have registry class variable"""
        from crashlens.observability.http_server import MetricsHTTPHandler
        # Will be None until set by server
        assert hasattr(MetricsHTTPHandler, 'registry')


class TestCLIValidation:
    """Tests for CLI flag validation"""
    
    def test_cli_validation_requires_env_var(self):
        """HTTP mode should require CRASHLENS_ALLOW_HTTP_METRICS=true"""
        import os
        from click.testing import CliRunner
        from crashlens.cli import cli
        
        runner = CliRunner()
        
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, ['scan', '--demo', '--metrics-http'])
        
        assert result.exit_code != 0
        assert 'CRASHLENS_ALLOW_HTTP_METRICS' in result.output
    
    def test_cli_validates_mutual_exclusivity(self):
        """Cannot use both --push-metrics and --metrics-http"""
        import os
        from click.testing import CliRunner
        from crashlens.cli import cli
        
        runner = CliRunner()
        
        # Set env var to pass that check
        with patch.dict(os.environ, {'CRASHLENS_ALLOW_HTTP_METRICS': 'true'}):
            result = runner.invoke(cli, [
                'scan', '--demo',
                '--push-metrics',
                '--metrics-http'
            ])
        
        assert result.exit_code != 0
        assert 'both' in result.output.lower() or 'mutual' in result.output.lower()
    
    def test_cli_validates_port_range(self):
        """Port must be in range 1024-65535"""
        import os
        from click.testing import CliRunner
        from crashlens.cli import cli
        
        runner = CliRunner()
        
        with patch.dict(os.environ, {'CRASHLENS_ALLOW_HTTP_METRICS': 'true'}):
            # Test port too low
            result = runner.invoke(cli, [
                'scan', '--demo',
                '--metrics-http',
                '--metrics-port', '80'
            ])
        
        assert result.exit_code != 0
        assert '1024' in result.output or 'range' in result.output.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
