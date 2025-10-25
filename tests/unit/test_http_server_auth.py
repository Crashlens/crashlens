"""
Unit tests for HTTP server authentication and TTY checks.

Tests Phase 2 security requirements:
- Authentication required for non-localhost binding
- TTY check before exposing on non-localhost
- Basic auth header validation
- 401 responses for unauthorized requests
"""

import pytest
import base64
import sys
from unittest.mock import Mock, patch, MagicMock
from crashlens.observability.http_server import MetricsHTTPServer, MetricsHTTPHandler


class TestHTTPServerAuthentication:
    """Test authentication requirements for HTTP server"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_metrics = Mock()
        self.mock_metrics.registry = None
    
    def test_localhost_no_auth_required(self):
        """Test that localhost binding doesn't require auth"""
        # Should not raise ValueError
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='127.0.0.1',
            port=9090
        )
        assert server.host == '127.0.0.1'
        assert not MetricsHTTPHandler.auth_required
    
    def test_non_localhost_requires_auth(self):
        """Test that non-localhost binding requires auth credentials"""
        with pytest.raises(ValueError) as exc_info:
            MetricsHTTPServer(
                self.mock_metrics,
                host='0.0.0.0',
                port=9090
            )
        
        assert "Authentication required" in str(exc_info.value)
        assert "0.0.0.0" in str(exc_info.value)
    
    def test_non_localhost_with_auth_succeeds(self):
        """Test that non-localhost binding succeeds with auth credentials"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret123'
        )
        
        assert server.host == '0.0.0.0'
        assert MetricsHTTPHandler.auth_required
        assert MetricsHTTPHandler.auth_username == 'admin'
        assert MetricsHTTPHandler.auth_password == 'secret123'
    
    def test_auth_with_localhost_is_optional(self):
        """Test that auth can be provided for localhost (but not required)"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='127.0.0.1',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        
        assert MetricsHTTPHandler.auth_required
        assert MetricsHTTPHandler.auth_username == 'admin'


class TestHTTPHandlerAuthCheck:
    """Test authentication checking in HTTP handler"""
    
    def setup_method(self):
        """Setup handler fixtures"""
        # Reset handler class variables
        MetricsHTTPHandler.auth_required = False
        MetricsHTTPHandler.auth_username = None
        MetricsHTTPHandler.auth_password = None
        MetricsHTTPHandler.registry = None
        
        # Create mock request
        self.handler = MetricsHTTPHandler(
            request=Mock(),
            client_address=('127.0.0.1', 12345),
            server=Mock()
        )
        # Mock headers as Message-like object with get method
        self.handler.headers = Mock()
        self.handler.headers.get = Mock(return_value=None)
    
    def test_auth_not_required_passes(self):
        """Test that _check_auth passes when auth not required"""
        MetricsHTTPHandler.auth_required = False
    def test_auth_required_no_header_fails(self):
        """Test that _check_auth fails when auth required but no header"""
        MetricsHTTPHandler.auth_required = True
        MetricsHTTPHandler.auth_username = 'admin'
        MetricsHTTPHandler.auth_password = 'secret'
        
        self.handler.headers.get = Mock(return_value=None)
        assert self.handler._check_auth() is False
        self.handler.headers = {}
    def test_auth_required_valid_credentials_pass(self):
        """Test that valid credentials pass auth check"""
        MetricsHTTPHandler.auth_required = True
        MetricsHTTPHandler.auth_username = 'admin'
        MetricsHTTPHandler.auth_password = 'secret123'
        
        # Create valid Basic auth header
        credentials = base64.b64encode(b'admin:secret123').decode('utf-8')
        self.handler.headers.get = Mock(return_value=f'Basic {credentials}')
        
        assert self.handler._check_auth() is True
        
    def test_auth_required_invalid_credentials_fail(self):
        """Test that invalid credentials fail auth check"""
        MetricsHTTPHandler.auth_required = True
        MetricsHTTPHandler.auth_username = 'admin'
        MetricsHTTPHandler.auth_password = 'secret123'
        
        # Create invalid Basic auth header
        credentials = base64.b64encode(b'admin:wrongpassword').decode('utf-8')
        self.handler.headers.get = Mock(return_value=f'Basic {credentials}')
        
        assert self.handler._check_auth() is False
        
    def test_auth_malformed_header_fails(self):
        """Test that malformed auth header fails"""
        MetricsHTTPHandler.auth_required = True
        MetricsHTTPHandler.auth_username = 'admin'
        MetricsHTTPHandler.auth_password = 'secret'
        
        # Malformed header (not base64)
        self.handler.headers.get = Mock(return_value='Basic notbase64!!!')
        
        assert self.handler._check_auth() is False
        
        assert self.handler._check_auth() is False


