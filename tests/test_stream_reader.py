#!/usr/bin/env python3
"""
Unit tests for streaming JSONL reader (Step 3).
"""

import gzip
import json
from pathlib import Path

import pytest

from crashlens.io.stream_reader import stream_jsonl, count_jsonl_records


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create sample JSONL file."""
    jsonl_file = tmp_path / "sample.jsonl"
    records = [
        {"id": 1, "model": "gpt-4", "tokens": 100},
        {"id": 2, "model": "gpt-3.5-turbo", "tokens": 200},
        {"id": 3, "model": "claude-2", "tokens": 150},
        {"id": 4, "model": "gpt-4", "tokens": 300},
        {"id": 5, "model": "llama-2", "tokens": 250},
    ]
    
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    return jsonl_file


@pytest.fixture
def large_jsonl(tmp_path):
    """Create large JSONL file (5000 records)."""
    jsonl_file = tmp_path / "large.jsonl"
    
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for i in range(5000):
            record = {
                "id": i,
                "model": f"model-{i % 10}",
                "tokens": 100 + (i % 500)
            }
            f.write(json.dumps(record) + '\n')
    
    return jsonl_file


@pytest.fixture
def malformed_jsonl(tmp_path):
    """Create JSONL file with malformed lines."""
    jsonl_file = tmp_path / "malformed.jsonl"
    content = """{"id": 1, "valid": true}
{ invalid json without quotes
{"id": 2, "valid": true}
    
{"id": 3, "valid": true}
{"incomplete": 
{"id": 4, "valid": true}
"""
    jsonl_file.write_text(content)
    return jsonl_file


@pytest.fixture
def gzipped_jsonl(tmp_path):
    """Create gzip-compressed JSONL file."""
    jsonl_file = tmp_path / "compressed.jsonl.gz"
    records = [
        {"id": i, "compressed": True}
        for i in range(100)
    ]
    
    with gzip.open(jsonl_file, 'wt', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    return jsonl_file


class TestStreamJSONL:
    """Test basic streaming functionality."""
    
    def test_stream_small_file(self, sample_jsonl):
        """Stream small file in single batch."""
        batches = list(stream_jsonl(sample_jsonl, batch_size=10))
        
        # All records in one batch
        assert len(batches) == 1
        assert len(batches[0]) == 5
        
        # Verify content
        assert batches[0][0]['id'] == 1
        assert batches[0][4]['id'] == 5
    
    def test_stream_with_batching(self, sample_jsonl):
        """Stream with small batch size."""
        batches = list(stream_jsonl(sample_jsonl, batch_size=2))
        
        # Should have 3 batches: [2, 2, 1]
        assert len(batches) == 3
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1
        
        # Verify IDs are sequential
        assert batches[0][0]['id'] == 1
        assert batches[0][1]['id'] == 2
        assert batches[1][0]['id'] == 3
        assert batches[2][0]['id'] == 5
    
    def test_stream_large_file(self, large_jsonl):
        """Stream large file efficiently."""
        batch_size = 1000
        batches = list(stream_jsonl(large_jsonl, batch_size=batch_size))
        
        # Should have 5 batches of 1000 each
        assert len(batches) == 5
        
        for i, batch in enumerate(batches):
            assert len(batch) == batch_size
            # Verify first record ID in each batch
            expected_first_id = i * batch_size
            assert batch[0]['id'] == expected_first_id
    
    def test_stream_empty_file(self, tmp_path):
        """Handle empty file gracefully."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        
        batches = list(stream_jsonl(empty_file, batch_size=100))
        assert len(batches) == 0
    
    def test_stream_file_not_found(self):
        """Raise error for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            list(stream_jsonl(Path("nonexistent.jsonl")))


class TestMalformedLines:
    """Test handling of malformed JSON lines."""
    
    def test_skip_malformed_lines(self, malformed_jsonl):
        """Skip malformed lines by default."""
        batches = list(stream_jsonl(malformed_jsonl, batch_size=10, skip_malformed=True))
        
        # Should get 4 valid records
        assert len(batches) == 1
        assert len(batches[0]) == 4
        
        # Verify only valid records
        assert all(record.get('valid') is True for record in batches[0])
    
    def test_raise_on_malformed(self, malformed_jsonl):
        """Raise error when skip_malformed=False."""
        with pytest.raises(json.JSONDecodeError):
            list(stream_jsonl(malformed_jsonl, batch_size=10, skip_malformed=False))
    
    def test_verbose_warnings(self, malformed_jsonl, capsys):
        """Print warnings in verbose mode."""
        list(stream_jsonl(malformed_jsonl, batch_size=10, skip_malformed=True, verbose=True))
        
        captured = capsys.readouterr()
        # Should warn about malformed lines
        assert "⚠️  Warning: Skipping malformed line" in captured.out
        assert "Summary: Skipped" in captured.out


class TestGzipSupport:
    """Test gzip-compressed file support."""
    
    def test_read_gzipped_file(self, gzipped_jsonl):
        """Read gzip-compressed JSONL file."""
        batches = list(stream_jsonl(gzipped_jsonl, batch_size=50))
        
        # Should have 2 batches: [50, 50]
        assert len(batches) == 2
        assert len(batches[0]) == 50
        assert len(batches[1]) == 50
        
        # Verify content
        assert batches[0][0]['compressed'] is True
    
    def test_gzip_auto_detection(self, gzipped_jsonl):
        """Automatically detect .gz extension."""
        # Just verify it works without explicit flag
        batches = list(stream_jsonl(gzipped_jsonl))
        assert len(batches) > 0
        assert all('compressed' in record for batch in batches for record in batch)


class TestCountRecords:
    """Test count_jsonl_records utility."""
    
    def test_count_small_file(self, sample_jsonl):
        """Count records in small file."""
        count = count_jsonl_records(sample_jsonl)
        assert count == 5
    
    def test_count_large_file(self, large_jsonl):
        """Count records in large file."""
        count = count_jsonl_records(large_jsonl)
        assert count == 5000
    
    def test_count_with_malformed(self, malformed_jsonl):
        """Count skips malformed lines."""
        count = count_jsonl_records(malformed_jsonl)
        assert count == 4  # Only valid records
    
    def test_count_gzipped(self, gzipped_jsonl):
        """Count records in compressed file."""
        count = count_jsonl_records(gzipped_jsonl)
        assert count == 100


class TestMemoryEfficiency:
    """Test memory efficiency of streaming."""
    
    def test_no_full_load(self, large_jsonl):
        """Verify streaming doesn't load entire file."""
        # Process only first batch
        first_batch = next(stream_jsonl(large_jsonl, batch_size=100))
        
        # Should get exactly 100 records
        assert len(first_batch) == 100
        assert first_batch[0]['id'] == 0
        assert first_batch[99]['id'] == 99
    
    def test_generator_behavior(self, sample_jsonl):
        """Verify returns generator (lazy evaluation)."""
        result = stream_jsonl(sample_jsonl, batch_size=2)
        
        # Should be generator, not list
        assert hasattr(result, '__next__')
        assert hasattr(result, '__iter__')
        
        # Consume manually
        batch1 = next(result)
        assert len(batch1) == 2
        
        batch2 = next(result)
        assert len(batch2) == 2


class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_single_record(self, tmp_path):
        """Handle file with single record."""
        single_file = tmp_path / "single.jsonl"
        single_file.write_text('{"only": "one"}\n')
        
        batches = list(stream_jsonl(single_file, batch_size=10))
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0][0]['only'] == 'one'
    
    def test_empty_lines_skipped(self, tmp_path):
        """Skip empty lines."""
        file_with_blanks = tmp_path / "blanks.jsonl"
        content = """{"id": 1}

{"id": 2}
    
    
{"id": 3}
"""
        file_with_blanks.write_text(content)
        
        batches = list(stream_jsonl(file_with_blanks, batch_size=10))
        assert len(batches) == 1
        assert len(batches[0]) == 3
    
    def test_large_batch_size(self, sample_jsonl):
        """Handle batch size larger than file."""
        batches = list(stream_jsonl(sample_jsonl, batch_size=10000))
        
        # All in one batch
        assert len(batches) == 1
        assert len(batches[0]) == 5
    
    def test_batch_size_one(self, sample_jsonl):
        """Handle batch_size=1."""
        batches = list(stream_jsonl(sample_jsonl, batch_size=1))
        
        # Each record in separate batch
        assert len(batches) == 5
        assert all(len(batch) == 1 for batch in batches)
