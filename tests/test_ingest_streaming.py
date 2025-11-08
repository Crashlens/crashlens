"""
Tests for shared log ingestion layer.

These tests verify streaming, batching, and schema validation functionality.
"""

import pytest
import json
import os
from pathlib import Path
from crashlens.io.ingest import LogIterator, iterate_logs, IngestionStats


@pytest.fixture
def small_log_file(tmp_path):
    """Create a small JSONL file (< 10MB)."""
    log_file = tmp_path / "small.jsonl"
    entries = [
        {"id": i, "model": "gpt-4o", "tokens": 100 + i}
        for i in range(100)
    ]
    
    with open(log_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    return log_file


@pytest.fixture
def large_log_file(tmp_path):
    """Create a large JSONL file (> stream threshold)."""
    log_file = tmp_path / "large.jsonl"
    
    # Create a file that's definitely over 10MB
    # Each entry needs to be ~1000 bytes to get 15MB total with 15K entries
    entries_per_batch = 1000
    num_batches = 15
    
    with open(log_file, 'w') as f:
        for batch in range(num_batches):
            for i in range(entries_per_batch):
                entry = {
                    "id": batch * entries_per_batch + i,
                    "model": "gpt-4o",
                    "tokens": 100 + i,
                    "prompt": "x" * 1000,  # 1000 chars = ~1KB per entry -> 15MB total
                }
                f.write(json.dumps(entry) + '\n')
    
    return log_file


@pytest.fixture
def malformed_log_file(tmp_path):
    """Create a JSONL file with some malformed lines."""
    log_file = tmp_path / "malformed.jsonl"
    
    with open(log_file, 'w') as f:
        f.write(json.dumps({"id": 1, "model": "gpt-4o"}) + '\n')
        f.write('{"invalid": json syntax}\n')  # Malformed
        f.write(json.dumps({"id": 2, "model": "gpt-3.5"}) + '\n')
        f.write('not json at all\n')  # Malformed
        f.write(json.dumps({"id": 3, "model": "claude-3"}) + '\n')
        f.write('\n')  # Empty line
        f.write(json.dumps({"id": 4, "model": "gpt-4"}) + '\n')
    
    return log_file


def test_log_iterator_initialization():
    """Test LogIterator can be initialized."""
    iterator = LogIterator('test.jsonl')
    
    assert iterator.path == Path('test.jsonl')
    assert iterator.batch_size == 5000
    assert iterator.skip_malformed is True
    assert iterator.verbose is False


def test_small_file_no_streaming(small_log_file):
    """Test that small files don't use streaming mode."""
    iterator = LogIterator(small_log_file)
    
    batches = list(iterator)
    
    # Small file should return all entries in one batch
    assert len(batches) == 1
    assert len(batches[0]) == 100
    assert not iterator.stats.used_streaming
    assert iterator.stats.parsed_lines == 100
    assert iterator.stats.skipped_lines == 0
    assert iterator.stats.batches_processed == 1


def test_large_file_uses_streaming(large_log_file):
    """Test that large files automatically use streaming mode."""
    iterator = LogIterator(large_log_file)
    
    batches = list(iterator)
    
    # Should use streaming
    assert iterator.stats.used_streaming
    
    # Should have multiple batches
    assert len(batches) > 1
    
    # Total entries should match
    total_entries = sum(len(batch) for batch in batches)
    assert total_entries == 15000
    
    # Each batch (except possibly last) should be full size
    for batch in batches[:-1]:
        assert len(batch) == 5000


def test_force_streaming_on_small_file(small_log_file):
    """Test forcing streaming mode on small files."""
    iterator = LogIterator(small_log_file, force_stream=True, batch_size=10)
    
    batches = list(iterator)
    
    # Should use streaming even though file is small
    assert iterator.stats.used_streaming
    
    # Should have multiple small batches
    assert len(batches) == 10  # 100 entries / 10 per batch
    
    for batch in batches:
        assert len(batch) == 10


def test_custom_batch_size(small_log_file):
    """Test custom batch size."""
    iterator = LogIterator(small_log_file, force_stream=True, batch_size=25)
    
    batches = list(iterator)
    
    assert len(batches) == 4  # 100 / 25
    
    for batch in batches:
        assert len(batch) == 25


def test_malformed_lines_skipped(malformed_log_file):
    """Test that malformed lines are skipped gracefully."""
    iterator = LogIterator(malformed_log_file, skip_malformed=True, verbose=False)
    
    batches = list(iterator)
    
    # Should get valid entries
    assert len(batches) == 1
    valid_entries = batches[0]
    
    # Should have 4 valid entries (IDs 1, 2, 3, 4)
    assert len(valid_entries) == 4
    assert iterator.stats.skipped_lines == 2  # Two malformed lines
    assert iterator.stats.parsed_lines == 4


def test_malformed_lines_raise_when_not_skipped(malformed_log_file):
    """Test that malformed lines raise when skip_malformed=False."""
    iterator = LogIterator(malformed_log_file, skip_malformed=False)
    
    with pytest.raises(json.JSONDecodeError):
        list(iterator)


def test_env_var_stream_threshold(small_log_file, monkeypatch):
    """Test CRASHLENS_STREAM_THRESHOLD environment variable."""
    # Set threshold very low so small file triggers streaming
    monkeypatch.setenv('CRASHLENS_STREAM_THRESHOLD', '100')
    
    iterator = LogIterator(small_log_file)
    
    # Should use streaming because file > 100 bytes
    list(iterator)  # Consume iterator
    assert iterator.stats.used_streaming


def test_env_var_batch_size(small_log_file, monkeypatch):
    """Test CRASHLENS_STREAM_BATCH_SIZE environment variable."""
    monkeypatch.setenv('CRASHLENS_STREAM_BATCH_SIZE', '20')
    
    iterator = LogIterator(small_log_file, force_stream=True)
    
    batches = list(iterator)
    
    # Should use batch size from env var
    assert len(batches) == 5  # 100 / 20


def test_iterate_logs_convenience_function(small_log_file):
    """Test the convenience function iterate_logs."""
    batches = list(iterate_logs(small_log_file))
    
    assert len(batches) == 1
    assert len(batches[0]) == 100


def test_get_stats(small_log_file):
    """Test getting statistics after iteration."""
    iterator = LogIterator(small_log_file)
    
    list(iterator)  # Consume iterator
    
    stats = iterator.get_stats()
    
    assert isinstance(stats, IngestionStats)
    assert stats.total_lines == 100
    assert stats.parsed_lines == 100
    assert stats.skipped_lines == 0
    assert stats.batches_processed == 1
    assert stats.used_streaming is False


def test_empty_lines_ignored(tmp_path):
    """Test that empty lines are ignored."""
    log_file = tmp_path / "with_empty.jsonl"
    
    with open(log_file, 'w') as f:
        f.write(json.dumps({"id": 1}) + '\n')
        f.write('\n')
        f.write('   \n')
        f.write(json.dumps({"id": 2}) + '\n')
        f.write('\n')
        f.write(json.dumps({"id": 3}) + '\n')
    
    iterator = LogIterator(log_file)
    batches = list(iterator)
    
    assert len(batches[0]) == 3
    assert iterator.stats.parsed_lines == 3


def test_nonexistent_file():
    """Test handling of nonexistent file."""
    iterator = LogIterator('nonexistent.jsonl', skip_malformed=True)
    
    batches = list(iterator)
    
    # Should return empty (no error if skip_malformed=True)
    assert len(batches) == 0


def test_langfuse_schema_disabled_by_default(small_log_file):
    """Test that Langfuse schema validation is disabled by default."""
    iterator = LogIterator(small_log_file)
    
    assert iterator.langfuse_schema is False
    assert iterator.langfuse_parser is None


def test_langfuse_schema_can_be_enabled(small_log_file):
    """Test enabling Langfuse schema validation."""
    # This will only work if LangfuseParser is available
    iterator = LogIterator(small_log_file, langfuse_schema=True)
    
    # If parser is available, it should be initialized
    # If not available, should fall back gracefully
    batches = list(iterator)
    assert len(batches) > 0


def test_streaming_with_langfuse_schema(large_log_file):
    """Test streaming mode with Langfuse schema validation."""
    iterator = LogIterator(large_log_file, langfuse_schema=True)
    
    batches = list(iterator)
    
    # Should still work in streaming mode
    total = sum(len(batch) for batch in batches)
    assert total == 15000


def test_verbose_mode_shows_warnings(malformed_log_file, capsys):
    """Test that verbose mode prints warnings."""
    iterator = LogIterator(malformed_log_file, verbose=True, skip_malformed=True)
    
    list(iterator)
    
    captured = capsys.readouterr()
    
    # Should have printed warnings for malformed lines
    assert 'Warning' in captured.out or 'Warning' in captured.err


def test_batch_iteration_preserves_order(small_log_file):
    """Test that batch iteration preserves entry order."""
    iterator = LogIterator(small_log_file, force_stream=True, batch_size=10)
    
    all_ids = []
    for batch in iterator:
        for entry in batch:
            all_ids.append(entry['id'])
    
    # IDs should be in order
    assert all_ids == list(range(100))


def test_multiple_iterations_reset_stats(small_log_file):
    """Test that stats are reset on each iteration."""
    iterator = LogIterator(small_log_file)
    
    # First iteration
    list(iterator)
    stats1 = iterator.get_stats()
    
    # Second iteration
    list(iterator)
    stats2 = iterator.get_stats()
    
    # Stats should be reset
    assert stats1.parsed_lines == stats2.parsed_lines
    assert stats1.batches_processed == stats2.batches_processed


def test_path_type_accepts_string_and_path(small_log_file):
    """Test that path can be string or Path object."""
    # Test with Path object
    iterator1 = LogIterator(small_log_file)
    batches1 = list(iterator1)
    
    # Test with string
    iterator2 = LogIterator(str(small_log_file))
    batches2 = list(iterator2)
    
    assert len(batches1) == len(batches2)
    assert len(batches1[0]) == len(batches2[0])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
