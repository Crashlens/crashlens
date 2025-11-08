"""
Feature flags for CrashLens (legacy module - kept for compatibility).

This module originally controlled the unified engine feature flag.
As of v1.0, the unified engine is always enabled.
"""

import os
from typing import Optional


def is_unified_enabled() -> bool:
    """Check if the unified engine is enabled.
    
    **Note:** As of v1.0, this function always returns True.
    The unified engine is the only execution path.
    
    Returns:
        True (always, in v1.0+)
    
    Examples:
        >>> is_unified_enabled()
        True
    """
    return True


# Legacy functions kept for backwards compatibility (deprecated)
def get_unified_flag_value() -> str:
    """Get the raw value of the unified engine flag.
    
    **Deprecated:** Always returns '1' in v1.0+
    
    Returns:
        '1' (always, unified engine is the only path)
    """
    return '1'


def set_unified_enabled(enabled: bool) -> None:
    """Set the unified engine flag (for testing purposes).
    
    **Deprecated:** No-op in v1.0+ (unified engine always enabled)
    
    Args:
        enabled: Ignored (unified engine always enabled)
    """
    pass  # No-op, unified engine always enabled
