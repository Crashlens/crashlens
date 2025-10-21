import pytest
from datetime import datetime, timedelta
from crashlens.detectors.retry_loops import RetryLoopDetector

def make_record(prompt, model, start_time, prompt_tokens=10, completion_tokens=5):
    """Helper to create fake trace records."""
    return {
        "prompt": prompt,
        "model": model,
        "startTime": start_time.isoformat() + "Z",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

def test_basic_retry_detection():
    now = datetime.utcnow()
    records = [
        make_record("Hello", "gpt-4", now),
        make_record("Hello", "gpt-4", now + timedelta(seconds=10)),
        make_record("Hello", "gpt-4", now + timedelta(seconds=20)),
        make_record("Hello", "gpt-4", now + timedelta(seconds=30)),
    ]

    traces = {"traceA": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)

    assert len(detections) == 1
    det = detections[0]
    assert det["type"] == "retry_loop"
    assert det["retry_count"] == 4
    assert "Retry loop detected" in det["description"]

def test_no_retry_when_prompts_differ():
    now = datetime.utcnow()
    records = [
        make_record("A", "gpt-4", now),
        make_record("B", "gpt-4", now + timedelta(seconds=5)),
        make_record("C", "gpt-4", now + timedelta(seconds=10)),
    ]
    traces = {"traceB": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)

    assert len(detections) == 0

def test_exponential_backoff_true():
    now = datetime.utcnow()
    # intervals: 1s, 2s, 4s → exponential
    records = [
        make_record("retry", "gpt-4", now),
        make_record("retry", "gpt-4", now + timedelta(seconds=1)),
        make_record("retry", "gpt-4", now + timedelta(seconds=3)),
        make_record("retry", "gpt-4", now + timedelta(seconds=7)),
    ]
    detector = RetryLoopDetector()
    assert detector._is_exponential_backoff(records) is True

def test_exponential_backoff_false():
    now = datetime.utcnow()
    # intervals: 1s, 2s, 3s → not exponential
    records = [
        make_record("retry", "gpt-4", now),
        make_record("retry", "gpt-4", now + timedelta(seconds=1)),
        make_record("retry", "gpt-4", now + timedelta(seconds=3)),
        make_record("retry", "gpt-4", now + timedelta(seconds=6)),
    ]
    detector = RetryLoopDetector()
    assert detector._is_exponential_backoff(records) is False

def test_detect_includes_exponential_flag():
    now = datetime.utcnow()
    records = [
        make_record("exp", "gpt-4", now),
        make_record("exp", "gpt-4", now + timedelta(seconds=1)),
        make_record("exp", "gpt-4", now + timedelta(seconds=3)),
        make_record("exp", "gpt-4", now + timedelta(seconds=7)),
    ]
    traces = {"traceC": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)

    assert len(detections) == 1
    det = detections[0]
    assert "has_exponential_backoff" in det
    assert det["has_exponential_backoff"] is True

def test_invalid_retry_loop_due_to_long_interval():
    now = datetime.utcnow()
    records = [
        make_record("retry", "gpt-4", now),
        make_record("retry", "gpt-4", now + timedelta(minutes=10)),
        make_record("retry", "gpt-4", now + timedelta(minutes=20)),
    ]
    traces = {"traceD": records}
    detector = RetryLoopDetector(max_retry_interval_minutes=2)
    detections = detector.detect(traces)
    assert len(detections) == 0

