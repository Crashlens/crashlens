#!/usr/bin/env python3
"""Generate large test file for performance benchmarking.

Creates 100,000 realistic trace records for CrashLens scanning.
Target: 5+ second baseline scan time.
"""

import json
import random
import argparse
from datetime import datetime, timedelta


def generate_realistic_trace(trace_id: int) -> dict:
    """Generate a single realistic trace record."""
    
    # Random timestamps over past 24 hours
    now = datetime.now()
    start_time = now - timedelta(hours=random.randint(0, 24))
    end_time = start_time + timedelta(seconds=random.uniform(0.1, 30.0))
    
    # Realistic model distributions
    models = [
        "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
        "claude-3-opus", "claude-3-sonnet",
        "gemini-pro", "llama-2-70b"
    ]
    
    # Realistic status codes
    statuses = ["success"] * 85 + ["error"] * 10 + ["timeout"] * 5
    
    # Realistic token distributions (log-normal)
    prompt_tokens = int(random.lognormvariate(6, 1.5))  # Mean ~400, tail to 10k
    completion_tokens = int(random.lognormvariate(5, 1.2))  # Mean ~150, tail to 5k
    
    # Realistic error patterns
    if random.choice(statuses) == "error":
        error_type = random.choice([
            "rate_limit_exceeded",
            "context_length_exceeded",
            "invalid_request",
            "timeout",
            "model_overloaded"
        ])
    else:
        error_type = None
    
    # Build trace with Langfuse-compliant schema structure
    model_name = random.choice(models)
    trace = {
        "traceId": f"trace_{trace_id:06d}",
        "timestamp": start_time.isoformat(),
        "end_timestamp": end_time.isoformat(),
        "status": random.choice(statuses),
        "input": {
            "model": model_name,
            "prompt": f"This is test prompt {trace_id}"
        },
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        },
        "latency_ms": (end_time - start_time).total_seconds() * 1000,
        "cost_usd": (prompt_tokens * 0.00003) + (completion_tokens * 0.00006),
        "user_id": f"user_{random.randint(1, 100)}",
        "session_id": f"session_{random.randint(1, 1000)}",
    }
    
    if error_type:
        trace["error_type"] = error_type
    
    # Add metadata for policy evaluation
    trace["metadata"] = {
        "retry_count": random.randint(0, 5) if error_type else 0,
        "cache_hit": random.choice([True, False]),
        "region": random.choice(["us-east-1", "eu-west-1", "ap-south-1"])
    }
    
    return trace


def generate_test_file(num_traces: int, output_file: str):
    """Generate test file with specified number of traces."""
    
    print(f"Generating {num_traces:,} traces...")
    
    with open(output_file, 'w') as f:
        for i in range(num_traces):
            trace = generate_realistic_trace(i)
            f.write(json.dumps(trace) + '\n')
            
            # Progress indicator
            if (i + 1) % 10000 == 0:
                print(f"  {i + 1:,} traces written...")
    
    print(f"✓ Complete: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate large test file for benchmarking"
    )
    parser.add_argument(
        "--traces",
        type=int,
        default=100000,
        help="Number of traces to generate (default: 100,000)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="large-test.jsonl",
        help="Output file path (default: large-test.jsonl)"
    )
    
    args = parser.parse_args()
    
    generate_test_file(args.traces, args.output)
