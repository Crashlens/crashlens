"""
Demo script for retry quality scoring system
"""
from crashlens.detectors.retry_loops import RetryLoopDetector
from datetime import datetime, timedelta


def create_worst_case_trace():
    """Worst case: Fixed intervals, many retries, errors, tight loop"""
    base_time = datetime.fromisoformat('2024-01-01T10:00:00+00:00')
    return [
        {
            'startTime': (base_time + timedelta(seconds=i*2)).isoformat().replace('+00:00', 'Z'),
            'prompt': 'Generate a summary',
            'model': 'gpt-4',
            'completion_tokens': 5,  # Small/error responses
            'prompt_tokens': 100,
            'cost': 0.01
        }
        for i in range(8)
    ]


def create_best_case_trace():
    """Best case: Exponential backoff, few retries, normal responses"""
    base_time = datetime.fromisoformat('2024-01-01T10:00:00+00:00')
    intervals = [0, 15, 45, 90]  # Cumulative: 0, 15, 45, 90 seconds
    return [
        {
            'startTime': (base_time + timedelta(seconds=intervals[i])).isoformat().replace('+00:00', 'Z'),
            'prompt': 'Generate a report',
            'model': 'gpt-4',
            'completion_tokens': 100,  # Normal responses
            'prompt_tokens': 100,
            'cost': 0.01
        }
        for i in range(4)
    ]


def create_medium_case_trace():
    """Medium case: No backoff, moderate retries, quick loop"""
    base_time = datetime.fromisoformat('2024-01-01T10:00:00+00:00')
    return [
        {
            'startTime': (base_time + timedelta(seconds=i*8)).isoformat().replace('+00:00', 'Z'),
            'prompt': 'Analyze data',
            'model': 'gpt-4',
            'completion_tokens': 80,  # Normal responses
            'prompt_tokens': 100,
            'cost': 0.01
        }
        for i in range(6)
    ]


def main():
    detector = RetryLoopDetector(max_retries=3)
    
    traces = {
        'trace-worst': create_worst_case_trace(),
        'trace-best': create_best_case_trace(),
        'trace-medium': create_medium_case_trace(),
    }
    
    detections = detector.detect(traces)
    
    print("\n" + "="*70)
    print("🎯 RETRY QUALITY SCORING DEMO")
    print("="*70 + "\n")
    
    # Sort by quality score (worst first)
    detections.sort(key=lambda d: d['quality_score'], reverse=True)
    
    for i, detection in enumerate(detections, 1):
        severity_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }[detection['severity']]
        
        print(f"{i}. Trace: {detection['trace_id']}")
        print(f"   Severity: {severity_emoji} {detection['severity'].upper()}")
        print(f"   Quality Score: {detection['quality_score']}/100 {'(WORST!)' if detection['quality_score'] == 100 else '(BEST!)' if detection['quality_score'] <= 15 else ''}")
        print(f"   Retries: {detection['retry_count']}")
        print(f"   Time span: {detection['time_span']}")
        print(f"   Model: {detection['model']}")
        print(f"   Exponential backoff: {'✅ Yes' if detection['has_exponential_backoff'] else '❌ No'}")
        print(f"   Small responses: {'✅ Yes (errors)' if detection['has_small_responses'] else '❌ No'}")
        print(f"   Waste: {detection['waste_tokens']} tokens, ${detection['waste_cost']:.4f}")
        
        # Show score breakdown
        print("\n   📊 Score Breakdown:")
        score = 0
        if detection['has_exponential_backoff']:
            print(f"      • Exponential backoff: +15 (still wasteful)")
            score += 15
        else:
            print(f"      • No backoff: +30")
            score += 30
        
        if detection['has_small_responses']:
            print(f"      • Small/error responses: +25")
            score += 25
        
        if detection['retry_count'] > 7:
            print(f"      • Many retries (>7): +25")
            score += 25
        elif detection['retry_count'] > 5:
            print(f"      • Moderate retries (>5): +15")
            score += 15
        
        time_span = float(detection['time_span'].replace(' seconds', ''))
        if time_span < 30:
            print(f"      • Tight loop (<30s): +20")
            score += 20
        elif time_span < 60:
            print(f"      • Quick loop (<60s): +15")
            score += 15
        
        print(f"      = Total: {min(score, 100)}/100")
        
        # Recommendations
        print("\n   💡 Recommendations:")
        if not detection['has_exponential_backoff']:
            print(f"      • Implement exponential backoff (saves 15 points)")
        if detection['has_small_responses']:
            print(f"      • Investigate root cause of errors (saves 25 points)")
        if detection['retry_count'] > 7:
            print(f"      • Add circuit breaker (saves 25 points)")
        elif detection['retry_count'] > 5:
            print(f"      • Reduce max retries (saves 15 points)")
        if time_span < 30:
            print(f"      • Increase retry intervals to >30s (saves 20 points)")
        elif time_span < 60:
            print(f"      • Increase retry intervals to >60s (saves 15 points)")
        
        print("\n" + "-"*70 + "\n")
    
    print("="*70)
    print("✅ Demo complete! Quality scoring provides nuanced severity assessment.")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
