"""
Policy enforcement engine for CrashLens.

Provides YAML-based rule definition and evaluation for log entries.
"""

from .engine import (
    PolicyEngine,
    PolicyRule, 
    PolicyMatcher,
    PolicyViolation,
    PolicyAction,
    PolicySeverity
)

__all__ = [
    'PolicyEngine',
    'PolicyRule',
    'PolicyMatcher', 
    'PolicyViolation',
    'PolicyAction',
    'PolicySeverity'
]
