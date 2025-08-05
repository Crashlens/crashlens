#!/usr/bin/env python3
"""
Helicone API Client for CrashLens
Fetches request logs from Helicone and converts them to CrashLens-compatible format.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import click
from pathlib import Path


class HeliconeClient:
    """Client for fetching request logs from Helicone API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Helicone client
        
        Args:
            api_key: Helicone API key (or from HELICONE_API_KEY env var)
            base_url: Helicone API base URL (defaults to production)
        """
        self.api_key = api_key or os.getenv('HELICONE_API_KEY')
        self.base_url = (base_url or 'https://api.hconeai.com').rstrip('/')
        
        if not self.api_key:
            raise ValueError(
                "Helicone API key required. Set HELICONE_API_KEY environment variable "
                "or pass it directly."
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'CrashLens/2.0'
        })
    
    def fetch_requests(self, hours_back: int = 24, limit: int = 1000, 
                      page_size: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch request logs from Helicone API
        
        Args:
            hours_back: Number of hours back to fetch requests (default: 24)
            limit: Maximum number of requests to fetch (default: 1000)
            page_size: Number of requests per API request (default: 50)
            
        Returns:
            List of request dictionaries from Helicone API
        """
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        click.echo(f"[HELICONE] Fetching requests from {start_time.strftime('%Y-%m-%d %H:%M')} "
                  f"to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
        
        all_requests = []
        offset = 0
        
        while len(all_requests) < limit:
            try:
                # Build API request
                params = {
                    'offset': offset,
                    'limit': min(page_size, limit - len(all_requests)),
                    'start_date': start_time.isoformat(),
                    'end_date': end_time.isoformat(),
                    'sort_by': 'created_at',
                    'sort_order': 'desc'
                }
                
                click.echo(f"[HELICONE] Fetching page {offset // page_size + 1} "
                          f"(up to {params['limit']} requests)...")
                
                response = self.session.get(f"{self.base_url}/v1/request", params=params)
                response.raise_for_status()
                
                data = response.json()
                requests_data = data.get('data', [])
                
                if not requests_data:
                    click.echo("[HELICONE] No more requests found")
                    break
                
                all_requests.extend(requests_data)
                click.echo(f"[HELICONE] Fetched {len(requests_data)} requests "
                          f"(total: {len(all_requests)})")
                
                # Check if we've reached the end
                if len(requests_data) < page_size:
                    break
                    
                offset += page_size
                
            except requests.exceptions.RequestException as e:
                click.echo(f"[ERROR] Error fetching requests: {e}", err=True)
                if hasattr(e, 'response') and e.response is not None:
                    click.echo(f"   Response: {e.response.text}", err=True)
                break
        
        click.echo(f"[HELICONE] Successfully fetched {len(all_requests)} requests")
        return all_requests
    
    def convert_to_crashlens_format(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Helicone requests to CrashLens-compatible JSONL format
        
        Args:
            requests: List of Helicone request objects
            
        Returns:
            List of CrashLens-compatible log entries
        """
        click.echo(f"[HELICONE] Converting {len(requests)} requests to CrashLens format...")
        
        crashlens_logs = []
        
        for i, request in enumerate(requests):
            try:
                if (i + 1) % 10 == 0:
                    click.echo(f"   Processing request {i + 1}/{len(requests)}...")
                
                log_entry = self._convert_request_to_log_entry(request)
                if log_entry:
                    crashlens_logs.append(log_entry)
                        
            except Exception as e:
                click.echo(f"[WARNING] Error processing request {request.get('id', 'unknown')}: {e}", err=True)
                continue
        
        click.echo(f"[HELICONE] Converted to {len(crashlens_logs)} CrashLens log entries")
        return crashlens_logs
    
    def _convert_request_to_log_entry(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a Helicone request to CrashLens log entry format"""
        
        try:
            # Extract basic info
            request_id = request.get('id')
            created_at = request.get('created_at')
            
            # Extract model and provider info
            request_body = request.get('request_body', {})
            response_body = request.get('response_body', {})
            
            model = request_body.get('model', 'unknown')
            
            # Extract usage/token info
            usage = response_body.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
            
            # Extract messages and response
            messages = request_body.get('messages', [])
            choices = response_body.get('choices', [])
            content = ""
            if choices and len(choices) > 0:
                message = choices[0].get('message', {})
                content = message.get('content', '')
            
            # Extract cost information
            cost_usd = request.get('cost_usd', 0.0)
            
            # Extract provider and additional metadata
            provider = request.get('provider', 'unknown')
            user_id = request.get('user_id')
            
            # Build CrashLens format
            log_entry = {
                'trace_id': request_id,
                'request_id': request_id,
                'timestamp': created_at,
                'input': {
                    'model': model,
                    'messages': messages,
                },
                'output': {
                    'content': content,
                    'choices': choices
                },
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens
                },
                'cost': cost_usd,
                'metadata': {
                    'provider': provider,
                    'user_id': user_id,
                    'helicone_request_id': request_id,
                    'request_path': request.get('request_path'),
                    'status_code': request.get('status_code'),
                    'latency_ms': request.get('latency'),
                    'cache_hit': request.get('cache_hit', False)
                }
            }
            
            return log_entry
            
        except Exception as e:
            click.echo(f"[WARNING] Error converting request {request.get('id', 'unknown')}: {e}", err=True)
            return None


def test_helicone_connection(api_key: Optional[str] = None) -> bool:
    """Test Helicone API connection"""
    
    try:
        client = HeliconeClient(api_key)
        
        # Try to fetch just 1 request to test connection
        requests = client.fetch_requests(hours_back=24, limit=1, page_size=1)
        
        click.echo(f"[HELICONE] Connection successful! Found {len(requests)} recent requests.")
        return True
        
    except Exception as e:
        click.echo(f"[ERROR] Helicone connection failed: {e}", err=True)
        return False
