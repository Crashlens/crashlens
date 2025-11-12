"""
Schema versioning and parser registry for CrashLens.

Supports multiple log formats and versions:
- langfuse-v1: Original Langfuse JSONL format
- langfuse-v2: Enhanced Langfuse format (future)
- openai-v1: OpenAI API response logs
- anthropic-v1: Anthropic Claude API logs
- helicone-v1: Helicone proxy logs

Usage:
    from crashlens.parsers.registry import get_parser, list_supported_formats
    
    # Get parser for specific format
    parser = get_parser("langfuse-v1", verbose=True)
    traces = parser.parse_file(Path("logs.jsonl"))
    
    # Auto-detect format (experimental)
    parser = get_parser("auto", sample_lines=10)
    
    # List all supported formats
    formats = list_supported_formats()
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Callable
import logging

from .langfuse import LangfuseParser

logger = logging.getLogger(__name__)


# Type alias for parser classes
ParserClass = Type[Any]


class SchemaRegistry:
    """
    Registry for log parsers supporting multiple schema versions.
    
    Features:
    - Version-specific parser selection
    - Auto-detection of schema format (experimental)
    - Backwards compatibility warnings
    - Future schema migration support
    """
    
    def __init__(self):
        """Initialize schema registry with supported formats."""
        self._parsers: Dict[str, Dict[str, Any]] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self) -> None:
        """Register built-in parsers."""
        # Langfuse v1 (current stable)
        self.register(
            schema_id="langfuse-v1",
            parser_class=LangfuseParser,
            description="Original Langfuse JSONL format",
            version="1.0.0",
            stable=True,
            default_kwargs={"default_schema": "v1"}
        )
        
        # Langfuse v2 (future - placeholder)
        self.register(
            schema_id="langfuse-v2",
            parser_class=LangfuseParser,  # Will be replaced with LangfuseV2Parser
            description="Enhanced Langfuse format with extended metadata",
            version="2.0.0",
            stable=False,
            default_kwargs={"default_schema": "v2"}
        )
        
        # OpenAI v1 (future)
        self.register(
            schema_id="openai-v1",
            parser_class=LangfuseParser,  # Placeholder - needs OpenAIParser
            description="OpenAI API response logs",
            version="1.0.0",
            stable=False,
            default_kwargs={"default_schema": "openai"}
        )
        
        # Anthropic v1 (future)
        self.register(
            schema_id="anthropic-v1",
            parser_class=LangfuseParser,  # Placeholder - needs AnthropicParser
            description="Anthropic Claude API logs",
            version="1.0.0",
            stable=False,
            default_kwargs={"default_schema": "anthropic"}
        )
        
        # Helicone v1 (future)
        self.register(
            schema_id="helicone-v1",
            parser_class=LangfuseParser,  # Placeholder - needs HeliconeParser
            description="Helicone proxy logs",
            version="1.0.0",
            stable=False,
            default_kwargs={"default_schema": "helicone"}
        )
    
    def register(
        self,
        schema_id: str,
        parser_class: ParserClass,
        description: str,
        version: str,
        stable: bool = True,
        default_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a parser for a specific schema version.
        
        Args:
            schema_id: Unique identifier (e.g., "langfuse-v1")
            parser_class: Parser class to instantiate
            description: Human-readable description
            version: Schema version string
            stable: Whether this schema is production-ready
            default_kwargs: Default kwargs for parser instantiation
        """
        self._parsers[schema_id] = {
            "parser_class": parser_class,
            "description": description,
            "version": version,
            "stable": stable,
            "default_kwargs": default_kwargs or {},
        }
        
        logger.debug(f"Registered parser: {schema_id} (v{version}, stable={stable})")
    
    def get_parser(
        self,
        schema_id: str,
        **kwargs: Any
    ) -> Any:
        """
        Get parser instance for specified schema.
        
        Args:
            schema_id: Schema identifier (e.g., "langfuse-v1")
            **kwargs: Additional kwargs passed to parser constructor
        
        Returns:
            Instantiated parser
        
        Raises:
            ValueError: If schema_id not registered
        """
        if schema_id == "auto":
            # Auto-detection (future feature)
            logger.warning(
                "Auto-detection not yet implemented. Defaulting to langfuse-v1."
            )
            schema_id = "langfuse-v1"
        
        if schema_id not in self._parsers:
            supported = ", ".join(self._parsers.keys())
            raise ValueError(
                f"Unknown schema '{schema_id}'. Supported: {supported}"
            )
        
        parser_info = self._parsers[schema_id]
        
        # Warn if using unstable schema
        if not parser_info["stable"]:
            logger.warning(
                f"Schema '{schema_id}' is experimental and may change in future versions."
            )
        
        # Merge default kwargs with user kwargs
        final_kwargs = {**parser_info["default_kwargs"], **kwargs}
        
        # Instantiate parser
        parser_class = parser_info["parser_class"]
        return parser_class(**final_kwargs)
    
    def list_formats(self, stable_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all registered schema formats.
        
        Args:
            stable_only: Only return stable/production-ready schemas
        
        Returns:
            List of schema metadata dicts
        """
        formats = []
        for schema_id, info in self._parsers.items():
            if stable_only and not info["stable"]:
                continue
            
            formats.append({
                "schema_id": schema_id,
                "description": info["description"],
                "version": info["version"],
                "stable": info["stable"],
            })
        
        return formats
    
    def auto_detect_schema(
        self,
        sample_lines: List[str],
        top_n: int = 3
    ) -> List[str]:
        """
        Attempt to auto-detect schema format from sample lines.
        
        Args:
            sample_lines: Sample JSONL lines to analyze
            top_n: Return top N best matches
        
        Returns:
            List of schema_ids ranked by confidence
        
        Note:
            This is an experimental feature. Heuristics may not be 100% accurate.
        """
        import json
        
        scores: Dict[str, int] = {schema_id: 0 for schema_id in self._parsers}
        
        for line in sample_lines[:10]:  # Analyze first 10 lines
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            # Heuristic: Check for schema-specific fields
            if "traceId" in record:
                scores["langfuse-v1"] += 2
                scores["langfuse-v2"] += 2
            
            if "choices" in record and "model" in record:
                scores["openai-v1"] += 3
            
            if "completion" in record and "model" in record:
                scores["anthropic-v1"] += 3
            
            if "response" in record and "helicone" in str(record).lower():
                scores["helicone-v1"] += 3
        
        # Sort by score (descending)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top N with non-zero scores
        return [schema_id for schema_id, score in ranked[:top_n] if score > 0]


# Global registry instance
_registry = SchemaRegistry()


def get_parser(schema_id: str = "langfuse-v1", **kwargs: Any) -> Any:
    """
    Get parser for specified schema format.
    
    Args:
        schema_id: Schema identifier (default: "langfuse-v1")
        **kwargs: Additional kwargs for parser constructor
    
    Returns:
        Instantiated parser
    
    Examples:
        >>> parser = get_parser("langfuse-v1", verbose=True)
        >>> traces = parser.parse_file(Path("logs.jsonl"))
        
        >>> parser = get_parser("openai-v1", fail_fast=True)
    """
    return _registry.get_parser(schema_id, **kwargs)


def list_supported_formats(stable_only: bool = False) -> List[Dict[str, Any]]:
    """
    List all supported log formats.
    
    Args:
        stable_only: Only return stable/production-ready formats
    
    Returns:
        List of format metadata dicts
    
    Examples:
        >>> formats = list_supported_formats(stable_only=True)
        >>> for fmt in formats:
        ...     print(f"{fmt['schema_id']}: {fmt['description']}")
    """
    return _registry.list_formats(stable_only=stable_only)


def auto_detect_schema(file_path: Path, sample_size: int = 10) -> Optional[str]:
    """
    Auto-detect schema format from file.
    
    Args:
        file_path: Path to JSONL file
        sample_size: Number of lines to sample
    
    Returns:
        Best-match schema_id or None if detection fails
    
    Examples:
        >>> schema_id = auto_detect_schema(Path("logs.jsonl"))
        >>> parser = get_parser(schema_id)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_lines = [f.readline() for _ in range(sample_size)]
        
        detected = _registry.auto_detect_schema(sample_lines)
        return detected[0] if detected else None
    
    except Exception as e:
        logger.error(f"Auto-detection failed: {e}")
        return None


def register_custom_parser(
    schema_id: str,
    parser_class: ParserClass,
    description: str,
    version: str = "1.0.0",
    stable: bool = False,
    **default_kwargs: Any
) -> None:
    """
    Register a custom parser (for external plugins).
    
    Args:
        schema_id: Unique identifier for your format
        parser_class: Your parser class
        description: Human-readable description
        version: Schema version
        stable: Whether production-ready
        **default_kwargs: Default constructor arguments
    
    Examples:
        >>> from myproject.parsers import MyCustomParser
        >>> register_custom_parser(
        ...     schema_id="custom-v1",
        ...     parser_class=MyCustomParser,
        ...     description="My custom log format",
        ...     verbose=True
        ... )
    """
    _registry.register(
        schema_id=schema_id,
        parser_class=parser_class,
        description=description,
        version=version,
        stable=stable,
        default_kwargs=default_kwargs
    )
