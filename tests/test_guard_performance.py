"""
Performance baseline tests for guard command with large datasets.

These tests are gated by RUN_SLOW_TESTS environment variable to avoid
slowing down regular test runs. Run with:

    RUN_SLOW_TESTS=true poetry run pytest tests/test_guard_performance.py -v

or on Windows PowerShell:

    $env:RUN_SLOW_TESTS="true"; poetry run pytest tests/test_guard_performance.py -v
"""

import json
import os
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import guard
from crashlens.io.stream_reader import stream_jsonl


def generate_test_file(path: Path, num_entries: int) -> None:
    """
    Generate a test JSONL file with specified number of entries.
    
    Creates realistic log entries with varying models, token counts,
    and retry patterns to simulate production data.
    
    Args:
        path: Path to output file
        num_entries: Number of log entries to generate
    """
    models = ['gpt-4', 'gpt-3.5-turbo', 'claude-2', 'claude-instant']
    
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            entry = {
                'timestamp': f'2025-10-25T{(i % 24):02d}:{(i % 60):02d}:{(i % 60):02d}Z',
                'model': models[i % len(models)],
                'tokens': 500 + (i % 3000),  # 500-3500 tokens
                'retry_count': i % 5,  # 0-4 retries
                'fallback_triggered': (i % 10) == 0,  # 10% fallback rate
                'endpoint': '/api/generate',
                'prompt': f'Test prompt {i}',
                'cost': 0.001 * (i % 100)  # $0.001-$0.100
            }
            f.write(json.dumps(entry) + '\n')


# Gate all tests in this module with RUN_SLOW_TESTS
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SLOW_TESTS") != "true",
    reason="Slow tests are disabled. Set RUN_SLOW_TESTS=true to run."
)


class TestGuardPerformance:
    """Performance baseline tests for large log file processing."""
    
    def test_stream_jsonl_100k_entries(self, tmp_path):
        """Test streaming JSONL reader with 100k entries."""
        # Generate 100k entry test file
        log_file = tmp_path / "large_logs.jsonl"
        num_entries = 100_000
        
        print(f"\n📝 Generating {num_entries:,} test entries...")
        start_gen = time.time()
        generate_test_file(log_file, num_entries)
        gen_time = time.time() - start_gen
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        print(f"✅ Generated {file_size_mb:.2f} MB in {gen_time:.2f}s")
        
        # Test streaming with default batch size (10,000)
        print(f"\n📖 Streaming {num_entries:,} entries (batch_size=10,000)...")
        start_stream = time.time()
        
        entries_read = 0
        batch_count = 0
        for batch in stream_jsonl(log_file, batch_size=10_000, skip_malformed=True, verbose=False):
            entries_read += len(batch)
            batch_count += 1
        
        stream_time = time.time() - start_stream
        throughput = entries_read / stream_time
        
        print(f"✅ Streamed {entries_read:,} entries in {batch_count} batches")
        print(f"⏱️  Time: {stream_time:.2f}s ({throughput:,.0f} entries/sec)")
        
        # Assertions
        assert entries_read == num_entries, f"Expected {num_entries} entries, got {entries_read}"
        assert batch_count == 10, f"Expected 10 batches (100k/10k), got {batch_count}"
        assert stream_time < 30, f"Streaming took {stream_time:.2f}s (expected <30s)"
        assert throughput > 3000, f"Throughput {throughput:.0f} entries/sec (expected >3000)"
    
    def test_guard_100k_entries_no_violations(self, tmp_path):
        """Test guard command with 100k entries and no violations."""
        # Generate 100k entry test file
        log_file = tmp_path / "large_logs.jsonl"
        num_entries = 100_000
        
        print(f"\n📝 Generating {num_entries:,} test entries...")
        generate_test_file(log_file, num_entries)
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        print(f"✅ Generated {file_size_mb:.2f} MB")
        
        # Create rules that won't match
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: IMPOSSIBLE_TOKENS
    description: "Token count over 10000 (should never match)"
    if:
      if_tokens_gt: 10000
    action: warn
    severity: warn
