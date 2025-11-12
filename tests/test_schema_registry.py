"""
Tests for schema registry and parser versioning.
"""

import pytest
from pathlib import Path

from crashlens.parsers.registry import (
    SchemaRegistry,
    get_parser,
    list_supported_formats,
    auto_detect_schema,
    register_custom_parser,
)
from crashlens.parsers.langfuse import LangfuseParser


class TestSchemaRegistry:
    """Test SchemaRegistry class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.registry = SchemaRegistry()
    
    def test_default_parsers_registered(self):
        """Test that default parsers are registered."""
        formats = self.registry.list_formats()
        schema_ids = [f["schema_id"] for f in formats]
        
        assert "langfuse-v1" in schema_ids
        assert "langfuse-v2" in schema_ids
        assert "openai-v1" in schema_ids
        assert "anthropic-v1" in schema_ids
        assert "helicone-v1" in schema_ids
    
    def test_get_parser_langfuse_v1(self):
        """Test getting Langfuse v1 parser."""
        parser = self.registry.get_parser("langfuse-v1", verbose=False)
        
        assert parser is not None
        assert isinstance(parser, LangfuseParser)
    
    def test_get_parser_unknown_schema(self):
        """Test getting parser for unknown schema raises error."""
        with pytest.raises(ValueError, match="Unknown schema"):
            self.registry.get_parser("unknown-schema")
    
    def test_list_formats_stable_only(self):
        """Test listing only stable formats."""
        all_formats = self.registry.list_formats(stable_only=False)
        stable_formats = self.registry.list_formats(stable_only=True)
        
        assert len(stable_formats) <= len(all_formats)
        
        # Check all stable formats are marked as stable
        for fmt in stable_formats:
            assert fmt["stable"] is True
    
    def test_auto_detect_langfuse(self):
        """Test auto-detection for Langfuse format."""
        sample_lines = [
            '{"traceId": "abc123", "model": "gpt-4", "prompt_tokens": 100}',
            '{"traceId": "def456", "model": "gpt-3.5-turbo", "completion_tokens": 50}',
        ]
        
        detected = self.registry.auto_detect_schema(sample_lines)
        
        assert len(detected) > 0
        assert "langfuse-v1" in detected or "langfuse-v2" in detected
    
    def test_auto_detect_openai(self):
        """Test auto-detection for OpenAI format."""
        sample_lines = [
            '{"model": "gpt-4", "choices": [{"message": {"role": "assistant"}}]}',
            '{"model": "gpt-3.5-turbo", "choices": [{"text": "Hello"}]}',
        ]
        
        detected = self.registry.auto_detect_schema(sample_lines)
        
        assert len(detected) > 0
        assert "openai-v1" in detected
    
    def test_register_custom_parser(self):
        """Test registering custom parser."""
        # Create dummy parser class
        class CustomParser:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        
        self.registry.register(
            schema_id="custom-v1",
            parser_class=CustomParser,
            description="Custom test parser",
            version="1.0.0",
            stable=False,
            default_kwargs={"test_arg": "test_value"}
        )
        
        # Verify registration
        formats = self.registry.list_formats()
        schema_ids = [f["schema_id"] for f in formats]
        assert "custom-v1" in schema_ids
        
        # Get parser
        parser = self.registry.get_parser("custom-v1")
        assert isinstance(parser, CustomParser)
        assert parser.kwargs["test_arg"] == "test_value"


class TestModuleFunctions:
    """Test module-level convenience functions."""
    
    def test_get_parser_default(self):
        """Test get_parser with default arguments."""
        parser = get_parser()
        
        assert parser is not None
        assert isinstance(parser, LangfuseParser)
    
    def test_get_parser_with_kwargs(self):
        """Test get_parser passes kwargs to parser."""
        parser = get_parser("langfuse-v1", verbose=True, fail_fast=False)
        
        assert parser is not None
    
    def test_list_supported_formats(self):
        """Test listing supported formats."""
        formats = list_supported_formats()
        
        assert len(formats) > 0
        assert all("schema_id" in f for f in formats)
        assert all("description" in f for f in formats)
        assert all("version" in f for f in formats)
        assert all("stable" in f for f in formats)
    
    def test_auto_detect_schema_file(self, tmp_path):
        """Test auto-detecting schema from file."""
        # Create test file
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            '{"traceId": "abc123", "model": "gpt-4"}\n'
            '{"traceId": "def456", "model": "gpt-3.5-turbo"}\n'
        )
        
        schema_id = auto_detect_schema(log_file)
        
        assert schema_id is not None
        assert schema_id in ["langfuse-v1", "langfuse-v2"]
    
    def test_auto_detect_schema_nonexistent_file(self):
        """Test auto-detection with nonexistent file."""
        result = auto_detect_schema(Path("nonexistent.jsonl"))
        
        assert result is None
    
    def test_register_custom_parser_function(self):
        """Test register_custom_parser convenience function."""
        class MyParser:
            def __init__(self, **kwargs):
                pass
        
        register_custom_parser(
            schema_id="test-v1",
            parser_class=MyParser,
            description="Test parser",
            custom_arg="custom_value"
        )
        
        formats = list_supported_formats()
        schema_ids = [f["schema_id"] for f in formats]
        assert "test-v1" in schema_ids


class TestAutoDetection:
    """Test auto-detection heuristics."""
    
    def test_detect_empty_lines(self):
        """Test auto-detection with empty lines."""
        registry = SchemaRegistry()
        detected = registry.auto_detect_schema([])
        
        assert detected == []
    
    def test_detect_invalid_json(self):
        """Test auto-detection with invalid JSON."""
        registry = SchemaRegistry()
        sample_lines = [
            'not valid json',
            '{"incomplete":',
        ]
        
        detected = registry.auto_detect_schema(sample_lines)
        
        # Should not crash, just return empty or low-confidence results
        assert isinstance(detected, list)
    
    def test_detect_multiple_formats(self):
        """Test auto-detection returns top N matches."""
        registry = SchemaRegistry()
        sample_lines = [
            '{"traceId": "abc", "model": "gpt-4", "choices": []}',  # Ambiguous
        ]
        
        detected = registry.auto_detect_schema(sample_lines, top_n=3)
        
        assert len(detected) <= 3
    
    def test_detect_confidence_ranking(self):
        """Test that detection ranks by confidence."""
        registry = SchemaRegistry()
        
        # Strong Langfuse signals
        langfuse_lines = [
            '{"traceId": "abc123", "model": "gpt-4"}',
            '{"traceId": "def456", "startTime": "2025-01-25"}',
        ]
        
        detected = registry.auto_detect_schema(langfuse_lines, top_n=1)
        
        assert detected[0] in ["langfuse-v1", "langfuse-v2"]
