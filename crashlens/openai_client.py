#!/usr/bin/env python3
"""
OpenAI Usage API Client for CrashLens
Fetches usage data from OpenAI API and converts to CrashLens-compatible format.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import click
from pathlib import Path


class OpenAIClient:
    """Client for fetching usage data from OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None, org_id: Optional[str] = None):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key (or from OPENAI_API_KEY env var)
            org_id: OpenAI Organization ID (or from OPENAI_ORG_ID env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.org_id = org_id or os.getenv('OPENAI_ORG_ID')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass it directly."
            )
        
        self.session = requests.Session()
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'CrashLens/2.0'
        }
        
        if self.org_id:
            headers['OpenAI-Organization'] = self.org_id
            
        self.session.headers.update(headers)
    
    def fetch_usage_data(self, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch usage data from OpenAI API
        
        Args:
            days_back: Number of days back to fetch usage (default: 1)
            
        Returns:
            List of usage data dictionaries
        """
        
        # Calculate date range
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days_back)
        
        click.echo(f"[OPENAI] Fetching usage data from {start_date} to {end_date}")
        
        try:
            # OpenAI usage API endpoint
            params = {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            response = self.session.get('https://api.openai.com/v1/usage', params=params)
            response.raise_for_status()
            
            data = response.json()
            usage_data = data.get('data', [])
            
            click.echo(f"[OPENAI] Successfully fetched {len(usage_data)} usage records")
            return usage_data
            
        except requests.exceptions.RequestException as e:
            click.echo(f"[ERROR] Error fetching OpenAI usage data: {e}", err=True)
            if hasattr(e, 'response') and e.response is not None:
                click.echo(f"   Response: {e.response.text}", err=True)
            return []
    
    def convert_to_crashlens_format(self, usage_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert OpenAI usage data to CrashLens-compatible JSONL format
        
        Args:
            usage_data: List of OpenAI usage objects
            
        Returns:
            List of CrashLens-compatible log entries
        """
        click.echo(f"[OPENAI] Converting {len(usage_data)} usage records to CrashLens format...")
        
        crashlens_logs = []
        
        for i, usage_record in enumerate(usage_data):
            try:
                if (i + 1) % 10 == 0:
                    click.echo(f"   Processing record {i + 1}/{len(usage_data)}...")
                
                # Create multiple log entries for each usage record based on snapshots
                log_entries = self._convert_usage_to_log_entries(usage_record)
                crashlens_logs.extend(log_entries)
                        
            except Exception as e:
                click.echo(f"[WARNING] Error processing usage record: {e}", err=True)
                continue
        
        click.echo(f"[OPENAI] Converted to {len(crashlens_logs)} CrashLens log entries")
        return crashlens_logs
    
    def _convert_usage_to_log_entries(self, usage_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert an OpenAI usage record to CrashLens log entries"""
        
        try:
            aggregation_timestamp = usage_record.get('aggregation_timestamp')
            object_type = usage_record.get('object', 'usage')
            
            log_entries = []
            
            # Process each model usage snapshot
            for snapshot in usage_record.get('data', []):
                # Extract model and usage info
                model = snapshot.get('snapshot_id', 'unknown')
                n_requests = snapshot.get('n_requests', 0)
                operation = snapshot.get('operation', 'completion')
                
                # Extract token usage
                n_context_tokens_total = snapshot.get('n_context_tokens_total', 0)
                n_generated_tokens_total = snapshot.get('n_generated_tokens_total', 0)
                
                # Calculate costs if available
                cost_usd = 0.0
                if 'cost' in snapshot:
                    cost_usd = snapshot['cost']
                
                # Create a synthetic log entry for each request batch
                log_entry = {
                    'trace_id': f"openai-usage-{aggregation_timestamp}-{model}",
                    'timestamp': aggregation_timestamp,
                    'input': {
                        'model': model,
                        'messages': [{'role': 'system', 'content': f'Aggregated usage for {n_requests} requests'}],
                    },
                    'output': {
                        'content': f'Usage summary: {n_requests} requests processed',
                    },
                    'usage': {
                        'prompt_tokens': n_context_tokens_total,
                        'completion_tokens': n_generated_tokens_total,
                        'total_tokens': n_context_tokens_total + n_generated_tokens_total
                    },
                    'cost': cost_usd,
                    'metadata': {
                        'source': 'openai_usage_api',
                        'operation': operation,
                        'n_requests': n_requests,
                        'aggregation_timestamp': aggregation_timestamp,
                        'is_usage_summary': True,
                        'openai_snapshot_id': snapshot.get('snapshot_id'),
                        'organization_id': self.org_id
                    }
                }
                
                log_entries.append(log_entry)
            
            return log_entries
            
        except Exception as e:
            click.echo(f"[WARNING] Error converting usage record: {e}", err=True)
            return []
    
    def fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenAI API"""
        
        try:
            response = self.session.get('https://api.openai.com/v1/models')
            response.raise_for_status()
            
            data = response.json()
            models = data.get('data', [])
            
            click.echo(f"[OPENAI] Found {len(models)} available models")
            return models
            
        except requests.exceptions.RequestException as e:
            click.echo(f"[WARNING] Could not fetch OpenAI models: {e}", err=True)
            return []


def test_openai_connection(api_key: Optional[str] = None, org_id: Optional[str] = None) -> bool:
    """Test OpenAI API connection"""
    
    try:
        client = OpenAIClient(api_key, org_id)
        
        # Try to fetch models to test connection
        models = client.fetch_models()
        
        if models:
            click.echo(f"[OPENAI] Connection successful! Found {len(models)} available models.")
            return True
        else:
            click.echo("[OPENAI] Connection works but no models found.")
            return True
        
    except Exception as e:
        click.echo(f"[ERROR] OpenAI connection failed: {e}", err=True)
        return False