""", encoding='utf-8')
        
        # Run guard command
        print(f"\n🛡️  Running guard on {num_entries:,} entries...")
        runner = CliRunner()
        start = time.time()
        
        result = runner.invoke(guard, [
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'json',
            '--no-content'
        ])
        
        elapsed = time.time() - start
        throughput = num_entries / elapsed
        
        print(f"✅ Processed {num_entries:,} entries")
        print(f"⏱️  Time: {elapsed:.2f}s ({throughput:,.0f} entries/sec)")
        
        # Assertions
        assert result.exit_code == 0, f"Guard failed: {result.output}"
        
        # Parse output (skip progress messages)
        output_json = json.loads(result.output[result.output.find('{'):])
        assert output_json['summary']['violations'] == 0, "Expected no violations"
        
        assert elapsed < 60, f"Processing took {elapsed:.2f}s (expected <60s)"
        assert throughput > 1500, f"Throughput {throughput:.0f} entries/sec (expected >1500)"
    
    def test_guard_100k_entries_with_violations(self, tmp_path):
        """Test guard command with 100k entries and ~10k violations."""
        # Generate 100k entry test file
        log_file = tmp_path / "large_logs.jsonl"
        num_entries = 100_000
        
        print(f"\n📝 Generating {num_entries:,} test entries...")
        generate_test_file(log_file, num_entries)
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        print(f"✅ Generated {file_size_mb:.2f} MB")
        
        # Create rules that will match ~10% (fallback_triggered)
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: FALLBACK_DETECTED
    description: "Fallback triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn
""", encoding='utf-8')
        
        # Run guard command
        print(f"\n🛡️  Running guard on {num_entries:,} entries...")
        runner = CliRunner()
        start = time.time()
        
        result = runner.invoke(guard, [
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'json',
            '--no-content'
        ])
        
        elapsed = time.time() - start
        throughput = num_entries / elapsed
        
        print(f"✅ Processed {num_entries:,} entries")
        print(f"⏱️  Time: {elapsed:.2f}s ({throughput:,.0f} entries/sec)")
        
        # Assertions
        assert result.exit_code == 0, f"Guard failed: {result.output}"
        
        # Parse output
        output_json = json.loads(result.output[result.output.find('{'):])
        violations = output_json['rules']['FALLBACK_DETECTED']['count']
        
        print(f"📊 Found {violations:,} violations (expected ~10,000)")
        
        assert 9000 <= violations <= 11000, f"Expected ~10k violations, got {violations}"
        assert elapsed < 60, f"Processing took {elapsed:.2f}s (expected <60s)"
        assert throughput > 1500, f"Throughput {throughput:.0f} entries/sec (expected >1500)"
    
    def test_guard_memory_usage_100k_entries(self, tmp_path):
        """Test that guard doesn't consume excessive memory with 100k entries."""
        pytest.importorskip("psutil", reason="psutil required for memory testing")
        import psutil
        import os as os_module
        
        # Generate 100k entry test file
        log_file = tmp_path / "large_logs.jsonl"
        num_entries = 100_000
        
        generate_test_file(log_file, num_entries)
        
        # Create simple rule
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: HIGH_TOKENS
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: warn
    severity: warn
""", encoding='utf-8')
        
        # Get baseline memory
        process = psutil.Process(os_module.getpid())
        baseline_mb = process.memory_info().rss / (1024 * 1024)
        
        print(f"\n💾 Baseline memory: {baseline_mb:.2f} MB")
        
        # Run guard command
        runner = CliRunner()
        result = runner.invoke(guard, [
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'json',
            '--no-content'
        ])
        
        # Get peak memory
        peak_mb = process.memory_info().rss / (1024 * 1024)
        memory_increase = peak_mb - baseline_mb
        
        print(f"💾 Peak memory: {peak_mb:.2f} MB")
        print(f"📈 Memory increase: {memory_increase:.2f} MB")
        
        # Assertions
        assert result.exit_code == 0, f"Guard failed: {result.output}"
        
        # Memory should not increase by more than 200MB for 100k entries
        assert memory_increase < 200, f"Memory increased by {memory_increase:.2f} MB (expected <200 MB)"
    
    def test_generate_test_file_deterministic(self, tmp_path):
        """Test that generate_test_file produces deterministic output."""
        file1 = tmp_path / "test1.jsonl"
        file2 = tmp_path / "test2.jsonl"
        
        # Generate same file twice
        generate_test_file(file1, 1000)
        generate_test_file(file2, 1000)
        
        # Files should be identical
        assert file1.read_text() == file2.read_text(), "Generated files should be identical"
        
        # Verify structure of first entry
        with open(file1, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            entry = json.loads(first_line)
            
            assert 'timestamp' in entry
            assert 'model' in entry
            assert 'tokens' in entry
            assert 'retry_count' in entry
            assert 'fallback_triggered' in entry
            assert entry['model'] in ['gpt-4', 'gpt-3.5-turbo', 'claude-2', 'claude-instant']


class TestStreamingThresholds:
    """Test streaming mode is triggered at correct thresholds."""
    
    def test_streaming_triggered_above_threshold(self, tmp_path):
        """Test that files above 10MB trigger streaming mode."""
        # Generate file just over 10MB (should trigger streaming)
        log_file = tmp_path / "medium_logs.jsonl"
        
        # ~35k entries = ~12MB
        generate_test_file(log_file, 35_000)
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        
        print(f"\n📊 File size: {file_size_mb:.2f} MB (threshold: 10 MB)")
        assert file_size_mb > 10, f"Expected file >10MB, got {file_size_mb:.2f} MB"
        
        # Create rules
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: ANY_MODEL
    description: "Any model"
    if:
      model: 'gpt-4'
    action: warn
    severity: warn
""", encoding='utf-8')
        
        # Run guard - should see streaming message
        runner = CliRunner()
        result = runner.invoke(guard, [
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'text'
        ])
        
        assert result.exit_code == 0
        # Check for streaming mode message in stderr/stdout
        assert "streaming mode" in result.output.lower() or "streaming mode" in str(result.stderr).lower()
    
    def test_no_streaming_below_threshold(self, tmp_path):
        """Test that small files don't trigger streaming mode."""
        # Generate small file (<10MB)
        log_file = tmp_path / "small_logs.jsonl"
        
        # 1k entries = ~350KB
        generate_test_file(log_file, 1_000)
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        
        print(f"\n📊 File size: {file_size_mb:.2f} MB (threshold: 10 MB)")
        assert file_size_mb < 10, f"Expected file <10MB, got {file_size_mb:.2f} MB"
        
        # Create rules
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
version: 1
rules:
  - id: ANY_MODEL
    description: "Any model"
    if:
      model: 'gpt-4'
    action: warn
    severity: warn
""", encoding='utf-8')
        
        # Run guard - should NOT see streaming message
        runner = CliRunner()
        result = runner.invoke(guard, [
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'text'
        ])
        
        assert result.exit_code == 0
        # Should not see streaming mode message for small files
        assert "streaming mode" not in result.output.lower()
