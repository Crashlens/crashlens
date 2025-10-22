"""
Prometheus Pushgateway Integration for CrashLens

This module implements fire-and-forget metric pushing to Prometheus Pushgateway
with these characteristics:
- Non-blocking: Uses daemon threads to prevent CLI hang
- Timeout protection: Maximum 2-second wait before abandoning push
- Graceful degradation: Failed pushes logged but don't crash the CLI
- URL validation: Validates pushgateway URL format
- Rotating logs: Tracks push failures for debugging (max 2MB total)

Design validated in Phase 0 Task 3: Fire-and-forget push tests passed
with 0.00s blocking time even with dead endpoints.
"""

import os
import logging
import threading
import time
from typing import Optional
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Push configuration constants
DEFAULT_PUSHGATEWAY_URL = "http://localhost:9091"
DEFAULT_JOB_NAME = "crashlens"
PUSH_TIMEOUT_SECONDS = 5.0
MAX_WAIT_SECONDS = 2.0

# Rotating log configuration
LOG_DIR = Path("/tmp") if os.name != "nt" else Path(os.environ.get("TEMP", "C:\\Temp"))
LOG_FILE = LOG_DIR / "crashlens-metrics.log"
MAX_LOG_SIZE = 1_000_000  # 1MB
BACKUP_COUNT = 1  # Total: 2MB (1MB current + 1MB backup)

# Set up rotating file handler for metrics push failures
_metrics_logger = logging.getLogger("crashlens.observability.push")
_metrics_logger.setLevel(logging.INFO)

# Only add handler if not already present
if not _metrics_logger.handlers:
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        _metrics_logger.addHandler(handler)
    except Exception as e:
        # If we can't set up file logging, fall back to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        _metrics_logger.addHandler(console_handler)
        _metrics_logger.warning(f"Could not set up rotating log file: {e}")


def validate_pushgateway_url(url: str) -> str:
    """
    Validate and normalize pushgateway URL.
    
    Args:
        url: Pushgateway URL to validate
        
    Returns:
        Normalized URL string
        
    Raises:
        ValueError: If URL is invalid (missing scheme, netloc, or wrong scheme)
        
    Example:
        >>> validate_pushgateway_url("http://localhost:9091")
        'http://localhost:9091'
        >>> validate_pushgateway_url("https://prometheus:9091")
        'https://prometheus:9091'
        >>> validate_pushgateway_url("localhost")
        Traceback (most recent call last):
        ValueError: Invalid URL 'localhost': missing scheme (http/https)
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
        
        # Validate scheme
        if not parsed.scheme:
            raise ValueError(f"Invalid URL '{url}': missing scheme (http/https)")
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}': must be http or https")
        
        # Validate netloc (host:port)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL '{url}': missing host")
        
        # Return the original URL (already normalized by urlparse)
        return url
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse URL '{url}': {e}") from e


def push_metrics_async(
    gateway_url: str = DEFAULT_PUSHGATEWAY_URL,
    job_name: str = DEFAULT_JOB_NAME,
    registry=None,
    timeout: float = PUSH_TIMEOUT_SECONDS,
    max_wait: float = MAX_WAIT_SECONDS,
    metrics_instance: Optional['CrashLensMetrics'] = None
) -> None:
    """
    Push metrics to Pushgateway in fire-and-forget mode.
    
    This function spawns a daemon thread to push metrics and returns immediately
    after max_wait seconds. The CLI will not wait for the push to complete.
    
    Args:
        gateway_url: URL of the Pushgateway (e.g., http://localhost:9091)
        job_name: Job name for grouping metrics in Pushgateway
        registry: Prometheus registry (defaults to REGISTRY if None)
        timeout: Maximum seconds for the push request itself
        max_wait: Maximum seconds to wait for thread (CLI blocking time)
        metrics_instance: CrashLensMetrics instance (for status updates)
        
    Note:
        This function returns after max_wait seconds regardless of push status.
        The push continues in a background daemon thread if not complete.
        
    Example:
        >>> push_metrics_async("http://localhost:9091", "crashlens")
        # Returns immediately (within max_wait seconds)
        # Push happens in background
    """
    # Validate URL before spawning thread
    try:
        normalized_url = validate_pushgateway_url(gateway_url)
    except ValueError as e:
        _metrics_logger.error(f"Invalid pushgateway URL: {e}")
        if metrics_instance:
            metrics_instance.update_push_status(False)
        return
    
    def _push_worker():
        """Worker function that runs in daemon thread."""
        start_time = time.time()
        
        try:
            # Lazy import prometheus_client only if needed
            try:
                from prometheus_client import push_to_gateway, REGISTRY as DEFAULT_REGISTRY
            except ImportError:
                _metrics_logger.error(
                    "prometheus_client not available. "
                    "Install with: pip install crashlens[metrics]"
                )
                if metrics_instance:
                    metrics_instance.update_push_status(False)
                return
            
            # Use provided registry or default
            target_registry = registry if registry is not None else DEFAULT_REGISTRY
            
            _metrics_logger.info(f"Pushing metrics to {normalized_url} (job={job_name}, timeout={timeout}s)")
            
            push_to_gateway(
                gateway=normalized_url,
                job=job_name,
                registry=target_registry,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            _metrics_logger.info(f"✓ Metrics pushed successfully in {elapsed:.2f}s")
            
            # Update push status metric
            if metrics_instance:
                metrics_instance.update_push_status(True)
                
        except Exception as e:
            elapsed = time.time() - start_time
            _metrics_logger.error(
                f"✗ Failed to push metrics to {normalized_url} after {elapsed:.2f}s: "
                f"{type(e).__name__}: {e}"
            )
            
            # Update push status metric
            if metrics_instance:
                metrics_instance.update_push_status(False)
    
    # Spawn daemon thread (won't block process exit)
    thread = threading.Thread(target=_push_worker, daemon=True, name="metrics-push")
    thread.start()
    
    # Wait maximum max_wait seconds (non-blocking for CLI)
    thread.join(timeout=max_wait)
    
    if thread.is_alive():
        _metrics_logger.debug(
            f"Push thread still running after {max_wait}s wait, "
            f"continuing in background (daemon)"
        )
    else:
        _metrics_logger.debug(f"Push thread completed within {max_wait}s")


def get_pushgateway_url_from_env() -> Optional[str]:
    """
    Get Pushgateway URL from environment variable.
    
    Returns:
        URL from CRASHLENS_PUSHGATEWAY_URL env var, or None if not set
        
    Example:
        >>> os.environ['CRASHLENS_PUSHGATEWAY_URL'] = 'http://localhost:9091'
        >>> get_pushgateway_url_from_env()
        'http://localhost:9091'
    """
    url = os.environ.get('CRASHLENS_PUSHGATEWAY_URL')
    if url:
        _metrics_logger.info(f"Using pushgateway URL from environment: {url}")
    return url


# Backward compatibility alias
push_metrics_fire_and_forget = push_metrics_async


__all__ = [
    'push_metrics_async',
    'push_metrics_fire_and_forget',
    'validate_pushgateway_url',
    'get_pushgateway_url_from_env',
    'DEFAULT_PUSHGATEWAY_URL',
    'DEFAULT_JOB_NAME',
]
