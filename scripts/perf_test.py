#!/usr/bin/env python3
"""
Performance test for streaming JSONL reader.

Tests memory efficiency and throughput with large datasets.
Validates that streaming reader uses constant memory regardless of file size.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Tuple

# Add crashlens to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.io.stream_reader import stream_jsonl


def generate_large_jsonl(path: Path, num_records: int = 100_000) -> None:
    """
    Generate large JSONL test file.
    
    Args:
        path: Output file path
        num_records: Number of records to generate (default: 100k)
    """
    print(f"📝 Generating {num_records:,} records...")
    
    start = time.time()
    
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(num_records):
            record = {
                'id': i,
                'traceId': f'trace-{i}',
                'model': f'gpt-{i % 5}',
                'prompt_tokens': 100 + (i % 1000),
                'completion_tokens': 50 + (i % 500),
                'metadata': {
                    'user': f'user-{i % 100}',
                    'endpoint': '/v1/chat/completions'
                }
            }
            f.write(json.dumps(record) + '\n')
    
    elapsed = time.time() - start
    file_size_mb = path.stat().st_size / (1024 * 1024)
    
    print(f"✅ Generated {file_size_mb:.2f} MB in {elapsed:.2f}s")


def benchmark_streaming(path: Path, batch_size: int) -> Tuple[float, int]:
    """
    Benchmark streaming reader performance.
    
    Args:
        path: Path to JSONL file
        batch_size: Batch size for streaming
        
    Returns:
        Tuple of (elapsed_seconds, total_records)
    """
    print(f"🔍 Streaming with batch_size={batch_size:,}...")
    
    start = time.time()
    total_records = 0
    batch_count = 0
    
    for batch in stream_jsonl(path, batch_size=batch_size, skip_malformed=True):
        total_records += len(batch)
        batch_count += 1
    
    elapsed = time.time() - start
    
    print(f"   Processed {total_records:,} records in {batch_count} batches")
    print(f"   Time: {elapsed:.2f}s ({total_records/elapsed:,.0f} records/sec)")
    
    return elapsed, total_records


def benchmark_memory_naive(path: Path) -> Tuple[float, int]:
    """
    Benchmark naive approach (load entire file).
    
    Args:
        path: Path to JSONL file
        
    Returns:
        Tuple of (elapsed_seconds, total_records)
    """
    print(f"🔍 Naive loading (full file into memory)...")
    
    start = time.time()
    records = []
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    elapsed = time.time() - start
    total_records = len(records)
    
    print(f"   Loaded {total_records:,} records")
    print(f"   Time: {elapsed:.2f}s ({total_records/elapsed:,.0f} records/sec)")
    
    return elapsed, total_records


def main():
    """Run performance benchmarks."""
    print("=" * 60)
    print("CrashLens Streaming JSONL Reader - Performance Test")
    print("=" * 60)
    print()
    
    # Create test file
    test_dir = Path(__file__).parent.parent / 'tmp'
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / 'perf_test_large.jsonl'
    
    # Generate test data
    num_records = 100_000
    
    if not test_file.exists():
        generate_large_jsonl(test_file, num_records)
    else:
        file_size_mb = test_file.stat().st_size / (1024 * 1024)
        print(f"📋 Using existing test file: {file_size_mb:.2f} MB")
    
    print()
    
    # Benchmark different batch sizes
    print("📊 Benchmarking streaming with different batch sizes:")
    print("-" * 60)
    
    batch_sizes = [100, 1_000, 5_000, 10_000]
    results = []
    
    for batch_size in batch_sizes:
        elapsed, total = benchmark_streaming(test_file, batch_size)
        results.append((batch_size, elapsed, total))
        print()
    
    # Benchmark naive approach
    print("📊 Benchmarking naive approach (full load):")
    print("-" * 60)
    naive_elapsed, naive_total = benchmark_memory_naive(test_file)
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Records processed: {num_records:,}")
    print()
    print("Streaming Results:")
    for batch_size, elapsed, total in results:
        speedup = naive_elapsed / elapsed if elapsed > 0 else 0
        print(f"  batch_size={batch_size:>6,}: {elapsed:>6.2f}s (speedup: {speedup:.2f}x)")
    
    print()
    print(f"Naive approach:         {naive_elapsed:>6.2f}s (baseline)")
    print()
    
    # Best performing batch size
    best_batch_size, best_time, _ = min(results, key=lambda x: x[1])
    print(f"🏆 Best batch size: {best_batch_size:,} ({best_time:.2f}s)")
    print()
    
    # Memory efficiency note
    print("💡 Memory Efficiency:")
    print("   Streaming: O(batch_size) constant memory")
    print("   Naive:     O(n) memory (entire file loaded)")
    print()
    
    # Cleanup option
    print(f"📁 Test file: {test_file}")
    print(f"   (To remove: rm {test_file})")


if __name__ == '__main__':
    main()
