import pytest
from datetime import datetime, timedelta, timezone
from crashlens.detectors.retry_loops import RetryLoopDetector

# ---------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------

BASE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

def make_record(prompt, model, offset_s=0, prompt_tokens=10, completion_tokens=5):
    """Creates deterministic log record."""
    ts = BASE + timedelta(seconds=offset_s)
    return {
        "prompt": prompt,
        "model": model,
        "startTime": ts.isoformat().replace("+00:00", "Z"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

# ---------------------------------------------------------------------
# Core retry detection behavior
# ---------------------------------------------------------------------

def test_detects_retry_loop_basic():
    records = [
        make_record("Hello", "gpt-4", 0),
        make_record("Hello", "gpt-4", 5),
        make_record("Hello", "gpt-4", 10),
        make_record("Hello", "gpt-4", 15),
    ]
    traces = {"traceA": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)

    assert len(detections) == 1
    det = detections[0]
    assert det["type"] == "retry_loop"
    assert det["retry_count"] == 4
    assert det["trace_id"] == "traceA"
    assert det["has_exponential_backoff"] is False


def test_no_retry_when_prompts_differ():
    records = [
        make_record("A", "gpt-4", 0),
        make_record("B", "gpt-4", 5),
        make_record("C", "gpt-4", 10),
    ]
    traces = {"traceB": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)
    assert detections == []


def test_out_of_order_timestamps_still_detected():
    records = [
        make_record("retry", "gpt-4", 20),
        make_record("retry", "gpt-4", 0),
        make_record("retry", "gpt-4", 10),
    ]
    traces = {"traceC": records}
    detector = RetryLoopDetector(max_retries=1)
    detections = detector.detect(traces)
    assert len(detections) == 1
    assert detections[0]["retry_count"] == 3


def test_long_intervals_do_not_trigger_retry():
    records = [
        make_record("Hello", "gpt-4", 0),
        make_record("Hello", "gpt-4", 600),
        make_record("Hello", "gpt-4", 1200),
    ]
    traces = {"traceD": records}
    detector = RetryLoopDetector(max_retry_interval_minutes=2)
    detections = detector.detect(traces)
    assert detections == []


# ---------------------------------------------------------------------
# Exponential backoff detection
# ---------------------------------------------------------------------

@pytest.mark.parametrize("offsets, expected", [
    ([0, 1, 3, 7], True),   # 1,2,4s pattern
    ([0, 1, 3, 6], False),  # breaks doubling
])
def test_exponential_backoff_detection(offsets, expected):
    records = [make_record("exp", "gpt-4", o) for o in offsets]
    detector = RetryLoopDetector()
    result = detector._is_exponential_backoff(records)
    assert result is expected


def test_detect_flags_exponential_backoff_true():
    records = [
        make_record("exp", "gpt-4", 0),
        make_record("exp", "gpt-4", 1),
        make_record("exp", "gpt-4", 3),
        make_record("exp", "gpt-4", 7),
    ]
    traces = {"traceE": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)

    assert len(detections) == 1
    det = detections[0]
    assert det["has_exponential_backoff"] is True
    assert "description" in det


# ---------------------------------------------------------------------
# Model escalation & boundary testing
# ---------------------------------------------------------------------

def test_model_escalation_not_counted_as_retry():
    records = [
        make_record("same task", "gpt-4", 0),
        make_record("same task", "gpt-4-turbo", 2),
        make_record("same task", "gpt-4", 4),
    ]
    traces = {"traceF": records}
    detector = RetryLoopDetector(max_retries=1)
    detections = detector.detect(traces)
    assert detections == []


@pytest.mark.parametrize("count, should_detect", [
    (2, False),
    (3, True),
])
def test_retry_threshold_boundary(count, should_detect):
    records = [make_record("limit", "gpt-4", i * 2) for i in range(count)]
    traces = {"traceG": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)
    assert bool(detections) is should_detect


def test_retry_description_contains_core_details():
    records = [
        make_record("Hello", "gpt-4", 0),
        make_record("Hello", "gpt-4", 1),
        make_record("Hello", "gpt-4", 2),
        make_record("Hello", "gpt-4", 3),
    ]
    traces = {"traceH": records}
    detector = RetryLoopDetector(max_retries=2)
    detections = detector.detect(traces)
    desc = detections[0]["description"]
    for key in ["retry", "trace", "count"]:
        assert key in desc.lower()
