#!/usr/bin/env python3
"""
Langfuse API Client for CrashLens
Fetches traces from Langfuse and converts them to CrashLens-compatible format.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import click
from pathlib import Path


class LangfuseClient:
    """Client for fetching traces from Langfuse API"""
    
    def __init__(self, public_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 base_url: Optional[str] = None):
        """
        Initialize Langfuse client
        
        Args:
            public_key: Langfuse public key (or from LANGFUSE_PUBLIC_KEY env var)
            secret_key: Langfuse secret key (or from LANGFUSE_SECRET_KEY env var)
            base_url: Langfuse API base URL (or from LANGFUSE_HOST env var, defaults to cloud)
        """
        self.public_key = public_key or os.getenv('LANGFUSE_PUBLIC_KEY')
        self.secret_key = secret_key or os.getenv('LANGFUSE_SECRET_KEY')
        self.base_url = (base_url or 
                        os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')).rstrip('/')
        
        if not self.public_key or not self.secret_key:
            raise ValueError(
                "Langfuse credentials required. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "environment variables or pass them directly."
            )
        
        self.session = requests.Session()
        self.session.auth = (self.public_key, self.secret_key)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CrashLens/2.0'
        })
    
    def fetch_traces(self, hours_back: int = 24, limit: int = 1000, 
                    page_size: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch traces from Langfuse API
        
        Args:
            hours_back: Number of hours back to fetch traces (default: 24)
            limit: Maximum number of traces to fetch (default: 1000)
            page_size: Number of traces per API request (default: 50)
            
        Returns:
            List of trace dictionaries from Langfuse API
        """
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        click.echo(f"🔍 Fetching Langfuse traces from {start_time.strftime('%Y-%m-%d %H:%M')} "
                  f"to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
        
        all_traces = []
        page = 1
        
        while len(all_traces) < limit:
            try:
                # Build API request
                params = {
                    'page': page,
                    'limit': min(page_size, limit - len(all_traces)),
                    'fromTimestamp': start_time.isoformat(),
                    'toTimestamp': end_time.isoformat(),
                    'orderBy': 'timestamp',
                    'orderByDirection': 'DESC'
                }
                
                click.echo(f"📡 Fetching page {page} (up to {params['limit']} traces)...")
                
                response = self.session.get(f"{self.base_url}/api/public/traces", params=params)
                response.raise_for_status()
                
                data = response.json()
                traces = data.get('data', [])
                
                if not traces:
                    click.echo("✅ No more traces found")
                    break
                
                all_traces.extend(traces)
                click.echo(f"✅ Fetched {len(traces)} traces (total: {len(all_traces)})")
                
                # Check if we've reached the end
                if len(traces) < page_size:
                    break
                    
                page += 1
                
            except requests.exceptions.RequestException as e:
                click.echo(f"❌ Error fetching traces: {e}", err=True)
                if hasattr(e, 'response') and e.response is not None:
                    click.echo(f"   Response: {e.response.text}", err=True)
                break
        
        click.echo(f"🎉 Successfully fetched {len(all_traces)} traces from Langfuse")
        return all_traces
    
    def fetch_trace_details(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific trace including generations
        
        Args:
            trace_id: The trace ID to fetch details for
            
        Returns:
            Detailed trace information with generations, or None if error
        """
        try:
            response = self.session.get(f"{self.base_url}/api/public/traces/{trace_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            click.echo(f"⚠️  Warning: Could not fetch details for trace {trace_id}: {e}", err=True)
            return None
    
    def convert_to_crashlens_format(self, traces: List[Dict[str, Any]], 
                                   include_details: bool = True) -> List[Dict[str, Any]]:
        """
        Convert Langfuse traces to CrashLens-compatible JSONL format
        
        Args:
            traces: List of Langfuse trace objects
            include_details: Whether to fetch detailed generation info (slower but more accurate)
            
        Returns:
            List of CrashLens-compatible log entries
        """
        click.echo(f"🔄 Converting {len(traces)} Langfuse traces to CrashLens format...")
        
        crashlens_logs = []
        
        for i, trace in enumerate(traces):
            try:
                if (i + 1) % 10 == 0:
                    click.echo(f"   Processing trace {i + 1}/{len(traces)}...")
                
                trace_id = trace.get('id')
                if not trace_id:
                    continue
                
                # Get detailed trace info if requested
                if include_details:
                    detailed_trace = self.fetch_trace_details(trace_id)
                    if detailed_trace:
                        trace = detailed_trace
                
                # Extract generations from the trace
                generations = []
                
                # Look for observations that are generations (completions)
                for obs in trace.get('observations', []):
                    if obs.get('type') == 'GENERATION':
                        generations.append(obs)
                
                # Convert each generation to CrashLens format
                for gen in generations:
                    log_entry = self._convert_generation_to_log_entry(trace, gen)
                    if log_entry:
                        crashlens_logs.append(log_entry)
                
                # If no generations found, create a basic log entry from trace
                if not generations:
                    basic_entry = self._convert_trace_to_log_entry(trace)
                    if basic_entry:
                        crashlens_logs.append(basic_entry)
                        
            except Exception as e:
                click.echo(f"⚠️  Warning: Error processing trace {trace.get('id', 'unknown')}: {e}", err=True)
                continue
        
        click.echo(f"✅ Converted to {len(crashlens_logs)} CrashLens log entries")
        return crashlens_logs
    
    def _convert_generation_to_log_entry(self, trace: Dict[str, Any], 
                                       generation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a Langfuse generation to CrashLens log entry format"""
        
        try:
            # Extract model info
            model = generation.get('model', 'unknown')
            
            # Extract token usage
            usage = generation.get('usage', {})
            prompt_tokens = usage.get('promptTokens', usage.get('input', 0))
            completion_tokens = usage.get('completionTokens', usage.get('output', 0))
            total_tokens = usage.get('totalTokens', prompt_tokens + completion_tokens)
            
            # Extract input/output
            input_data = generation.get('input', {})
            output_data = generation.get('output', {})
            
            # Build CrashLens format
            log_entry = {
                'trace_id': trace.get('id'),
                'generation_id': generation.get('id'),
                'timestamp': generation.get('startTime') or trace.get('timestamp'),
                'input': {
                    'model': model,
                    'messages': self._extract_messages(input_data),
                },
                'output': {
                    'content': self._extract_content(output_data),
                },
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens
                },
                'metadata': {
                    'name': generation.get('name'),
                    'level': generation.get('level'),
                    'status_message': generation.get('statusMessage'),
                    'trace_name': trace.get('name'),
                    'trace_tags': trace.get('tags', []),
                    'session_id': trace.get('sessionId'),
                    'user_id': trace.get('userId'),
                    'langfuse_trace_id': trace.get('id'),
                    'langfuse_generation_id': generation.get('id')
                }
            }
            
            # Add cost if available
            cost_details = generation.get('calculatedTotalCost')
            if cost_details:
                log_entry['cost'] = cost_details
            
            return log_entry
            
        except Exception as e:
            click.echo(f"⚠️  Error converting generation {generation.get('id', 'unknown')}: {e}", err=True)
            return None
    
    def _convert_trace_to_log_entry(self, trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a Langfuse trace (without generations) to basic CrashLens log entry"""
        
        try:
            log_entry = {
                'trace_id': trace.get('id'),
                'timestamp': trace.get('timestamp'),
                'input': {
                    'model': 'unknown',
                    'messages': []
                },
                'output': {
                    'content': ''
                },
                'usage': {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0
                },
                'metadata': {
                    'trace_name': trace.get('name'),
                    'trace_tags': trace.get('tags', []),
                    'session_id': trace.get('sessionId'),
                    'user_id': trace.get('userId'),
                    'langfuse_trace_id': trace.get('id'),
                    'note': 'Basic trace entry - no generations found'
                }
            }
            
            return log_entry
            
        except Exception as e:
            click.echo(f"⚠️  Error converting trace {trace.get('id', 'unknown')}: {e}", err=True)
            return None
    
    def _extract_messages(self, input_data: Any) -> List[Dict[str, Any]]:
        """Extract messages from Langfuse input data"""
        
        if isinstance(input_data, dict):
            if 'messages' in input_data:
                return input_data['messages']
            elif 'prompt' in input_data:
                return [{'role': 'user', 'content': input_data['prompt']}]
        elif isinstance(input_data, str):
            return [{'role': 'user', 'content': input_data}]
        elif isinstance(input_data, list):
            return input_data
        
        return []
    
    def _extract_content(self, output_data: Any) -> str:
        """Extract content from Langfuse output data"""
        
        if isinstance(output_data, dict):
            if 'content' in output_data:
                return str(output_data['content'])
            elif 'text' in output_data:
                return str(output_data['text'])
            elif 'message' in output_data:
                msg = output_data['message']
                if isinstance(msg, dict) and 'content' in msg:
                    return str(msg['content'])
                return str(msg)
        elif isinstance(output_data, str):
            return output_data
        
        return str(output_data) if output_data else ''


def save_logs_to_temp_file(logs: List[Dict[str, Any]]) -> Path:
    """Save converted logs to a temporary JSONL file"""
    
    import tempfile
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', 
                                          delete=False, encoding='utf-8')
    
    try:
        # Write logs in JSONL format
        for log_entry in logs:
            json.dump(log_entry, temp_file, ensure_ascii=False)
            temp_file.write('\n')
        
        temp_file.flush()
        temp_path = Path(temp_file.name)
        
        click.echo(f"💾 Saved {len(logs)} log entries to temporary file: {temp_path}")
        return temp_path
        
    finally:
        temp_file.close()


def test_langfuse_connection(public_key: Optional[str] = None, secret_key: Optional[str] = None) -> bool:
    """Test Langfuse API connection"""
    
    try:
        client = LangfuseClient(public_key, secret_key)
        
        # Try to fetch just 1 trace to test connection
        traces = client.fetch_traces(hours_back=24, limit=1, page_size=1)
        
        click.echo(f"✅ Langfuse connection successful! Found {len(traces)} recent traces.")
        return True
        
    except Exception as e:
        click.echo(f"❌ Langfuse connection failed: {e}", err=True)
        return False
