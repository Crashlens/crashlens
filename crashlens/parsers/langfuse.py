"""
Langfuse JSONL Parser
Parses Langfuse-style JSONL logs and groups by trace_id
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
import click


class InvalidTraceError(Exception):
    """Raised when a trace fails schema validation"""
    pass


class LangfuseParser:
    """
    Parser for Langfuse-style JSONL log files with production-grade robustness.
    
    Features:
    - Schema version contracts with configurable required/optional fields
    - Schema validation with proper error handling and unknown field detection
    - Colorful logging with different levels (info, warning, error)
    - Verbose mode toggle for debug information
    - Fail-fast mode for strict validation
    - Trace duration calculation from timestamps
    - Model cost tracking and aggregation
    - Timestamp-based sorting within traces
    - Extensible schema system for future versions
    
    Examples:
        Basic usage:
        >>> parser = LangfuseParser()
        >>> traces = parser.parse_file(Path("logs.jsonl"))
        
        With verbose logging and fail-fast:
        >>> parser = LangfuseParser(verbose=True, fail_fast=True)
        >>> traces = parser.parse_string(jsonl_content)
        >>> costs = parser.get_model_costs()
        
        Parse and sort by timestamp:
        >>> traces = parser.parse_all("logs.jsonl", sort_traces=True)
        
        Add custom schema version:
        >>> parser.add_schema_contract("v2", ["traceId", "userId"], 
        ...                          ["model"], {"traceId", "userId", "model"})
    """
    
    def __init__(self, verbose: bool = False, fail_fast: bool = False, default_schema: str = "v1"):
        """
        Initialize the parser with options for verbose logging and fail-fast behavior.
        
        Args:
            verbose: Enable debug logging when True
            fail_fast: Raise on first error when True, otherwise skip bad lines
            default_schema: Default schema version to use for parsing
        """
        self.traces: Dict[str, List[Dict[str, Any]]] = {}
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.default_schema = default_schema
        self.model_costs: Dict[str, Dict[str, int]] = {}  # model -> {prompt_tokens, completion_tokens}
        
        # Define schema contracts for different versions
        self.schema_contracts = {
            "v1": {
                "required_fields": [
                    "traceId"
                ],
                "warn_fields": [
                    "model",
                    "prompt_tokens", 
                    "completion_tokens"
                ],
                "all_known_fields": {
                    # Core fields
                    "traceId", "startTime", "endTime", "level", "name", "cost",
                    # Input fields
                    "model", "prompt", "prompt_tokens", "completion_tokens",
                    # Metadata fields  
                    "metadata.fallback_attempted", "metadata.fallback_reason",
                    "metadata.route", "metadata.team", "metadata.source",
                    # Additional fields
                    "userId", "timestamp",
                    # Computed fields
                    "duration_sec"
                }
            }
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(levelname)s: %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Set log level based on verbose mode
        self.logger.setLevel(logging.DEBUG if verbose else logging.WARNING)
    
    def parse_file(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL file and group by traceId"""
        self.traces.clear()
        self.model_costs.clear()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.logger.info(f"Parsing file: {file_path}")
                return self._parse_lines(f)
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            if self.fail_fast:
                raise FileNotFoundError(error_msg)
            return {}
        except IOError as e:
            error_msg = f"IO error reading file {file_path}: {e}"
            self.logger.error(error_msg)
            if self.fail_fast:
                raise IOError(error_msg)
            return {}
    
    def parse_string(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL string and group by traceId"""
        self.traces.clear()
        self.model_costs.clear()
        lines = text.splitlines()
        self.logger.debug(f"Parsing {len(lines)} lines from string")
        return self._parse_lines(lines)
    
    def parse_stdin(self) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL from stdin and group by traceId"""
        self.traces.clear()
        self.model_costs.clear()
        self.logger.debug("Parsing from stdin")
        return self._parse_lines(sys.stdin)

    def _normalize_v1(self, record: dict, schema_version: str = "v1") -> Optional[dict]:
        """
        Extract and validate fields from a record using schema contracts.
        
        Args:
            record: Raw JSON record
            schema_version: Schema version to validate against
            
        Returns:
            Normalized record dict or None if validation fails
            
        Raises:
            InvalidTraceError: If required fields are missing and fail_fast is True
        """
        if schema_version not in self.schema_contracts:
            self.logger.warning(f"Unknown schema version: {schema_version}, falling back to v1")
            schema_version = "v1"
            
        contract = self.schema_contracts[schema_version]
        
        # Extract basic fields
        extracted = {
            'traceId': record.get('traceId'),
            'startTime': record.get('startTime'),
            'endTime': record.get('endTime'),
            'level': record.get('level'),
            'model': record.get('input', {}).get('model'),
            'prompt': record.get('input', {}).get('prompt'),
            'prompt_tokens': record.get('usage', {}).get('prompt_tokens'),
            'completion_tokens': record.get('usage', {}).get('completion_tokens'),
            'cost': record.get('cost'),
            'metadata.fallback_attempted': record.get('metadata', {}).get('fallback_attempted'),
            'metadata.fallback_reason': record.get('metadata', {}).get('fallback_reason'),
            'metadata.route': record.get('metadata', {}).get('route'),
            'metadata.team': record.get('metadata', {}).get('team'),
            'name': record.get('name'),
            'metadata.source': record.get('metadata', {}).get('source'),
            # Additional fields that might be top-level
            'userId': record.get('userId'),
            'timestamp': record.get('timestamp'),
        }
        
        # Check for required fields using schema contract
        missing_required = [field for field in contract["required_fields"] 
                          if extracted.get(field) is None]
        if missing_required:
            error_msg = f"Missing required field(s) for {schema_version}: {missing_required}"
            self.logger.error(error_msg)
            if self.fail_fast:
                raise InvalidTraceError(error_msg)
            return None
        
        # Warn about missing optional but important fields using schema contract
        missing_warn = [field for field in contract["warn_fields"] 
                       if extracted.get(field) is None]
        if missing_warn:
            line_info = getattr(self, '_current_line_num', '?')
            self.logger.warning(f"[Line {line_info}] Missing optional field(s) for {schema_version}: {missing_warn}")
            # Track warnings as data quality issues
            self.parsing_stats['warning_records'] += 1
            self.parsing_stats['has_errors'] = True
        
        # Add trace duration if both timestamps exist
        if extracted['startTime'] and extracted['endTime']:
            try:
                start_time = self._parse_timestamp(extracted['startTime'])
                end_time = self._parse_timestamp(extracted['endTime'])
                if start_time and end_time:
                    extracted['duration_sec'] = (end_time - start_time).total_seconds()
                    self.logger.debug(f"Calculated duration: {extracted['duration_sec']}s")
            except Exception as e:
                self.logger.warning(f"Failed to calculate duration: {e}")
        
        # Identify and log unknown fields not in the schema contract
        extracted_fields = set(key for key, value in extracted.items() if value is not None)
        unknown_fields = extracted_fields - contract["all_known_fields"]
        if unknown_fields:
            self.logger.info(f"Unknown fields found (not in {schema_version} schema): {sorted(unknown_fields)}")
        
        # Also check for any top-level fields in the original record that we didn't extract
        original_top_level = set(record.keys())
        # Map some known nested paths back to their top-level equivalents
        known_top_level = {'traceId', 'startTime', 'endTime', 'level', 'name', 'cost', 
                          'input', 'usage', 'metadata', 'userId', 'timestamp'}
        unexpected_top_level = original_top_level - known_top_level
        if unexpected_top_level:
            self.logger.info(f"Unexpected top-level fields in record: {sorted(unexpected_top_level)}")
        
        return extracted

    def _normalize_record(self, record: dict, schema_version: str = "v1") -> Optional[dict]:
        """
        Generic record normalization that delegates to version-specific methods.
        
        Args:
            record: Raw JSON record
            schema_version: Schema version to use for normalization
            
        Returns:
            Normalized record dict or None if validation fails
        """
        # For now, all versions use the same extraction logic but different validation
        # This allows for easy extension in the future
        if schema_version in self.schema_contracts:
            return self._normalize_v1(record, schema_version)
        else:
            self.logger.warning(f"Unknown schema version: {schema_version}, falling back to v1")
            return self._normalize_v1(record, "v1")

    def add_schema_contract(self, version: str, required_fields: List[str], 
                           warn_fields: List[str], all_known_fields: set) -> None:
        """
        Add a new schema contract version.
        
        Args:
            version: Schema version identifier (e.g., "v2")
            required_fields: List of fields that must be present
            warn_fields: List of optional fields to warn about if missing
            all_known_fields: Set of all fields known in this schema version
        """
        self.schema_contracts[version] = {
            "required_fields": required_fields,
            "warn_fields": warn_fields,
            "all_known_fields": all_known_fields
        }
        self.logger.info(f"Added schema contract for version: {version}")

    def get_available_schema_versions(self) -> List[str]:
        """Get list of available schema versions"""
        return list(self.schema_contracts.keys())

    def validate_schema_contract(self, version: str) -> bool:
        """
        Validate that a schema contract is properly defined.
        
        Args:
            version: Schema version to validate
            
        Returns:
            True if contract is valid, False otherwise
        """
        if version not in self.schema_contracts:
            self.logger.error(f"Schema version {version} not found")
            return False
            
        contract = self.schema_contracts[version]
        required_keys = {"required_fields", "warn_fields", "all_known_fields"}
        
        if not all(key in contract for key in required_keys):
            missing_keys = required_keys - set(contract.keys())
            self.logger.error(f"Schema contract {version} missing required keys: {missing_keys}")
            return False
            
        # Validate that required and warn fields are subsets of all known fields
        required_set = set(contract["required_fields"])
        warn_set = set(contract["warn_fields"])
        known_set = contract["all_known_fields"]
        
        if not required_set.issubset(known_set):
            unknown_required = required_set - known_set
            self.logger.error(f"Schema {version}: required fields not in known fields: {unknown_required}")
            return False
            
        if not warn_set.issubset(known_set):
            unknown_warn = warn_set - known_set
            self.logger.error(f"Schema {version}: warn fields not in known fields: {unknown_warn}")
            return False
            
        self.logger.info(f"Schema contract {version} is valid")
        return True

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse ISO timestamp string safely.
        
        Args:
            timestamp_str: ISO timestamp string
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None
            
        try:
            # Handle various ISO formats
            if timestamp_str.endswith('Z'):
                # Replace Z with +00:00 for Python compatibility
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            # Try parsing with timezone info
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            try:
                # Fallback: try without timezone
                return datetime.fromisoformat(timestamp_str.replace('Z', ''))
            except ValueError:
                self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
                return None

    def _update_model_costs(self, parsed_record: Dict[str, Any]) -> None:
        """
        Update model costs tracking with token usage from a parsed record.
        
        Args:
            parsed_record: Normalized record with token usage data
        """
        model = parsed_record.get('model')
        if not model:
            return
            
        prompt_tokens = parsed_record.get('prompt_tokens', 0) or 0
        completion_tokens = parsed_record.get('completion_tokens', 0) or 0
        
        if model not in self.model_costs:
            self.model_costs[model] = {'prompt_tokens': 0, 'completion_tokens': 0}
        
        self.model_costs[model]['prompt_tokens'] += prompt_tokens
        self.model_costs[model]['completion_tokens'] += completion_tokens
        
        self.logger.debug(f"Updated costs for {model}: +{prompt_tokens} prompt, +{completion_tokens} completion tokens")

    def _parse_lines(self, lines) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse lines and group by traceId with enhanced error handling and validation.
        
        Args:
            lines: Iterable of lines to parse
            
        Returns:
            Dictionary mapping trace IDs to lists of normalized records
        """
        # Initialize parsing statistics
        self.parsing_stats = {
            'valid_records': 0,
            'skipped_records': 0,
            'warning_records': 0,
            'has_errors': False
        }
        
        valid_records = 0
        skipped_records = 0
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
                self.logger.debug(f"Line {line_num}: Parsing record")
                
                # Set current input line number for downstream logging context
                self._current_line_num = line_num
                parsed = self._normalize_record(record, self.default_schema)
                if not parsed:
                    skipped_records += 1
                    self.logger.warning(f"Line {line_num}: Skipping invalid record")
                    if self.fail_fast:
                        raise ValueError(f"Invalid record on line {line_num}")
                    continue
                
                trace_id = parsed.get('traceId')
                if not trace_id:
                    skipped_records += 1
                    self.logger.warning(f"Line {line_num}: Missing traceId")
                    if self.fail_fast:
                        raise ValueError(f"Missing traceId on line {line_num}")
                    continue
                
                # Add to traces
                if trace_id not in self.traces:
                    self.traces[trace_id] = []
                self.traces[trace_id].append(parsed)
                
                # Update model costs tracking
                self._update_model_costs(parsed)
                
                valid_records += 1
                
            except InvalidTraceError as e:
                skipped_records += 1
                error_msg = f"Line {line_num}: {e}"
                self.logger.error(error_msg)
                if self.fail_fast:
                    raise
                continue
                
            except json.JSONDecodeError as e:
                skipped_records += 1
                error_msg = f"Line {line_num}: Invalid JSON - {e}"
                self.logger.error(error_msg)
                if self.fail_fast:
                    raise json.JSONDecodeError(f"JSON decode error on line {line_num}", line, 0) from e
                continue
                
            except Exception as e:
                skipped_records += 1
                error_msg = f"Line {line_num}: Unexpected error - {e}"
                self.logger.error(error_msg)
                if self.fail_fast:
                    raise
                continue
        
        # Store parsing statistics
        self.parsing_stats = {
            'valid_records': valid_records,
            'skipped_records': skipped_records,
            'warning_records': self.parsing_stats.get('warning_records', 0),
            'has_errors': skipped_records > 0 or self.parsing_stats.get('warning_records', 0) > 0
        }
        
        self.logger.info(f"Parsing complete: {valid_records} valid records, {skipped_records} skipped")
        return self.traces
    
    def get_trace_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get summary statistics for a trace"""
        if trace_id not in self.traces:
            return {}
        
        trace_records = self.traces[trace_id]
        
        # Extract key metrics
        total_tokens = 0
        total_cost = 0.0
        model_usage = {}
        
        for record in trace_records:
            # Extract token usage
            completion_tokens = record.get('completion_tokens')
            if completion_tokens is not None:
                total_tokens += completion_tokens
            
            # Extract cost if available
            cost = record.get('cost')
            if cost is not None:
                total_cost += cost
            
            # Track model usage
            model = record.get('model', 'unknown')
            if model not in model_usage:
                model_usage[model] = 0
            model_usage[model] += 1
        
        return {
            'trace_id': trace_id,
            'total_records': len(trace_records),
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'model_usage': model_usage,
            'records': trace_records
        }

    def get_model_costs(self) -> Dict[str, Dict[str, int]]:
        """
        Get aggregated model costs across all traces.
        
        Returns:
            Dictionary mapping model names to token usage statistics
        """
        return self.model_costs.copy()
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        """
        Get parsing statistics including error counts.
        
        Returns:
            Dictionary with parsing statistics
        """
        return getattr(self, 'parsing_stats', {
            'valid_records': 0,
            'skipped_records': 0,
            'warning_records': 0,
            'has_errors': False
        })
    
    def has_parsing_errors(self) -> bool:
        """
        Check if there were any parsing errors during the last parse operation.
        
        Returns:
            True if there were parsing errors, False otherwise
        """
        stats = self.get_parsing_stats()
        return stats.get('has_errors', False)

    def sort_by_timestamp(self) -> None:
        """
        Sort records within each trace by timestamp (startTime).
        Records without startTime will be placed at the end.
        """
        for trace_id in self.traces:
            self.traces[trace_id].sort(
                key=lambda record: self._parse_timestamp(record.get('startTime', '')) or datetime.min.replace(tzinfo=timezone.utc)
            )
        
        self.logger.debug("Sorted all traces by timestamp")

    def parse_all(self, source, sort_traces: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convenience method to parse from various sources and optionally sort.
        
        Args:
            source: Can be a Path, string content, or 'stdin'
            sort_traces: Whether to sort traces by timestamp after parsing
            
        Returns:
            Dictionary mapping trace IDs to lists of normalized records
        """
        if source == 'stdin':
            result = self.parse_stdin()
        elif isinstance(source, (str, Path)) and Path(source).exists():
            result = self.parse_file(Path(source))
        else:
            # Assume it's string content
            result = self.parse_string(str(source))
        
        if sort_traces:
            self.sort_by_timestamp()
            
        return result 