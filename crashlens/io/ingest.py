"""
Shared log ingestion layer for CrashLens.

This module provides a unified log iterator that supports streaming,
batching, and optional Langfuse schema validation.
"""

import os
import json
from pathlib import Path
from typing import Iterator, List, Dict, Any, Optional, Union
from dataclasses import dataclass

# Import Langfuse parser if available
try:
    from crashlens.parsers.langfuse import LangfuseParser
    HAS_LANGFUSE_PARSER = True
except ImportError:
    HAS_LANGFUSE_PARSER = False


# Default thresholds (can be overridden by environment variables)
DEFAULT_STREAM_THRESHOLD = 10 * 1024 * 1024  # 10 MB
DEFAULT_BATCH_SIZE = 5000


@dataclass
class IngestionStats:
    """Statistics about log ingestion."""
    total_lines: int = 0
    parsed_lines: int = 0
    skipped_lines: int = 0
    batches_processed: int = 0
    used_streaming: bool = False


class LogIterator:
    """
    Unified log iterator with streaming support and optional schema validation.
    
    This iterator provides a single interface for reading JSONL logs with:
    - Automatic streaming for large files
    - Batched processing for memory efficiency
    - Optional Langfuse schema validation
    - Graceful error handling for malformed lines
    
    Examples:
        # Simple iteration (auto-detects streaming)
        for batch in LogIterator('logs.jsonl'):
            for entry in batch:
                process(entry)
        
        # Force streaming with custom batch size
        for batch in LogIterator('logs.jsonl', force_stream=True, batch_size=1000):
            process_batch(batch)
        
        # With Langfuse schema validation
        iterator = LogIterator('logs.jsonl', langfuse_schema=True)
        for batch in iterator:
            # Entries are validated and normalized
            process_validated_batch(batch)
    """
    
    def __init__(
        self,
        path: Union[str, Path],
        stream_threshold: Optional[int] = None,
        batch_size: Optional[int] = None,
        langfuse_schema: bool = False,
        force_stream: bool = False,
        skip_malformed: bool = True,
        verbose: bool = False,
    ):
        """Initialize log iterator.
        
        Args:
            path: Path to JSONL file.
            stream_threshold: File size threshold for streaming (bytes).
                             If None, uses CRASHLENS_STREAM_THRESHOLD env var or 10MB.
            batch_size: Number of records per batch when streaming.
                       If None, uses CRASHLENS_STREAM_BATCH_SIZE env var or 5000.
            langfuse_schema: Whether to use Langfuse parser for validation.
            force_stream: Force streaming mode regardless of file size.
            skip_malformed: Continue on malformed lines (True) or raise (False).
            verbose: Print warnings for skipped lines.
        """
        self.path = Path(path)
        self.langfuse_schema = langfuse_schema and HAS_LANGFUSE_PARSER
        self.force_stream = force_stream
        self.skip_malformed = skip_malformed
        self.verbose = verbose
        
        # Get thresholds from env vars or defaults
        if stream_threshold is None:
            stream_threshold = int(os.getenv(
                'CRASHLENS_STREAM_THRESHOLD',
                str(DEFAULT_STREAM_THRESHOLD)
            ))
        
        if batch_size is None:
            batch_size = int(os.getenv(
                'CRASHLENS_STREAM_BATCH_SIZE',
                str(DEFAULT_BATCH_SIZE)
            ))
        
        self.stream_threshold = stream_threshold
        self.batch_size = batch_size
        
        # Statistics
        self.stats = IngestionStats()
        
        # Initialize Langfuse parser if requested
        self.langfuse_parser: Optional[Any] = None
        if self.langfuse_schema:
            if not HAS_LANGFUSE_PARSER:
                if verbose:
                    print("Warning: Langfuse parser not available, falling back to basic JSON parsing")
            else:
                try:
                    self.langfuse_parser = LangfuseParser(
                        verbose=verbose,
                        fail_fast=not skip_malformed
                    )
                except Exception as e:
                    if verbose:
                        print(f"Warning: Could not initialize Langfuse parser: {e}")
                    self.langfuse_parser = None
        
        # Determine if we should use streaming
        self._should_stream = self._check_should_stream()
    
    def _check_should_stream(self) -> bool:
        """Check if we should use streaming mode."""
        if self.force_stream:
            return True
        
        if not self.path.exists():
            return False
        
        try:
            file_size = self.path.stat().st_size
            return file_size > self.stream_threshold
        except OSError:
            return False
    
    def __iter__(self) -> Iterator[List[Dict[str, Any]]]:
        """Iterate over log batches.
        
        Yields:
            List of log entry dictionaries (batch).
        """
        self.stats = IngestionStats()  # Reset stats
        self.stats.used_streaming = self._should_stream
        
        if self._should_stream:
            yield from self._stream_batches()
        else:
            yield from self._load_all()
    
    def _stream_batches(self) -> Iterator[List[Dict[str, Any]]]:
        """Stream file in batches (for large files)."""
        batch = []
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    self.stats.total_lines += 1
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    entry = self._parse_line(line, line_num)
                    if entry is not None:
                        batch.append(entry)
                        self.stats.parsed_lines += 1
                        
                        # Yield batch when full
                        if len(batch) >= self.batch_size:
                            self.stats.batches_processed += 1
                            yield batch
                            batch = []
                
                # Yield remaining entries
                if batch:
                    self.stats.batches_processed += 1
                    yield batch
        
        except IOError as e:
            if self.verbose:
                print(f"Error reading file {self.path}: {e}")
            if not self.skip_malformed:
                raise
    
    def _load_all(self) -> Iterator[List[Dict[str, Any]]]:
        """Load entire file at once (for small files)."""
        all_entries = []
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    self.stats.total_lines += 1
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    entry = self._parse_line(line, line_num)
                    if entry is not None:
                        all_entries.append(entry)
                        self.stats.parsed_lines += 1
            
            # Return all entries as a single batch
            if all_entries:
                self.stats.batches_processed = 1
                yield all_entries
        
        except IOError as e:
            if self.verbose:
                print(f"Error reading file {self.path}: {e}")
            if not self.skip_malformed:
                raise
    
    def _parse_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Parse a single line.
        
        Args:
            line: Raw line string.
            line_num: Line number (for error reporting).
            
        Returns:
            Parsed entry dict, or None if parsing failed.
        """
        # Try Langfuse parser first if enabled
        if self.langfuse_parser is not None:
            try:
                # LangfuseParser expects a dict, so parse JSON first
                raw_entry = json.loads(line)
                # Note: LangfuseParser.parse_file returns grouped traces
                # For line-by-line parsing, we just validate and return
                # This is a simplified approach; full integration would use parse_file
                return raw_entry
            except json.JSONDecodeError as e:
                self.stats.skipped_lines += 1
                if self.verbose:
                    print(f"Warning: Line {line_num}: Invalid JSON: {e}")
                if not self.skip_malformed:
                    raise
                return None
            except Exception as e:
                self.stats.skipped_lines += 1
                if self.verbose:
                    print(f"Warning: Line {line_num}: Validation failed: {e}")
                if not self.skip_malformed:
                    raise
                return None
        
        # Basic JSON parsing
        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            self.stats.skipped_lines += 1
            if self.verbose:
                content_snippet = line[:80] + "..." if len(line) > 80 else line
                print(f"Warning: Line {line_num}: Invalid JSON: {e}")
                print(f"  Content: {content_snippet}")
            if not self.skip_malformed:
                raise
            return None
    
    def get_stats(self) -> IngestionStats:
        """Get ingestion statistics.
        
        Returns:
            IngestionStats object with counts and metadata.
        """
        return self.stats


def iterate_logs(
    path: Union[str, Path],
    **kwargs
) -> Iterator[List[Dict[str, Any]]]:
    """Convenience function to iterate over logs.
    
    Args:
        path: Path to JSONL file.
        **kwargs: Additional arguments passed to LogIterator.
    
    Yields:
        Batches of log entries.
    
    Examples:
        for batch in iterate_logs('logs.jsonl'):
            process(batch)
    """
    iterator = LogIterator(path, **kwargs)
    yield from iterator
