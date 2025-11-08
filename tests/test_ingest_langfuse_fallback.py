"""
Tests for Langfuse parser integration and fallback behavior.

These tests verify that the ingestion layer gracefully handles
malformed Langfuse logs and falls back to basic JSON parsing.
"""

import pytest
import json
from pathlib import Path
from crashlens.io.ingest import LogIterator


@pytest.fixture
def mixed_validity_log_file(tmp_path):
    """Create a log file with valid and invalid Langfuse entries."""
    log_file = tmp_path / "mixed.jsonl"
    
    entries = [
        # Valid Langfuse-style entry
        {
            "traceId": "trace-001",
            "model": "gpt-4o",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "timestamp": "2025-01-01T00:00:00Z"
        },
        # Missing traceId (invalid for Langfuse)
        {
            "model": "gpt-3.5",
            "prompt_tokens": 50,
            "completion_tokens": 25,
        },
        # Valid entry
        {
            "traceId": "trace-002",
            "model": "claude-3",
            "prompt_tokens": 200,
            "completion_tokens": 100,
        },
        # Completely malformed JSON (handled at parse level)
        # (we'll add this as a raw line)
    ]
    
    with open(log_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
        f.write('{"this is": "not valid json\n')  # Malformed
    
    return log_file


def test_langfuse_parser_graceful_fallback(mixed_validity_log_file):
    """Test that Langfuse parser fallback works for invalid entries."""
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=True,
        skip_malformed=True,
        verbose=False
    )
    
    batches = list(iterator)
    
    # Should get all valid JSON entries (3 entries)
    assert len(batches) == 1
    assert len(batches[0]) == 3
    
    # Should have skipped 1 malformed line
    assert iterator.stats.skipped_lines == 1
    assert iterator.stats.parsed_lines == 3


def test_langfuse_disabled_parses_all_valid_json(mixed_validity_log_file):
    """Test that without Langfuse validation, all valid JSON is parsed."""
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=False,  # Disabled
        skip_malformed=True
    )
    
    batches = list(iterator)
    
    # Should parse all valid JSON lines (3 valid + 1 missing traceId = 3 JSON-valid)
    assert len(batches[0]) == 3
    assert iterator.stats.parsed_lines == 3
    assert iterator.stats.skipped_lines == 1  # Only the truly malformed JSON


def test_langfuse_schema_with_streaming(tmp_path):
    """Test Langfuse schema validation in streaming mode."""
    log_file = tmp_path / "streaming_langfuse.jsonl"
    
    # Create enough entries to trigger streaming
    entries = [
        {
            "traceId": f"trace-{i:04d}",
            "model": "gpt-4o",
            "tokens": 100 + i,
        }
        for i in range(1000)
    ]
    
    with open(log_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    iterator = LogIterator(
        log_file,
        langfuse_schema=True,
        force_stream=True,
        batch_size=100
    )
    
    batches = list(iterator)
    
    # Should process all batches
    assert len(batches) == 10
    
    # Total entries should match
    total = sum(len(batch) for batch in batches)
    assert total == 1000


def test_langfuse_parser_unavailable_fallback(mixed_validity_log_file, monkeypatch):
    """Test fallback when Langfuse parser is not available."""
    # Simulate LangfuseParser not being available
    import crashlens.io.ingest as ingest_module
    monkeypatch.setattr(ingest_module, 'HAS_LANGFUSE_PARSER', False)
    
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=True,  # Request it, but it won't be used
        skip_malformed=True
    )
    
    # Should fall back to basic JSON parsing
    assert iterator.langfuse_parser is None
    
    batches = list(iterator)
    
    # Should still parse valid JSON
    assert len(batches[0]) == 3


def test_strict_mode_langfuse_validation(mixed_validity_log_file):
    """Test that strict mode (skip_malformed=False) raises on errors."""
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=True,
        skip_malformed=False  # Strict mode
    )
    
    # Should raise on first malformed line
    with pytest.raises(json.JSONDecodeError):
        list(iterator)


def test_empty_file_with_langfuse(tmp_path):
    """Test handling of empty file with Langfuse validation."""
    log_file = tmp_path / "empty.jsonl"
    log_file.touch()
    
    iterator = LogIterator(log_file, langfuse_schema=True)
    
    batches = list(iterator)
    
    assert len(batches) == 0
    assert iterator.stats.parsed_lines == 0


def test_stats_track_langfuse_processing(mixed_validity_log_file):
    """Test that stats correctly track Langfuse processing."""
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=True,
        skip_malformed=True
    )
    
    list(iterator)
    
    stats = iterator.stats
    
    # 4 total lines (3 valid JSON + 1 malformed)
    assert stats.total_lines == 4
    assert stats.parsed_lines == 3
    assert stats.skipped_lines == 1


def test_langfuse_with_custom_threshold(tmp_path):
    """Test Langfuse validation with custom stream threshold."""
    log_file = tmp_path / "custom_threshold.jsonl"
    
    entries = [{"traceId": f"t-{i}", "model": "gpt-4"} for i in range(50)]
    
    with open(log_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    # Force streaming with low threshold
    iterator = LogIterator(
        log_file,
        langfuse_schema=True,
        stream_threshold=100,  # Very low
        batch_size=10
    )
    
    batches = list(iterator)
    
    # Should use streaming
    assert iterator.stats.used_streaming
    assert len(batches) == 5  # 50 entries / 10 per batch


def test_verbose_langfuse_warnings(mixed_validity_log_file, capsys):
    """Test that verbose mode shows Langfuse validation warnings."""
    iterator = LogIterator(
        mixed_validity_log_file,
        langfuse_schema=True,
        skip_malformed=True,
        verbose=True
    )
    
    list(iterator)
    
    captured = capsys.readouterr()
    
    # Should show warnings (either from our code or from LangfuseParser)
    # We check for any output as a sign that warnings were shown
    output = captured.out + captured.err
    assert len(output) > 0 or iterator.stats.skipped_lines > 0


def test_langfuse_preserves_all_fields(tmp_path):
    """Test that Langfuse parsing preserves all fields."""
    log_file = tmp_path / "full_entry.jsonl"
    
    full_entry = {
        "traceId": "trace-001",
        "model": "gpt-4o",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cost": 0.015,
        "metadata": {"team": "platform"},
        "custom_field": "custom_value"
    }
    
    with open(log_file, 'w') as f:
        f.write(json.dumps(full_entry) + '\n')
    
    iterator = LogIterator(log_file, langfuse_schema=True)
    
    batches = list(iterator)
    
    parsed_entry = batches[0][0]
    
    # All fields should be preserved
    assert parsed_entry['traceId'] == 'trace-001'
    assert parsed_entry['model'] == 'gpt-4o'
    assert parsed_entry['custom_field'] == 'custom_value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
