"""
Configuration file loader for CrashLens metrics.

This module handles finding and loading metrics configuration from YAML files,
with support for multiple config locations and precedence rules.

Config File Locations (searched in order):
1. CLI flag: --metrics-config <path>
2. Environment variable: CRASHLENS_METRICS_CONFIG
3. Project directory: ./.crashlens/metrics.yaml
4. User home: ~/.crashlens/metrics.yaml
5. System directory: /etc/crashlens/metrics.yaml

Precedence (highest to lowest):
1. CLI flags (e.g., --push-metrics)
2. Environment variables (e.g., CRASHLENS_PUSH_METRICS)
3. Config file (e.g., metrics.yaml)
4. Defaults (defined in pydantic models)

Example:
    ```python
    from crashlens.config.loader import load_metrics_config
    
    # Automatic search
    config = load_metrics_config()
    
    # Explicit path
    config = load_metrics_config(Path("./my-config.yaml"))
    
    # Access config values
    if config.enabled:
        print(f"Sampling rate: {config.sampling.rate}")
    ```
"""

import os
import logging
from pathlib import Path
from typing import Optional
import yaml
from pydantic import ValidationError

from .metrics_config import MetricsConfig

logger = logging.getLogger(__name__)


def find_config_file() -> Optional[Path]:
    """
    Search for metrics config file in standard locations.
    
    Search order:
    1. Environment variable: CRASHLENS_METRICS_CONFIG
    2. Project directory: ./.crashlens/metrics.yaml
    3. User home: ~/.crashlens/metrics.yaml
    4. System directory: /etc/crashlens/metrics.yaml
    
    Returns:
        Path to config file if found, None otherwise
    
    Example:
        ```python
        config_path = find_config_file()
        if config_path:
            print(f"Found config at: {config_path}")
        else:
            print("No config file found, using defaults")
        ```
    """
    # Check environment variable first
    env_path = os.getenv("CRASHLENS_METRICS_CONFIG")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        if path.exists():
            logger.info(f"Found config file via CRASHLENS_METRICS_CONFIG: {path}")
            return path
        else:
            logger.warning(
                f"CRASHLENS_METRICS_CONFIG points to non-existent file: {path}"
            )
    
    # Define search locations
    search_locations = [
        Path("./.crashlens/metrics.yaml"),  # Project directory
        Path("~/.crashlens/metrics.yaml").expanduser(),  # User home
        Path("/etc/crashlens/metrics.yaml"),  # System (Unix-like only)
    ]
    
    # Search each location
    for location in search_locations:
        logger.debug(f"Checking for config file: {location}")
        if location.exists():
            logger.info(f"Found config file: {location}")
            return location
    
    # No config file found
    logger.debug(
        "No config file found in standard locations. "
        "Checked: CRASHLENS_METRICS_CONFIG env var, "
        "./.crashlens/metrics.yaml, ~/.crashlens/metrics.yaml, "
        "/etc/crashlens/metrics.yaml"
    )
    return None


def load_metrics_config(path: Optional[Path] = None) -> MetricsConfig:
    """
    Load metrics configuration from YAML file with validation.
    
    If no path is provided, searches standard locations using find_config_file().
    If no config file is found, returns default MetricsConfig.
    
    Args:
        path: Optional explicit path to config file. If provided, this path
              is used directly without searching standard locations.
    
    Returns:
        MetricsConfig instance with validated configuration
    
    Raises:
        FileNotFoundError: If explicit path is provided but file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ValidationError: If config values fail pydantic validation
        PermissionError: If file exists but cannot be read
    
    Example:
        ```python
        # Automatic search (recommended)
        config = load_metrics_config()
        
        # Explicit path
        config = load_metrics_config(Path("./custom-config.yaml"))
        
        # Use config
        if config.enabled:
            print(f"Metrics enabled with {config.sampling.rate * 100}% sampling")
        ```
    
    Error Examples:
        ```python
        # Invalid YAML
        try:
            config = load_metrics_config(Path("bad.yaml"))
        except yaml.YAMLError as e:
            print(f"Invalid YAML syntax: {e}")
        
        # Validation error
        try:
            config = load_metrics_config(Path("invalid.yaml"))
        except ValidationError as e:
            print(f"Configuration validation failed: {e}")
        ```
    """
    # If explicit path provided, use it
    if path is not None:
        config_path = path.resolve()
        logger.info(f"Loading config from explicit path: {config_path}")
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Hint: Check the path is correct and file exists."
            )
    else:
        # Search for config file
        config_path = find_config_file()
        
        # If no config found, use defaults
        if config_path is None:
            logger.info("No config file found, using default configuration")
            return MetricsConfig()
    
    # Load YAML file
    try:
        logger.info(f"Reading config file: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied reading config file: {config_path}\n"
            f"Hint: Check file permissions or run with appropriate privileges."
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Error reading config file {config_path}: {e}\n"
            f"Hint: Check file is readable and not corrupted."
        ) from e
    
    # Parse YAML
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        # Extract line number if available
        line_info = ""
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            line_info = f" at line {mark.line + 1}, column {mark.column + 1}"
        
        raise yaml.YAMLError(
            f"Invalid YAML syntax in {config_path}{line_info}:\n{e}\n"
            f"Hint: Check YAML indentation and syntax. "
            f"Use a YAML validator like yamllint."
        ) from e
    
    # Handle empty file
    if yaml_data is None:
        logger.warning(f"Config file is empty: {config_path}, using defaults")
        return MetricsConfig()
    
    # Extract metrics config (support both top-level and nested)
    if isinstance(yaml_data, dict):
        # Check if there's a 'metrics' key (nested config)
        if 'metrics' in yaml_data:
            config_dict = yaml_data['metrics']
        else:
            # Assume entire file is metrics config (flat config)
            config_dict = yaml_data
    else:
        raise ValueError(
            f"Config file must contain a dictionary, got {type(yaml_data).__name__}\n"
            f"File: {config_path}\n"
            f"Hint: YAML file should start with key-value pairs, not a list."
        )
    
    # Validate with pydantic
    try:
        config = MetricsConfig(**config_dict)
        logger.info(
            f"Config loaded successfully: "
            f"enabled={config.enabled}, "
            f"sampling_rate={config.sampling.rate}"
        )
        return config
    except ValidationError as e:
        # Format validation errors nicely
        error_messages = []
        for error in e.errors():
            field = ".".join(str(x) for x in error['loc'])
            msg = error['msg']
            error_messages.append(f"  • {field}: {msg}")
        
        raise ValidationError(
            f"Configuration validation failed in {config_path}:\n"
            + "\n".join(error_messages) + "\n"
            f"Hint: Check field names, types, and value ranges. "
            f"See examples/ directory for valid config examples.",
            e.errors()
        ) from e


