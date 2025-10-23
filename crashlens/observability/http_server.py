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
import threading
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Any
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
    - GET /metrics -> Return Prometheus metrics
    - GET /health -> Return 200 OK
    - All other requests -> 404
    """
    
    # Class variable to hold metrics registry
    registry = None
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        _http_logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/metrics':
                self._handle_metrics()
            elif self.path == '/health':
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
    
    Example:
        >>> server = MetricsHTTPServer(metrics, '127.0.0.1', 9090)
        >>> url = server.start()
        ⚠️  WARNING: Metrics HTTP server enabled
           Endpoint: http://127.0.0.1:9090/metrics
           Security: Ensure this is not exposed to the internet
           To disable: Remove --metrics-http flag
        >>> # ... do work ...
        >>> server.stop()
    """
    
    def __init__(self, metrics: Any, host: str = '127.0.0.1', port: int = 9090):
        """
        Initialize HTTP server for metrics.
        
        Args:
            metrics: CrashLensMetrics instance (for registry access)
            host: IP address to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 9090)
        """
        self.metrics = metrics
        self.host = host
        self.port = port
        self.httpd: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.actual_port: Optional[int] = None
        
        # Set registry for handler
        if hasattr(metrics, 'registry'):
            MetricsHTTPHandler.registry = metrics.registry
        else:
            MetricsHTTPHandler.registry = None
    
    def start(self) -> str:
        """
        Start HTTP server in background thread.
        
        Returns:
            Server URL (e.g., 'http://127.0.0.1:9090')
        
        Raises:
            RuntimeError: If server cannot bind to any port
        
        Process:
        1. Check if port is available
        2. If not, try port+1, port+2
        3. If all fail, raise RuntimeError
        4. Start server in daemon thread
        5. Print security audit banner to stderr
        6. Return server URL
        """
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
        banner = f"""
⚠️  WARNING: Metrics HTTP server enabled
   Endpoint: {server_url}/metrics
   Health check: {server_url}/health
   Security: Ensure this is not exposed to the internet
   To disable: Remove --metrics-http flag or unset CRASHLENS_ALLOW_HTTP_METRICS
"""
        # Print to stderr so it doesn't interfere with stdout
        print(banner, file=sys.stderr, flush=True)
