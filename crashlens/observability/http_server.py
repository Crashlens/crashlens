"""
HTTP Server for Prometheus Metrics Scraping

This module implements an HTTP server that exposes Crash Lens metrics for
Prometheus scraping as an alternative to Pushgateway push mode.

Security Model:
- Localhost-only default (127.0.0.1)
- Explicit opt-in required (CRASHLENS_ALLOW_HTTP_METRICS=true)
- Mutually exclusive with push mode
- Port range validation (1024-65535)
- Read-only endpoints only

Endpoints:
- GET /metrics - Prometheus text format metrics
- GET /health - Health check (200 OK)
- All others - 404 Not Found

Design:
- Runs in daemon thread (doesn't block CLI exit)
- Graceful shutdown support
- Automatic port fallback (tries port, port+1, port+2)
- Clear audit banner on start
"""

import sys
import os
import os
import threading
import time
import logging
import base64
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Any, Tuple
from typing import Optional, Any, Tuple
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Configure logger
_http_logger = logging.getLogger("crashlens.observability.http")
_http_logger.setLevel(logging.INFO)

if not _http_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    _http_logger.addHandler(handler)


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for Prometheus metrics.
    
    Handles:
    - GET /metrics -> Return Prometheus metrics (with optional auth)
    - GET /health -> Return 200 OK (no auth required)
    - All other requests -> 404
    
    Security:
    - Basic authentication support (if credentials configured)
    - Localhost-only default binding
    - Read-only endpoints
    
    Security:
    - Basic authentication support (if credentials configured)
    - Localhost-only default binding
    - Read-only endpoints
    """
    
    # Class variables to hold config
    registry: Optional[Any] = None
    auth_required: bool = False
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        _http_logger.info(f"{self.address_string()} - {format % args}")
    
    def _check_auth(self) -> bool:
        """
        Check HTTP Basic Authentication credentials.
        
        Returns:
            True if auth passes or not required, False otherwise
        """
        if not self.auth_required:
            return True
        
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return False
        
        try:
            # Decode base64 credentials
            encoded_creds = auth_header[6:]  # Remove 'Basic ' prefix
            decoded = base64.b64decode(encoded_creds).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            # Check credentials
            return (username == self.auth_username and 
                    password == self.auth_password)
        except Exception as e:
            _http_logger.warning(f"Auth check failed: {e}")
            return False
    
    def _send_auth_required(self):
        """Send 401 Unauthorized response"""
        try:
            message = b"401 Unauthorized\n\nBasic authentication required.\n"
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="CrashLens Metrics"')
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(message)))
            self.end_headers()
            self.wfile.write(message)
        except Exception as e:
            _http_logger.error(f"Error sending 401: {e}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/metrics':
                # Auth required for metrics endpoint
                if not self._check_auth():
                    self._send_auth_required()
                    return
                self._handle_metrics()
            elif self.path == '/health':
                # No auth for health check
                self._handle_health()
            else:
                self._handle_not_found()
        except Exception as e:
            _http_logger.error(f"Error handling request: {e}")
            self._handle_error(str(e))
    
    def _handle_metrics(self):
        """Handle /metrics endpoint - return Prometheus format"""
        try:
            # Generate metrics in Prometheus text format
            if self.registry:
                output = generate_latest(self.registry)
            else:
                # Fallback to default registry
                output = generate_latest()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.send_header('Content-Length', str(len(output)))
            self.end_headers()
            self.wfile.write(output)
            
        except Exception as e:
            _http_logger.error(f"Error generating metrics: {e}")
            self._handle_error(f"Metrics generation failed: {e}")
    
    def _handle_health(self):
        """Handle /health endpoint - return 200 OK"""
        try:
            response = b"OK\n"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            _http_logger.error(f"Error in health check: {e}")
            self._handle_error(str(e))
    
    def _handle_not_found(self):
        """Handle unknown endpoints - return 404"""
        try:
            message = f"404 Not Found: {self.path}\n\nAvailable endpoints:\n  GET /metrics\n  GET /health\n"
            response = message.encode('utf-8')
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            _http_logger.error(f"Error sending 404: {e}")
    
    def _handle_error(self, error_msg: str):
        """Handle internal server errors - return 500"""
        try:
            message = f"500 Internal Server Error\n\n{error_msg}\n"
            response = message.encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception:
            pass  # Can't do much if error handling fails


class MetricsHTTPServer:
    """
    HTTP server for exposing Prometheus metrics.
    
    Features:
    - Runs in background daemon thread
    - Automatic port fallback
    - Graceful shutdown
    - Security audit banner
    - Optional Basic authentication
    - TTY/interactivity checks
    
    Security Model:
    - Localhost (127.0.0.1) binding = no auth required
    - Non-localhost binding = auth required (or explicit override)
    - TTY check before exposing on non-localhost
    - Optional Basic authentication
    - TTY/interactivity checks
    
    Security Model:
    - Localhost (127.0.0.1) binding = no auth required
    - Non-localhost binding = auth required (or explicit override)
    - TTY check before exposing on non-localhost
    
    Example:
        >>> # Localhost - no auth
        >>> # Localhost - no auth
        >>> server = MetricsHTTPServer(metrics, '127.0.0.1', 9090)
        >>> url = server.start()
        
        >>> # Non-localhost - auth required
        >>> server = MetricsHTTPServer(
        ...     metrics, '0.0.0.0', 9090,
        ...     auth_username='admin', auth_password='secret123'
        ... )
        >>> url = server.start()
        
        >>> # Non-localhost - auth required
        >>> server = MetricsHTTPServer(
        ...     metrics, '0.0.0.0', 9090,
        ...     auth_username='admin', auth_password='secret123'
        ... )
        >>> url = server.start()
    """
    
    def __init__(
        self,
        metrics: Any,
        host: str = '127.0.0.1',
        port: int = 9090,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
        skip_tty_check: bool = False
    ):
        """
        Initialize HTTP server for metrics.
        
        Args:
            metrics: CrashLensMetrics instance (for registry access)
            host: IP address to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 9090)
            auth_username: Username for Basic auth (required for non-localhost)
            auth_password: Password for Basic auth (required for non-localhost)
            skip_tty_check: Skip TTY check (for automated environments)
        
        Raises:
            ValueError: If non-localhost binding without auth credentials
            auth_username: Username for Basic auth (required for non-localhost)
            auth_password: Password for Basic auth (required for non-localhost)
            skip_tty_check: Skip TTY check (for automated environments)
        
        Raises:
            ValueError: If non-localhost binding without auth credentials
        """
        self.metrics = metrics
        self.host = host
        self.port = port
        self.httpd: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.actual_port: Optional[int] = None
        self.skip_tty_check = skip_tty_check
        # Determine if auth is required (non-localhost should provide credentials)
        is_localhost = host in ('127.0.0.1', 'localhost', '::1')

        if not is_localhost:
            # Non-localhost requires auth
            if not auth_username or not auth_password:
                raise ValueError(
                    f"Authentication required for non-localhost binding ({host}).\n"
                    "Provide auth_username and auth_password, or bind to 127.0.0.1.\n"
                    "See docs/HTTP_SERVER_SECURITY.md for details."
                )

        # Set registry and auth config for handler
        if hasattr(metrics, 'registry'):
            MetricsHTTPHandler.registry = metrics.registry
        else:
            MetricsHTTPHandler.registry = None

        # Configure authentication
        if auth_username and auth_password:
            MetricsHTTPHandler.auth_required = True
            MetricsHTTPHandler.auth_username = auth_username
            MetricsHTTPHandler.auth_password = auth_password
        else:
            MetricsHTTPHandler.auth_required = False
    
    def _check_tty_approval(self) -> bool:
        """
        Check if running in interactive TTY and get user approval for non-localhost.
        
        Returns:
            True if approved or check skipped, False otherwise
        """
        if self.skip_tty_check:
            return True

        # Only check for non-localhost bindings
        is_localhost = self.host in ('127.0.0.1', 'localhost', '::1')
        if is_localhost:
            return True

        # Check if stdin is a TTY
        if not sys.stdin.isatty():
            _http_logger.error(
                f"Cannot bind to {self.host} in non-interactive environment. "
                "Use --skip-tty-check flag if intentional."
            )
            return False

        # Interactive approval
        print(f"\n⚠️  WARNING: You are about to expose metrics on {self.host}:{self.port}", file=sys.stderr)
        print("   This will be accessible from other machines on the network.", file=sys.stderr)
        print("   Authentication is enabled. Credentials required for access.", file=sys.stderr)

        try:
            response = input("\nProceed? (yes/no): ").strip().lower()
            return response in ('yes', 'y')
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            return False
    
    def start(self) -> str:
        """
        Start HTTP server in background thread.
        
        Returns:
            Server URL (e.g., 'http://127.0.0.1:9090')
        
        Raises:
            RuntimeError: If server cannot bind to any port or TTY check fails
            RuntimeError: If server cannot bind to any port or TTY check fails
        
        Process:
        1. Check TTY approval for non-localhost bindings
        2. Check if port is available
        3. If not, try port+1, port+2
        4. If all fail, raise RuntimeError
        5. Start server in daemon thread
        6. Print security audit banner to stderr
        7. Return server URL
        1. Check TTY approval for non-localhost bindings
        2. Check if port is available
        3. If not, try port+1, port+2
        4. If all fail, raise RuntimeError
        5. Start server in daemon thread
        6. Print security audit banner to stderr
        7. Return server URL
        """
        # Check TTY approval first
        if not self._check_tty_approval():
            raise RuntimeError(
                f"TTY approval required for non-localhost binding to {self.host}. "
                "User declined or non-interactive environment detected. "
                "Use --skip-tty-check flag to bypass (NOT recommended for production)."
            )
        
        # Import here to avoid circular dependency
        from crashlens.observability.server import check_port_available
        
        # Try to find an available port
        ports_to_try = [self.port, self.port + 1, self.port + 2]
        bound_port = None
        
        for port in ports_to_try:
            if check_port_available(self.host, port):
                bound_port = port
                break
        
        if bound_port is None:
            ports_str = ', '.join(str(p) for p in ports_to_try)
            raise RuntimeError(
                f"Could not bind to any port in range: {ports_str}. "
                f"All ports are in use on {self.host}"
            )
        
        self.actual_port = bound_port
        
        # Create HTTP server
        try:
            self.httpd = HTTPServer((self.host, self.actual_port), MetricsHTTPHandler)
        except OSError as e:
            raise RuntimeError(f"Failed to create HTTP server on {self.host}:{self.actual_port}: {e}")
        
        # Start server in daemon thread
        self.running = True
        self.thread = threading.Thread(
            target=self._run_server,
            name="crashlens-metrics-http-server",
            daemon=True
        )
        self.thread.start()
        
        # Build server URL
        server_url = f"http://{self.host}:{self.actual_port}"
        
        # Print security audit banner to stderr
        self._print_audit_banner(server_url)
        
        return server_url
    
    def _run_server(self):
        """Run HTTP server (called in background thread)"""
        try:
            _http_logger.info(f"HTTP metrics server started on {self.host}:{self.actual_port}")
            if self.httpd is not None:
                while self.running:
                    # Handle one request with timeout
                    self.httpd.timeout = 0.5  # Check running flag every 500ms
                    self.httpd.handle_request()
            if self.httpd is not None:
                while self.running:
                    # Handle one request with timeout
                    self.httpd.timeout = 0.5  # Check running flag every 500ms
                    self.httpd.handle_request()
        except Exception as e:
            if self.running:  # Only log if not deliberately stopped
                _http_logger.error(f"HTTP server error: {e}")
        finally:
            _http_logger.info("HTTP metrics server stopped")
    
    def stop(self):
        """
        Gracefully shutdown HTTP server.
        
        Process:
        1. Set running flag to False
        2. Close server socket
        3. Wait for thread to finish (with timeout)
        """
        if not self.running:
            return
        
        self.running = False
        
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception as e:
                _http_logger.warning(f"Error closing HTTP server: {e}")
        
        if self.thread and self.thread.is_alive():
            # Wait up to 2 seconds for thread to finish
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                _http_logger.warning("HTTP server thread did not stop cleanly")
    
    def _print_audit_banner(self, server_url: str):
        """
        Print security audit banner to stderr.
        
        Args:
            server_url: Full server URL (e.g., 'http://127.0.0.1:9090')
        """
        is_localhost = self.host in ('127.0.0.1', 'localhost', '::1')
        auth_status = "✓ Basic auth enabled" if MetricsHTTPHandler.auth_required else "⚠️  No authentication"
        binding_warning = "" if is_localhost else "\n   ⚠️  WARNING: Exposed on network - ensure firewall is configured"
        
        is_localhost = self.host in ('127.0.0.1', 'localhost', '::1')
        auth_status = "✓ Basic auth enabled" if MetricsHTTPHandler.auth_required else "⚠️  No authentication"
        binding_warning = "" if is_localhost else "\n   ⚠️  WARNING: Exposed on network - ensure firewall is configured"
        
        banner = f"""
⚠️  WARNING: Metrics HTTP server enabled
   Endpoint: {server_url}/metrics
   Health check: {server_url}/health
   Authentication: {auth_status}
   Binding: {self.host}:{self.actual_port} {'(localhost-only)' if is_localhost else '(network-accessible)'}{binding_warning}
   Authentication: {auth_status}
   Binding: {self.host}:{self.actual_port} {'(localhost-only)' if is_localhost else '(network-accessible)'}{binding_warning}
   To disable: Remove --metrics-http flag or unset CRASHLENS_ALLOW_HTTP_METRICS
"""
        # Print to stderr so it doesn't interfere with stdout
        print(banner, file=sys.stderr, flush=True)
