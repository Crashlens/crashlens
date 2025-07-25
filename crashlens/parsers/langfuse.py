"""
Langfuse JSONL Parser
Parses Langfuse-style JSONL logs and groups by trace_id
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import click


class LangfuseParser:
    """Parser for Langfuse-style JSONL log files (newer style)"""
    
    def __init__(self):
        self.traces: Dict[str, List[Dict[str, Any]]] = {}
    
    def parse_file(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL file and group by traceId"""
        self.traces.clear()
        with open(file_path, 'r', encoding='utf-8') as f:
            return self._parse_lines(f)
    
    def parse_string(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL string and group by traceId"""
        self.traces.clear()
        lines = text.splitlines()
        return self._parse_lines(lines)
    
    def parse_stdin(self) -> Dict[str, List[Dict[str, Any]]]:
        """Parse JSONL from stdin and group by traceId"""
        self.traces.clear()
        import sys
        return self._parse_lines(sys.stdin)

    def _extract_fields(self, record: dict) -> 'Optional[dict]':
        # No type check; accept all records
        return {
            'traceId': record.get('traceId'),
            'startTime': record.get('startTime'),
            'endTime': record.get('endTime'),
            'level': record.get('level'),
            'model': record.get('input', {}).get('model'),
            'prompt': record.get('input', {}).get('prompt'),
            'prompt_tokens': record.get('usage', {}).get('prompt_tokens'),
            'completion_tokens': record.get('usage', {}).get('completion_tokens'),
            'cost': record.get('cost'),  # Add cost field
            'metadata.fallback_attempted': record.get('metadata', {}).get('fallback_attempted'),
            'metadata.fallback_reason': record.get('metadata', {}).get('fallback_reason'), # optional
            'metadata.route': record.get('metadata', {}).get('route'), # Add route field
            'metadata.team': record.get('metadata', {}).get('team'), # Add team field
            'name': record.get('name'), # optional
            'metadata.source': record.get('metadata', {}).get('source'), # optional
        }

    def _parse_lines(self, lines) -> Dict[str, List[Dict[str, Any]]]:
        """Parse lines and group by traceId (newer style)"""
        required_fields = ['traceId', 'model', 'prompt', 'completion_tokens']
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                trace_id = record.get('traceId')
                parsed = self._extract_fields(record)
                # Check for required fields
                if parsed:
                    missing = [f for f in required_fields if parsed.get(f) is None]
                    if missing:
                        click.echo(f"⚠️  Warning: Missing required field(s) {missing} on line {line_num}. Skipping.", err=True)
                        continue
                if trace_id and parsed:
                    if trace_id not in self.traces:
                        self.traces[trace_id] = []
                    self.traces[trace_id].append(parsed)
            except json.JSONDecodeError as e:
                click.echo(f"⚠️  Warning: Invalid JSON on line {line_num}: {e}", err=True)
                continue
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
            if 'completion_tokens' in record:
                total_tokens += record.get('completion_tokens', 0)
            
            # Extract cost if available
            if 'cost' in record:
                total_cost += record.get('cost', 0.0)
            
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