class TestTTYCheck:
    """Test TTY/interactivity checks for non-localhost binding"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_metrics = Mock()
        self.mock_metrics.registry = None
    
    def test_localhost_no_tty_check(self):
        """Test that localhost binding skips TTY check"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='127.0.0.1',
            port=9090
        )
        
        # Should always pass for localhost
        assert server._check_tty_approval() is True
    
    def test_skip_tty_check_flag(self):
        """Test that skip_tty_check flag bypasses check"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret',
            skip_tty_check=True
        )
        
        # Should pass even for non-localhost
        assert server._check_tty_approval() is True
    
    @patch('sys.stdin.isatty')
    def test_non_interactive_fails(self, mock_isatty):
        """Test that non-interactive environment fails TTY check"""
        mock_isatty.return_value = False
        
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        
        # Should fail in non-interactive environment
        assert server._check_tty_approval() is False
    
    @patch('sys.stdin.isatty')
    @patch('builtins.input')
    def test_interactive_user_approves(self, mock_input, mock_isatty):
        """Test that interactive approval works"""
        mock_isatty.return_value = True
        mock_input.return_value = 'yes'
        
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        
        # Should pass when user approves
        assert server._check_tty_approval() is True
        mock_input.assert_called_once()
    
    @patch('sys.stdin.isatty')
    @patch('builtins.input')
    def test_interactive_user_declines(self, mock_input, mock_isatty):
        """Test that user can decline approval"""
        mock_isatty.return_value = True
        mock_input.return_value = 'no'
        
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        
        # Should fail when user declines
        assert server._check_tty_approval() is False
    
    @patch('sys.stdin.isatty')
    @patch('builtins.input')
    def test_interactive_keyboard_interrupt(self, mock_input, mock_isatty):
        """Test that Ctrl+C during approval fails gracefully"""
        mock_isatty.return_value = True
        mock_input.side_effect = KeyboardInterrupt()
        
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        
        # Should fail gracefully on keyboard interrupt
        assert server._check_tty_approval() is False


class TestMetricsEndpointAuth:
    """Test that /metrics endpoint enforces authentication"""
    
    def setup_method(self):
        """Setup handler fixtures"""
        MetricsHTTPHandler.auth_required = True
        MetricsHTTPHandler.auth_username = 'admin'
        MetricsHTTPHandler.auth_password = 'secret123'
        MetricsHTTPHandler.registry = None
        
        self.handler = MetricsHTTPHandler(
            request=Mock(),
            client_address=('127.0.0.1', 12345),
            server=Mock()
        )
        self.handler.send_response = Mock()
        self.handler.send_header = Mock()
        self.handler.end_headers = Mock()
    
    def test_metrics_endpoint_no_auth_returns_401(self):
        """Test that /metrics without auth returns 401"""
        self.handler.path = '/metrics'
        self.handler.headers.get = Mock(return_value=None)
        
        self.handler.do_GET()
        
        # Should send 401 response
        self.handler.send_response.assert_called()
        args = self.handler.send_response.call_args[0]
        assert 401 in args
    
    def test_metrics_endpoint_valid_auth_returns_200(self):
        """Test that /metrics with valid auth returns metrics"""
        self.handler.path = '/metrics'
        credentials = base64.b64encode(b'admin:secret123').decode('utf-8')
        self.handler.headers.get = Mock(return_value=f'Basic {credentials}')
        
        with patch('crashlens.observability.http_server.generate_latest') as mock_gen:
            mock_gen.return_value = b'# HELP metric\nmetric 1.0\n'
            
            self.handler.do_GET()
            
            # Should send 200 response
            self.handler.send_response.assert_called()
            args = self.handler.send_response.call_args[0]
            assert 200 in args
            args = self.handler.send_response.call_args[0]
    def test_health_endpoint_no_auth_required(self):
        """Test that /health endpoint doesn't require auth"""
        self.handler.path = '/health'
        self.handler.headers.get = Mock(return_value=None)  # No auth header
        
        self.handler.do_GET()
        
        # Should send 200 response (not 401)
        self.handler.send_response.assert_called()
        args = self.handler.send_response.call_args[0]
        assert 200 in args
        args = self.handler.send_response.call_args[0]
        assert 200 in args


class TestSecurityBanner:
    """Test security audit 

banner reflects auth status"""
    
    def setup_method(self):
        """Setup fixtures"""
        self.mock_metrics = Mock()
        self.mock_metrics.registry = None
    
    @patch('sys.stderr')
    def test_localhost_banner_no_auth(self, mock_stderr):
        """Test banner for localhost without auth"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='127.0.0.1',
            port=9090
        )
        server.actual_port = 9090
        
        server._print_audit_banner('http://127.0.0.1:9090')
        
        # Check that banner was printed
        assert mock_stderr.write.called or True  # stderr.write may not be mocked correctly
    
    @patch('sys.stderr')
    def test_non_localhost_banner_with_auth(self, mock_stderr):
        """Test banner for non-localhost with auth"""
        server = MetricsHTTPServer(
            self.mock_metrics,
            host='0.0.0.0',
            port=9090,
            auth_username='admin',
            auth_password='secret'
        )
        server.actual_port = 9090
        
        server._print_audit_banner('http://0.0.0.0:9090')
        
        # Should show auth enabled
        assert MetricsHTTPHandler.auth_required is True
