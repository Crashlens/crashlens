"""
Variable resolution for .crashlens/config.yaml fallback.

This module provides fallback resolution for variables ($VAR or ${VAR}) used in
guard policy files. Variables are resolved in the following order:
1. Environment variables (os.getenv)
2. Config file's env mapping (.crashlens/config.yaml → env.VAR)
3. Top-level config keys (.crashlens/config.yaml → VAR)

If required=True and a variable is not found, raises KeyError.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# Module-level cache
_CONFIG: Optional[Dict[str, Any]] = None


def load_config() -> Dict[str, Any]:
    """
    Load .crashlens/config.yaml from current directory.
    
    Returns empty dict if file doesn't exist. Caches result in module-level _CONFIG.
    
    Returns:
        Dict with config data (may be empty)
    """
    global _CONFIG
    
    if _CONFIG is not None:
        return _CONFIG  # Already loaded and cached
    
    # Look for .crashlens/config.yaml or .crashlens/config.yml
    config_dir = Path.cwd() / ".crashlens"
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        config_file = config_dir / "config.yml"
    
    if not config_file.exists():
        _CONFIG = {}
        return _CONFIG
    
    with open(config_file, 'r', encoding='utf-8') as f:
        _CONFIG = yaml.safe_load(f) or {}
    
    return _CONFIG


def resolve_variables_in_obj(obj: Any, required: bool = False) -> Any:
    """
    Recursively resolve $VAR or ${VAR} in strings, dicts, and lists.
    
    Resolution order:
    1. os.getenv(VAR)
    2. config['env'][VAR]  (from .crashlens/config.yaml)
    3. config[VAR]         (top-level key in .crashlens/config.yaml)
    
    If required=True and variable not found, raises KeyError.
    If required=False and variable not found, returns original string.
    
    Args:
        obj: Any Python object (string, dict, list, or primitive)
        required: If True, raise KeyError for missing variables
        
    Returns:
        Object with variables resolved
        
    Raises:
        KeyError: If required=True and variable not found
    """
    if isinstance(obj, dict):
        return {k: resolve_variables_in_obj(v, required=required) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_variables_in_obj(item, required=required) for item in obj]
    elif isinstance(obj, str):
        return _resolve_string(obj, required=required)
    else:
        # Non-string primitives pass through unchanged
        return obj


def _resolve_string(s: str, required: bool = False) -> str:
    """
    Resolve $VAR or ${VAR} patterns in a string.
    
    Args:
        s: Input string potentially containing variables
        required: If True, raise KeyError for missing variables
        
    Returns:
        String with variables resolved
        
    Raises:
        KeyError: If required=True and variable not found
    """
    # Regex pattern: $VAR or ${VAR}
    pattern = re.compile(r'\$(\w+)|\$\{(\w+)\}')
    
    def replacer(match):
        # Group 1 is $VAR, Group 2 is ${VAR}
        var_name = match.group(1) or match.group(2)
        
        # Resolution order: env → config.env → config top-level
        value = os.getenv(var_name)
        if value is not None:
            return value
        
        config = load_config()
        
        # Check config.env mapping
        if 'env' in config and var_name in config['env']:
            value = config['env'][var_name]
            # Convert to string for substitution
            return str(value)
        
        # Check top-level config key
        if var_name in config:
            value = config[var_name]
            return str(value)
        
        # Variable not found
        if required:
            raise KeyError(f"Missing variable: {var_name}")
        
        # Not required - return original
        return match.group(0)
    
    return pattern.sub(replacer, s)
