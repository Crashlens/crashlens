"""
Feature flags for CrashLens unified engine migration.

This module provides helpers to check feature flags that control
the gradual rollout of the unified guard/policy-check engine.
"""

import os
from typing import Optional


def is_unified_enabled() -> bool:
    """Check if the unified engine is enabled.
    
    Returns:
        True if CRASHLENS_USE_UNIFIED_ENGINE is set to '1', False otherwise.
    
    Examples:
        >>> os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        >>> is_unified_enabled()
        True
        >>> os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '0'
        >>> is_unified_enabled()
        False
    """
    return os.getenv('CRASHLENS_USE_UNIFIED_ENGINE', '0') == '1'


def get_unified_flag_value() -> str:
    """Get the raw value of the unified engine flag.
    
    Returns:
        The value of CRASHLENS_USE_UNIFIED_ENGINE env var, or '0' if not set.
    """
    return os.getenv('CRASHLENS_USE_UNIFIED_ENGINE', '0')


def set_unified_enabled(enabled: bool) -> None:
    """Set the unified engine flag (for testing purposes).
    
    Args:
        enabled: Whether to enable the unified engine.
    
    Warning:
        This modifies os.environ and should only be used in tests.
    """
    os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '1' if enabled else '0'