def validate_config_file(path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate a config file without loading it into application.
    
    Useful for CLI validation command and pre-deployment checks.
    
    Args:
        path: Path to config file to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if config is valid, False otherwise
        - error_message: None if valid, error description if invalid
    
    Example:
        ```python
        is_valid, error = validate_config_file(Path("metrics.yaml"))
        if is_valid:
            print("✓ Config is valid")
        else:
            print(f"✗ Config is invalid: {error}")
        ```
    """
    try:
        # Try to load config
        config = load_metrics_config(path)
        
        # Additional validation checks
        warnings = []
        
        # Check if HTTP mode requires explicit opt-in
        if config.http_server and config.http_server.enabled:
            env_var = os.getenv('CRASHLENS_ALLOW_HTTP_METRICS', '').lower()
            if env_var != 'true':
                warnings.append(
                    "HTTP server mode requires CRASHLENS_ALLOW_HTTP_METRICS=true"
                )
        
        # Check for per-rule sampling without any rules
        if config.sampling.per_rule and len(config.sampling.per_rule) == 0:
            warnings.append(
                "per_rule sampling is empty dict (no rules configured)"
            )
        
        # Return warnings as info, not errors
        if warnings:
            return (True, f"Valid with warnings:\n" + "\n".join(f"  ⚠ {w}" for w in warnings))
        
        return (True, None)
        
    except FileNotFoundError as e:
        return (False, f"File not found: {e}")
    except yaml.YAMLError as e:
        return (False, f"YAML syntax error: {e}")
    except ValidationError as e:
        return (False, f"Validation error: {e}")
    except Exception as e:
        return (False, f"Unexpected error: {e}")


def get_config_summary(config: MetricsConfig) -> str:
    """
    Generate a human-readable summary of metrics configuration.
    
    Useful for logging and debugging.
    
    Args:
        config: MetricsConfig instance to summarize
    
    Returns:
        Multi-line string with config summary
    
    Example:
        ```python
        config = load_metrics_config()
        print(get_config_summary(config))
        # Output:
        # Metrics Configuration:
        #   Enabled: true
        #   Mode: push
        #   Global Sampling: 10.0%
        #   Per-Rule Overrides: 2 rules
        #   ...
        ```
    """
    lines = ["Metrics Configuration:"]
    lines.append(f"  Enabled: {config.enabled}")
    
    if not config.enabled:
        lines.append("  (All other settings ignored when disabled)")
        return "\n".join(lines)
    
    # Sampling info
    lines.append(f"  Global Sampling: {config.sampling.rate * 100:.1f}%")
    if config.sampling.per_rule:
        lines.append(f"  Per-Rule Overrides: {len(config.sampling.per_rule)} rules")
        for rule, rate in list(config.sampling.per_rule.items())[:5]:  # Show first 5
            lines.append(f"    • {rule}: {rate * 100:.1f}%")
        if len(config.sampling.per_rule) > 5:
            lines.append(f"    ... and {len(config.sampling.per_rule) - 5} more")
    
    # Pushgateway info
    if config.pushgateway:
        lines.append(f"  Pushgateway URL: {config.pushgateway.url}")
        lines.append(f"  Job Name: {config.pushgateway.job}")
    
    # HTTP server info
    if config.http_server and config.http_server.enabled:
        lines.append(f"  HTTP Server: {config.http_server.addr}:{config.http_server.port}")
    
    return "\n".join(lines)


__all__ = [
    "find_config_file",
    "load_metrics_config",
    "validate_config_file",
    "get_config_summary",
]
