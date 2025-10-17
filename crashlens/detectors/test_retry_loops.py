from datetime import datetime, timedelta
from .retry_loops import RetryLoopDetector  # Use relative import if inside package


def _make_record(prompt, model, time, pt=10, ct=5):
    return {
        "prompt": prompt,
        "model": model,
        "startTime": time.isoformat() + "Z",
        "prompt_tokens": pt,
        "completion_tokens": ct,
    }


def test_detect_simple_retry_loop():
    now = datetime.utcnow()
    traces = {
        "trace_1": [
            _make_record("Prompt A", "gpt-4", now),
            _make_record("Prompt A", "gpt-4", now + timedelta(seconds=1)),
            _make_record("Prompt A", "gpt-4", now + timedelta(seconds=2)),
            _make_record("Prompt A", "gpt-4", now + timedelta(seconds=3)),
        ]
    }
    detector = RetryLoopDetector(max_retries=2)
    results = detector.detect(traces)
    assert len(results) == 1
    assert results[0]["retry_count"] == 4


def test_no_retry_loop_when_prompts_differ():
    now = datetime.utcnow()
    traces = {
        "trace_diff": [
            _make_record("Prompt X", "gpt-4", now),
            _make_record("Prompt Y", "gpt-4", now + timedelta(seconds=1)),
        ]
    }
    detector = RetryLoopDetector()
    results = detector.detect(traces)
    assert len(results) == 0


def test_exponential_backoff_detection():
    detector = RetryLoopDetector(max_retries=2)
    now = datetime.utcnow()
    traces = {
        "trace_2": [
            _make_record("Prompt X", "gpt-4", now),
            _make_record("Prompt X", "gpt-4", now + timedelta(seconds=1)),
            _make_record("Prompt X", "gpt-4", now + timedelta(seconds=2)),
            _make_record("Prompt X", "gpt-4", now + timedelta(seconds=4)),
            _make_record("Prompt X", "gpt-4", now + timedelta(seconds=8)),
        ]
    }

    results = detector.detect(traces)
    assert len(results) == 1
    det = results[0]
    assert det["has_exponential_backoff"] is True
    assert det["severity"] in ("low", "medium")


def test_exponential_backoff_plateau():
    """Should detect exponential backoff even if final intervals plateau."""
    detector = RetryLoopDetector()
    now = datetime.utcnow()
    traces = {
        "trace_plateau": [
            _make_record("A", "gpt-4", now),
            _make_record("A", "gpt-4", now + timedelta(seconds=1)),
            _make_record("A", "gpt-4", now + timedelta(seconds=3)),  # 2s
            _make_record("A", "gpt-4", now + timedelta(seconds=7)),  # 4s
            _make_record("A", "gpt-4", now + timedelta(seconds=39)), # 32s
            _make_record("A", "gpt-4", now + timedelta(seconds=71)), # 32s
        ]
    }
    result = detector.detect(traces)
    assert result[0]["has_exponential_backoff"] is True


def test_zero_interval_handling():
    """Ensure zero-interval calls do not crash the detector."""
    detector = RetryLoopDetector()
    now = datetime.utcnow()
    traces = {
        "trace_zero": [
            _make_record("P", "gpt-4", now),
            _make_record("P", "gpt-4", now),  # zero gap
            _make_record("P", "gpt-4", now + timedelta(seconds=1)),
            _make_record("P", "gpt-4", now + timedelta(seconds=2)),
        ]
    }
    result = detector.detect(traces)
    assert len(result) == 1


def test_ignores_traces_with_too_few_records():
    now = datetime.utcnow()
    traces = {
        "short": [
            _make_record("Q", "gpt-4", now),
            _make_record("Q", "gpt-4", now + timedelta(seconds=1)),
        ]
    }
    detector = RetryLoopDetector(max_retries=3)
    assert detector.detect(traces) == []


def test_cost_calculation_with_model_pricing():
    now = datetime.utcnow()
    traces = {
        "trace_cost": [
            _make_record("T", "gpt-4", now, pt=100, ct=50),
            _make_record("T", "gpt-4", now + timedelta(seconds=1), pt=120, ct=60),
            _make_record("T", "gpt-4", now + timedelta(seconds=2), pt=110, ct=55),
            _make_record("T", "gpt-4", now + timedelta(seconds=3), pt=130, ct=65),
        ]
    }
    pricing = {"gpt-4": {"input_cost_per_1k": 0.01, "output_cost_per_1k": 0.03}}
    detector = RetryLoopDetector(max_retries=2)
    result = detector.detect(traces, model_pricing=pricing)

    # Total cost calculation:
    # (100/1000*0.01 + 50/1000*0.03) + ...
    total_expected = 0.0025 + 0.003 + 0.00275 + 0.00325
    assert result[0]["waste_cost"] > 0.0
    assert abs(result[0]["waste_cost"] - total_expected) < 1e-8


def test_invalid_retry_loop_due_to_time_gap():
    now = datetime.utcnow()
    traces = {
        "trace_gap": [
            _make_record("Prompt Z", "gpt-4", now),
            _make_record("Prompt Z", "gpt-4", now + timedelta(minutes=10)),
        ]
    }
    detector = RetryLoopDetector()
    results = detector.detect(traces)
    assert len(results) == 0
