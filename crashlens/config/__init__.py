"""
CrashLens Configuration Module

This module provides configuration management for CrashLens metrics and policies.

Main Components:
- metrics_config.py: Pydantic models for metrics configuration
- loader.py: Config file loading and validation

Usage:
    ```python
    from crashlens.config import load_metrics_config, MetricsConfig
    
    # Load config from standard locations
    config = load_metrics_config()
    
    # Or load from specific path
    config = load_metrics_config(Path("./my-config.yaml"))
    
    # Access config values
    if config.enabled:
        print(f"Sampling rate: {config.sampling.rate}")
    ```
"""

from .metrics_config import (
    MetricsConfig,
    SamplingConfig,
    PushgatewayConfig,
    HttpServerConfig,
)
from .loader import (
    load_metrics_config,
    find_config_file,
    validate_config_file,
    get_config_summary,
)

__all__ = [
    # Config models
    "MetricsConfig",
    "SamplingConfig",
    "PushgatewayConfig",
    "HttpServerConfig",
    # Loader functions
    "load_metrics_config",
    "find_config_file",
    "validate_config_file",
    "get_config_summary",
]
