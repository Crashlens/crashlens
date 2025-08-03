#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crashlens.detectors.retry_fallback_detector import RetryFallbackDetector
from datetime import datetime, timedelta
import json

def test_retry_fallback_detector():
    """Test the new RetryFallbackDetector with various scenarios."""
    print("=== Testing RetryFallbackDetector ===")
    
    # Create detector with verbose logging
    detector = RetryFallbackDetector(verbose=True)
    
    # Test Case 1: Retry loop detection
    print("\n1. Testing retry loop detection:")
    
    base_time = datetime.now()
    retry_traces = {
        "trace1": [
            {
                "id": "call1",
                "startTime": base_time.isoformat(),
                "prompt": "What is the capital of France?",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 0.001
            },
            {
                "id": "call2", 
                "startTime": (base_time + timedelta(seconds=1)).isoformat(),
                "prompt": "What is the capital of France?",  # Same prompt
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 0.001
            },
            {
                "id": "call3",
                "startTime": (base_time + timedelta(seconds=1.5)).isoformat(),
                "prompt": "What is the capital of France?",  # Same prompt again
                "model": "gpt-3.5-turbo", 
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 0.001
            },
            {
                "id": "call4",
                "startTime": (base_time + timedelta(seconds=1.8)).isoformat(),
                "prompt": "What is the capital of France?",  # 4th retry
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 0.001
            }
        ]
    }
    
    detections = detector.detect(retry_traces)
    print(f"Found {len(detections)} detections")
    for detection in detections:
        print(f"  - {detection['type']}: {detection['description']}")
        print(f"    Retry count: {detection['details']['retry_count']}")
        print(f"    Waste tokens: {detection['details']['waste_tokens']}")
    
    # Test Case 2: Fallback overuse detection
    print("\n2. Testing fallback overuse detection:")
    
    fallback_traces = {
        "trace2": [
            {
                "id": "call5",
                "startTime": base_time.isoformat(),
                "prompt": "Solve this complex math problem: 2+2",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "cost": 0.002
            },
            {
                "id": "call6",
                "startTime": (base_time + timedelta(seconds=5)).isoformat(),
                "prompt": "Solve this complex math problem: 2+2",  # Same prompt
                "model": "gpt-4",  # Escalated model
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "cost": 0.006
            },
            {
                "id": "call7",
                "startTime": (base_time + timedelta(seconds=10)).isoformat(),
                "prompt": "Solve this complex math problem: 2+2",  # Same prompt
                "model": "gpt-4o",  # Further escalation
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "cost": 0.01
            }
        ]
    }
    
    detections = detector.detect(fallback_traces)
    print(f"Found {len(detections)} detections")
    for detection in detections:
        print(f"  - {detection['type']}: {detection['description']}")
        if 'model_progression' in detection['details']:
            print(f"    Model progression: {' → '.join(detection['details']['model_progression'])}")
        print(f"    Waste cost: ${detection['details']['waste_cost']:.4f}")
    
    # Test Case 3: Out-of-order logs
    print("\n3. Testing out-of-order logs handling:")
    
    out_of_order_traces = {
        "trace3": [
            {
                "id": "call10",
                "startTime": (base_time + timedelta(seconds=1.5)).isoformat(),  # Later timestamp
                "prompt": "Out of order test",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 12,
                "completion_tokens": 6
            },
            {
                "id": "call8",
                "startTime": base_time.isoformat(),  # Earlier timestamp  
                "prompt": "Out of order test",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 12,
                "completion_tokens": 6
            },
            {
                "id": "call9",
                "startTime": (base_time + timedelta(seconds=0.5)).isoformat(),  # Middle timestamp
                "prompt": "Out of order test",
                "model": "gpt-3.5-turbo", 
                "prompt_tokens": 12,
                "completion_tokens": 6
            },
            {
                "id": "call11",
                "startTime": (base_time + timedelta(seconds=1.8)).isoformat(),  # Latest
                "prompt": "Out of order test",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 12,
                "completion_tokens": 6
            }
        ]
    }
    
    detections = detector.detect(out_of_order_traces)
    print(f"Found {len(detections)} detections")
    for detection in detections:
        print(f"  - {detection['type']}: {detection['description']}")
        print(f"    Timestamps properly sequenced: {detection['details']['timestamps'][:2]}...")
    
    # Test Case 4: Mixed patterns
    print("\n4. Testing mixed patterns (retries + fallbacks):")
    
    mixed_traces = {
        "trace4": [
            # Initial call
            {
                "id": "call12",
                "startTime": base_time.isoformat(),
                "prompt": "Complex reasoning task",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 20,
                "completion_tokens": 10
            },
            # Retry with same model
            {
                "id": "call13",
                "startTime": (base_time + timedelta(seconds=1)).isoformat(),
                "prompt": "Complex reasoning task", 
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 20,
                "completion_tokens": 10
            },
            # Fallback to stronger model (within fallback window)
            {
                "id": "call14",
                "startTime": (base_time + timedelta(seconds=3)).isoformat(),
                "prompt": "Complex reasoning task",
                "model": "gpt-4",
                "prompt_tokens": 20,
                "completion_tokens": 10
            }
        ]
    }
    
    detections = detector.detect(mixed_traces)
    print(f"Found {len(detections)} detections")
    for detection in detections:
        print(f"  - {detection['type']}: {detection['description']}")
    
    print("\n=== RetryFallbackDetector Test Complete ===")

if __name__ == "__main__":
    test_retry_fallback_detector()
