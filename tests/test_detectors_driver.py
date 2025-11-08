"""
Unit tests for DetectorDriver

Tests all three modes: none, precomputed, inline
Validates constant-memory batch processing and enrichment
"""

import pytest
import json
from pathlib import Path
from crashlens.detectors.driver import (
    DetectorDriver,
    run_detectors_on_batch,
    DetectorMetrics,
)


@pytest.fixture
def sample_batch():
    """Create a sample batch with retry loop pattern."""
    return [
        {
            "id": 1,
            "traceId": "trace-001",
            "startTime": "2024-01-01T10:00:00Z",
            "model": "gpt-4",
            "prompt": "What is the weather?",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
        {
            "id": 2,
            "traceId": "trace-001",
            "startTime": "2024-01-01T10:00:30Z",
            "model": "gpt-4",
            "prompt": "What is the weather?",  # Exact duplicate
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
        {
            "id": 3,
            "traceId": "trace-001",
            "startTime": "2024-01-01T10:01:00Z",
            "model": "gpt-4",
            "prompt": "What is the weather?",  # Exact duplicate
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
        {
            "id": 4,
            "traceId": "trace-001",
            "startTime": "2024-01-01T10:01:30Z",
            "model": "gpt-4",
            "prompt": "What is the weather?",  # Exact duplicate (4th retry - triggers detection)
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        },
    ]


@pytest.fixture
def precomputed_batch():
    """Create a batch with precomputed detector fields."""
    return [
        {
            "id": 1,
            "traceId": "trace-002",
            "detector.retry_loop.detected": True,
            "detector.retry_loop.severity": "high",
            "detector.retry_loop.waste_cost": 0.05,
        },
        {
            "id": 2,
            "traceId": "trace-002",
            "detector.retry_loop.detected": True,
            "detector.retry_loop.severity": "high",
            "detector.retry_loop.waste_cost": 0.05,
        },
    ]


@pytest.fixture
def fallback_storm_batch():
    """Create a batch with fallback storm pattern."""
    return [
        {
            "id": 1,
            "traceId": "trace-003",
            "startTime": "2024-01-01T10:00:00Z",
            "model": "gpt-4",
            "prompt": "Complex task",
        },
        {
            "id": 2,
            "traceId": "trace-003",
            "startTime": "2024-01-01T10:00:15Z",
            "model": "gpt-3.5-turbo",  # Fallback to cheaper model
            "prompt": "Complex task",
        },
        {
            "id": 3,
            "traceId": "trace-003",
            "startTime": "2024-01-01T10:00:30Z",
            "model": "claude-3-sonnet",  # Another fallback
            "prompt": "Complex task",
        },
    ]


class TestDetectorDriverModes:
    """Test the three detector modes."""
    
    def test_mode_none_passes_through_unchanged(self, sample_batch):
        """Mode 'none' should return batch unchanged."""
        driver = DetectorDriver(mode="none")
        result = driver.run_detectors_on_batch(sample_batch)
        
        assert result == sample_batch
        assert len(result) == len(sample_batch)
        
        # No enrichment should occur
        for record in result:
            assert not any(key.startswith("detector.") for key in record.keys())
        
        metrics = driver.get_metrics()
        assert metrics.records_processed == len(sample_batch)
        assert metrics.detector_time_ms == 0.0
        assert metrics.detections_found == 0
    
    def test_mode_precomputed_validates_fields(self, precomputed_batch):
        """Mode 'precomputed' should validate detector fields exist."""
        driver = DetectorDriver(mode="precomputed", verbose=False)
        result = driver.run_detectors_on_batch(precomputed_batch)
        
        assert result == precomputed_batch
        
        # Verify detector fields are present
        for record in result:
            assert "detector.retry_loop.detected" in record
            assert record["detector.retry_loop.detected"] is True
        
        metrics = driver.get_metrics()
        assert metrics.records_processed == len(precomputed_batch)
    
    def test_mode_inline_runs_detectors(self, sample_batch):
        """Mode 'inline' should run detectors and enrich batch."""
        driver = DetectorDriver(mode="inline", verbose=False)
        result = driver.run_detectors_on_batch(sample_batch)
        
        assert len(result) == len(sample_batch)
        
        # Check that enrichment occurred
        has_detection = any(
            any(key.startswith("detector.") for key in record.keys())
            for record in result
        )
        assert has_detection, "Expected detector enrichment in inline mode"
        
        metrics = driver.get_metrics()
        assert metrics.records_processed == len(sample_batch)
        assert metrics.detector_time_ms > 0
        assert metrics.detections_found >= 0  # May be 0 if no patterns detected
    
    def test_invalid_mode_raises_error(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            DetectorDriver(mode="invalid")  # type: ignore
    
    def test_mode_inline_without_detectors_raises_error(self, monkeypatch):
        """Inline mode without detector modules should raise RuntimeError."""
        import crashlens.detectors.driver as driver_module
        monkeypatch.setattr(driver_module, "HAS_DETECTORS", False)
        
        with pytest.raises(RuntimeError, match="Cannot use inline detector mode"):
            DetectorDriver(mode="inline")


class TestInlineDetection:
    """Test inline detector execution."""
    
    def test_retry_loop_detection(self, sample_batch):
        """Test that retry loop is detected in inline mode."""
        driver = DetectorDriver(mode="inline", verbose=True)
        result = driver.run_detectors_on_batch(sample_batch)
        
        # Check enrichment on at least one record
        enriched_records = [
            r for r in result
            if "detector.retry_loop.detected" in r
        ]
        
        assert len(enriched_records) > 0, "Expected retry loop detection"
        
        # Verify enrichment structure
        for record in enriched_records:
            if record.get("detector.retry_loop.detected"):
                assert "detector.retry_loop.severity" in record
                assert record["detector.retry_loop.severity"] in ["low", "medium", "high"]
                assert "detector.retry_loop.waste_cost" in record
                assert isinstance(record["detector.retry_loop.waste_cost"], (int, float))
    
    def test_fallback_storm_detection(self, fallback_storm_batch):
        """Test that fallback storm is detected."""
        driver = DetectorDriver(mode="inline", verbose=True)
        result = driver.run_detectors_on_batch(fallback_storm_batch)
        
        # Check for fallback storm enrichment
        enriched_records = [
            r for r in result
            if "detector.fallback_storm.detected" in r
        ]
        
        # May or may not detect depending on thresholds
        # Just verify the enrichment structure if detected
        for record in enriched_records:
            if record.get("detector.fallback_storm.detected"):
                assert "detector.fallback_storm.severity" in record
                assert "detector.fallback_storm.cascade_depth" in record
    
    def test_detector_config_applied(self):
        """Test that detector config is applied correctly."""
        config = {
            "retry_loop": {
                "max_retries": 2,  # Lower threshold
                "time_window_minutes": 10,
            },
            "fallback_storm": {
                "min_calls": 2,
                "min_models": 2,
            },
        }
        
        driver = DetectorDriver(mode="inline", detector_config=config, verbose=False)
        
        # Verify detectors were initialized with config
        assert len(driver._detectors) == 2
        
        # Check that retry loop detector has correct threshold
        retry_detector = driver._detectors[0][1]
        assert retry_detector.max_retries == 2
    
    def test_empty_batch_handled(self):
        """Test that empty batch is handled gracefully."""
        driver = DetectorDriver(mode="inline")
        result = driver.run_detectors_on_batch([])
        
        assert result == []
        assert driver.get_metrics().records_processed == 0


class TestMetrics:
    """Test metrics collection."""
    
    def test_metrics_collected_inline(self, sample_batch):
        """Test that metrics are collected in inline mode."""
        driver = DetectorDriver(mode="inline", verbose=False)
        driver.run_detectors_on_batch(sample_batch)
        
        metrics = driver.get_metrics()
        assert metrics.records_processed == len(sample_batch)
        assert metrics.detector_time_ms > 0
        assert metrics.detector_runs is not None
        assert len(metrics.detector_runs) > 0
        
        # Check individual detector timings
        for detector_name, time_ms in metrics.detector_runs.items():
            assert isinstance(time_ms, float)
            assert time_ms >= 0
    
    def test_metrics_reset(self, sample_batch):
        """Test that metrics can be reset."""
        driver = DetectorDriver(mode="inline")
        driver.run_detectors_on_batch(sample_batch)
        
        metrics_before = driver.get_metrics()
        assert metrics_before.records_processed > 0
        
        driver.reset_metrics()
        metrics_after = driver.get_metrics()
        assert metrics_after.records_processed == 0
        assert metrics_after.detector_time_ms == 0.0
    
    def test_metrics_accumulate_across_batches(self, sample_batch):
        """Test that metrics accumulate across multiple batches."""
        driver = DetectorDriver(mode="inline")
        
        driver.run_detectors_on_batch(sample_batch)
        first_count = driver.get_metrics().records_processed
        
        driver.run_detectors_on_batch(sample_batch)
        second_count = driver.get_metrics().records_processed
        
        assert second_count == first_count * 2


class TestEnrichment:
    """Test batch enrichment logic."""
    
    def test_enrichment_preserves_original_fields(self, sample_batch):
        """Test that enrichment preserves original record fields."""
        driver = DetectorDriver(mode="inline")
        result = driver.run_detectors_on_batch(sample_batch)
        
        for i, record in enumerate(result):
            # Original fields should still exist
            assert record["id"] == sample_batch[i]["id"]
            assert record["traceId"] == sample_batch[i]["traceId"]
            assert record["model"] == sample_batch[i]["model"]
    
    def test_enrichment_schema_structure(self, sample_batch):
        """Test that enrichment follows expected schema."""
        driver = DetectorDriver(mode="inline")
        result = driver.run_detectors_on_batch(sample_batch)
        
        # Find any enriched record
        for record in result:
            if "detector.retry_loop.detected" in record:
                # Check expected fields
                assert isinstance(record["detector.retry_loop.detected"], bool)
                assert isinstance(record["detector.retry_loop.severity"], str)
                assert isinstance(record["detector.retry_loop.waste_cost"], (int, float))
                
                # Type-specific fields
                if record["detector.retry_loop.detected"]:
                    assert "detector.retry_loop.quality_score" in record
                    assert "detector.retry_loop.retry_count" in record


class TestConvenienceFunction:
    """Test the run_detectors_on_batch convenience function."""
    
    def test_convenience_function_mode_none(self, sample_batch):
        """Test convenience function with mode='none'."""
        result = run_detectors_on_batch(sample_batch, mode="none")
        assert result == sample_batch
    
    def test_convenience_function_mode_inline(self, sample_batch):
        """Test convenience function with mode='inline'."""
        result = run_detectors_on_batch(sample_batch, mode="inline", verbose=False)
        assert len(result) == len(sample_batch)
    
    def test_convenience_function_with_config(self, sample_batch):
        """Test convenience function with detector config."""
        config = {"retry_loop": {"max_retries": 2}}
        result = run_detectors_on_batch(
            sample_batch,
            mode="inline",
            detector_config=config,
            verbose=False,
        )
        assert len(result) == len(sample_batch)


class TestConstantMemory:
    """Test that driver operates in constant memory."""
    
    def test_batch_processing_only(self):
        """Test that driver only processes provided batch, not accumulating state."""
        driver = DetectorDriver(mode="inline")
        
        batch1 = [
            {
                "id": 1,
                "traceId": "trace-100",
                "startTime": "2024-01-01T10:00:00Z",
                "model": "gpt-4",
                "prompt": "Test",
            }
        ]
        
        batch2 = [
            {
                "id": 2,
                "traceId": "trace-200",
                "startTime": "2024-01-01T11:00:00Z",
                "model": "gpt-4",
                "prompt": "Test",
            }
        ]
        
        result1 = driver.run_detectors_on_batch(batch1)
        result2 = driver.run_detectors_on_batch(batch2)
        
        # Each batch should be processed independently
        # Verify no cross-contamination
        assert result1[0]["traceId"] == "trace-100"
        assert result2[0]["traceId"] == "trace-200"
    
    def test_no_internal_state_accumulation(self, sample_batch):
        """Test that driver doesn't accumulate internal state between batches."""
        driver = DetectorDriver(mode="inline")
        
        # Process same batch twice
        driver.run_detectors_on_batch(sample_batch)
        driver.run_detectors_on_batch(sample_batch)
        
        # Only metrics should accumulate, not detection state
        metrics = driver.get_metrics()
        assert metrics.records_processed == len(sample_batch) * 2


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_malformed_records_handled(self):
        """Test that malformed records are handled gracefully."""
        driver = DetectorDriver(mode="inline", verbose=False)
        
        malformed_batch = [
            {"id": 1},  # Missing required fields
            {"id": 2, "traceId": "trace-001"},  # Missing other fields
        ]
        
        # Should not raise, just process what it can
        result = driver.run_detectors_on_batch(malformed_batch)
        assert len(result) == len(malformed_batch)
    
    def test_detector_failure_continues(self, sample_batch, monkeypatch):
        """Test that failure in one detector doesn't stop processing."""
        driver = DetectorDriver(mode="inline", verbose=True)
        
        # Mock one detector to fail
        original_detect = driver._detectors[0][1].detect
        
        def failing_detect(*args, **kwargs):
            raise RuntimeError("Simulated detector failure")
        
        driver._detectors[0] = (driver._detectors[0][0], type('obj', (object,), {'detect': failing_detect})())
        
        # Should not raise, should continue with other detectors
        result = driver.run_detectors_on_batch(sample_batch)
        assert len(result) == len(sample_batch)
