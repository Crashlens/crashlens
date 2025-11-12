"""Parsers package for CrashLens.

Supports multiple log formats via schema registry:
- langfuse-v1 (stable)
- langfuse-v2 (future)
- openai-v1 (future)
- anthropic-v1 (future)
- helicone-v1 (future)
"""

from .langfuse import LangfuseParser
from .registry import (
    get_parser,
    list_supported_formats,
    auto_detect_schema,
    register_custom_parser,
)

__all__ = [
    "LangfuseParser",
    "get_parser",
    "list_supported_formats",
    "auto_detect_schema",
    "register_custom_parser",
]
