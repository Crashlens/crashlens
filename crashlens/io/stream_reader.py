#!/usr/bin/env python3
"""
Streaming JSONL reader with batching support for memory-efficient processing of large log files.

Supports:
- Batched reading (yield N records at a time)
- Gzip-compressed files (.gz extension)
- Malformed line skipping with warnings
- Memory-efficient iteration (no full file load)
"""

import gzip
import json
from pathlib import Path
from typing import Any, Dict, Generator, List


def stream_jsonl(
    path: Path,
    batch_size: int = 1000,
    skip_malformed: bool = True,
    verbose: bool = False
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Stream JSONL file in batches for memory-efficient processing.
    
    Yields batches of parsed JSON objects instead of loading entire file into memory.
    Supports gzip-compressed files automatically.
    
    Args:
        path: Path to JSONL file (plain or .gz compressed)
        batch_size: Number of records per batch (default: 1000)
        skip_malformed: Skip unparseable lines with warning (default: True)
        verbose: Print warnings for malformed lines (default: False)
        
    Yields:
        Lists of parsed JSON dictionaries (batch_size records each, last may be smaller)
        
    Example:
        for batch in stream_jsonl(Path('large.jsonl'), batch_size=5000):
            # Process 5000 records at a time
            for record in batch:
                analyze(record)
    
    Raises:
        FileNotFoundError: If path doesn't exist
        IOError: If file cannot be read
    """
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")
    
    # Detect gzip compression
    is_gzipped = path.suffix.lower() == '.gz'
    
    # Choose appropriate file opener
    if is_gzipped:
        file_opener = gzip.open
        open_mode = 'rt'  # Text mode for gzip
    else:
        file_opener = open
        open_mode = 'r'
    
    batch = []
    skipped_count = 0
    line_number = 0
    
    try:
        with file_opener(path, open_mode, encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Parse JSON
                try:
                    record = json.loads(line)
                    batch.append(record)
                    
                    # Yield batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                
                except json.JSONDecodeError as e:
                    skipped_count += 1
                    
                    if skip_malformed:
                        if verbose:
                            print(f"⚠️  Warning: Skipping malformed line {line_number}: {e}")
                    else:
                        # Re-raise if not skipping
                        raise
            
            # Yield remaining records
            if batch:
                yield batch
    
    except IOError as e:
        raise IOError(f"Failed to read file {path}: {e}")
    
    # Print summary of skipped lines
    if skipped_count > 0 and verbose:
        print(f"⚠️  Summary: Skipped {skipped_count} malformed lines in {path}")


def count_jsonl_records(path: Path) -> int:
    """
    Count total records in JSONL file (streaming, no full load).
    
    Args:
        path: Path to JSONL file
        
    Returns:
        Total number of records
    """
    count = 0
    for batch in stream_jsonl(path, batch_size=10000, skip_malformed=True, verbose=False):
        count += len(batch)
    return count
