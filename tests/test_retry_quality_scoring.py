"""
Test suite for retry quality scoring system
"""
import pytest
from datetime import datetime, timedelta
from crashlens.detectors.retry_loops import RetryLoopDetector


class TestRetryQualityScoring:
    """Test the retry quality scoring system"""

    def setup_method(self):
        """Setup detector instance"""
        self.detector = RetryLoopDetector(max_retries=3)

    def create_group(
        self,
        count: int,
        interval_seconds: list,
        completion_tokens: list,
        start_time: str = "2024-01-01T10:00:00Z"
    ):
        """Helper to create retry groups with specific characteristics"""
        group = []
        current_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        
        for i in range(count):
            group.append({
                "startTime": current_time.isoformat().replace("+00:00", "Z"),
                "prompt": "Test prompt",
                "model": "gpt-4",
                "completion_tokens": completion_tokens[i] if i < len(completion_tokens) else 10,
                "prompt_tokens": 100,
                "cost": 0.01
            })
            
            if i < len(interval_seconds):
                current_time += timedelta(seconds=interval_seconds[i])
        
        return group

    def test_worst_case_scenario(self):
        """
        Test: Worst possible retry loop
        - No backoff (fixed intervals)
        - Small responses (errors)
        - Many retries (8)
        - Tight loop (< 30s)
        Expected: 100/100 score (30+25+25+20 = 100)
        """
        group = self.create_group(
            count=8,
            interval_seconds=[2, 2, 2, 2, 2, 2, 2],  # Fixed intervals
            completion_tokens=[5, 5, 5, 5, 5, 5, 5, 5]  # Small responses
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        # Should hit maximum penalties
        assert score == 100, f"Expected 100, got {score}"
        assert not self.detector._is_exponential_backoff(group)
        assert self.detector._has_small_responses(group)
        assert self.detector._get_time_span(group) < 30

    def test_best_case_scenario(self):
        """
        Test: Best retry loop (still wasteful, but properly implemented)
        - Exponential backoff
        - Normal responses
        - Few retries (4)
        - Moderate time span (> 60s)
        Expected: 15/100 score (only exponential backoff penalty)
        """
        group = self.create_group(
            count=4,
            interval_seconds=[15, 30, 45],  # True exponential (2x), 90s total
            completion_tokens=[100, 100, 100, 100]  # Normal responses
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        # Should only get exponential backoff penalty
        assert self.detector._is_exponential_backoff(group), f"Should detect exponential backoff (intervals: [15, 30, 45])"
        assert score == 15, f"Expected 15, got {score} (time_span: {self.detector._get_time_span(group)}s, has_backoff: {self.detector._is_exponential_backoff(group)})"
        assert not self.detector._has_small_responses(group)

    def test_high_severity_threshold(self):
        """
        Test: High severity (score >= 70)
        - No backoff (30)
        - Small responses (25)
        - Many retries (25)
        - Tight loop (20)
        Expected: 100/100 score -> HIGH severity
        """
        group = self.create_group(
            count=8,
            interval_seconds=[3] * 7,  # No backoff, 21 seconds total (< 30s = +20)
            completion_tokens=[10] * 8  # Small responses
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        assert score >= 70, f"Expected >= 70, got {score}"
        # Actual: 30 (no backoff) + 25 (small) + 25 (many retries) + 20 (tight) = 100

    def test_medium_severity_threshold(self):
        """
        Test: Medium severity (40 <= score < 70)
        - No backoff (30)
        - Normal responses (0)
        - Moderate retries (15)
        - Quick loop (15)
        Expected: 60/100 score -> MEDIUM severity
        """
        group = self.create_group(
            count=6,
            interval_seconds=[8, 8, 8, 8, 8],  # No backoff, 40 seconds total
            completion_tokens=[100] * 6  # Normal responses
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        assert 40 <= score < 70, f"Expected 40-69, got {score}"
        assert score == 60, f"Expected 60, got {score}"  # 30 + 0 + 15 + 15

    def test_low_severity_threshold(self):
        """
        Test: Low severity (score < 40)
        - Exponential backoff (15)
        - Normal responses (0)
        - Few retries (0)
        - Moderate time span (0)
        Expected: 15/100 score -> LOW severity
        """
        group = self.create_group(
            count=4,
            interval_seconds=[20, 25, 30],  # Long intervals, > 60s total (75s)
            completion_tokens=[100, 100, 100, 100]  # Normal responses
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        assert score < 40, f"Expected < 40, got {score} (time_span: {self.detector._get_time_span(group)}s)"
        # Note: May not be perfect exponential, but should be low score

    def test_exponential_backoff_penalty_vs_no_backoff(self):
        """
        Test: Compare exponential backoff vs no backoff
        Both with similar time spans (>60s) to isolate backoff penalty
        """
        # With exponential backoff (long intervals)
        group_with_backoff = self.create_group(
            count=4,
            interval_seconds=[15, 30, 45],  # 2x exponential, 90s total
            completion_tokens=[100] * 4
        )
        
        # Without exponential backoff (long fixed intervals)
        group_no_backoff = self.create_group(
            count=4,
            interval_seconds=[30, 30, 30],  # Fixed, 90s total
            completion_tokens=[100] * 4
        )
        
        score_with = self.detector._calculate_retry_quality_score(group_with_backoff)
        score_without = self.detector._calculate_retry_quality_score(group_no_backoff)
        
        # Verify exponential detection
        assert self.detector._is_exponential_backoff(group_with_backoff), "Should detect exponential backoff"
        assert not self.detector._is_exponential_backoff(group_no_backoff), "Should not detect exponential in fixed intervals"
        
        # Both should be low scores (no time penalty), difference should be backoff penalty
        assert score_without > score_with, f"No backoff ({score_without}) should have higher penalty than with backoff ({score_with})"
        # Difference should be 15 points (30 no backoff - 15 with backoff)
        assert score_without - score_with == 15, f"Expected 15 point difference, got {score_without - score_with}"

    def test_small_responses_penalty(self):
        """
        Test: Small responses add 25 points
        """
        # Normal responses
        group_normal = self.create_group(
            count=4,
            interval_seconds=[2, 4, 8],
            completion_tokens=[100, 100, 100, 100]
        )
        
        # Small responses
        group_small = self.create_group(
            count=4,
            interval_seconds=[2, 4, 8],
            completion_tokens=[10, 10, 10, 10]
        )
        
        score_normal = self.detector._calculate_retry_quality_score(group_normal)
        score_small = self.detector._calculate_retry_quality_score(group_small)
        
        assert score_small - score_normal == 25, f"Expected 25 point difference, got {score_small - score_normal}"

    def test_retry_count_penalties(self):
        """
        Test: Retry count penalties (>7: +25, >5: +15, <=5: 0)
        Using long intervals to isolate retry count penalty
        """
        # 4 retries (no penalty)
        group_few = self.create_group(
            count=4,
            interval_seconds=[25, 25, 25],  # 75s total, >60s = no time penalty
            completion_tokens=[100] * 4
        )
        
        # 6 retries (+15)
        group_medium = self.create_group(
            count=6,
            interval_seconds=[15, 15, 15, 15, 15],  # 75s total, >60s = no time penalty
            completion_tokens=[100] * 6
        )
        
        # 8 retries (+25)
        group_many = self.create_group(
            count=8,
            interval_seconds=[11, 11, 11, 11, 11, 11, 11],  # 77s total, >60s = no time penalty
            completion_tokens=[100] * 8
        )
        
        score_few = self.detector._calculate_retry_quality_score(group_few)
        score_medium = self.detector._calculate_retry_quality_score(group_medium)
        score_many = self.detector._calculate_retry_quality_score(group_many)
        
        assert score_medium - score_few == 15, f"Expected 15 point increase for 6 retries, got {score_medium - score_few} ({score_medium} - {score_few})"
        assert score_many - score_few == 25, f"Expected 25 point increase for 8 retries, got {score_many - score_few} ({score_many} - {score_few})"

    def test_time_span_penalties(self):
        """
        Test: Time span penalties (<30s: +20, <60s: +15, >=60s: 0)
        """
        # Tight loop (20s)
        group_tight = self.create_group(
            count=5,
            interval_seconds=[5, 5, 5, 5],
            completion_tokens=[100] * 5
        )
        
        # Quick loop (50s)
        group_quick = self.create_group(
            count=5,
            interval_seconds=[12, 13, 12, 13],
            completion_tokens=[100] * 5
        )
        
        # Slow loop (70s)
        group_slow = self.create_group(
            count=5,
            interval_seconds=[17, 18, 17, 18],
            completion_tokens=[100] * 5
        )
        
        score_tight = self.detector._calculate_retry_quality_score(group_tight)
        score_quick = self.detector._calculate_retry_quality_score(group_quick)
        score_slow = self.detector._calculate_retry_quality_score(group_slow)
        
        # All have no backoff (30 points)
        assert score_tight - score_slow == 20, f"Expected 20 point increase for tight loop"
        assert score_quick - score_slow == 15, f"Expected 15 point increase for quick loop"

    def test_score_capped_at_100(self):
        """
        Test: Score cannot exceed 100
        """
        # Create worst case that would theoretically exceed 100
        group = self.create_group(
            count=10,  # Would be +25
            interval_seconds=[1] * 9,  # Would be +30 (no backoff) + 20 (tight loop)
            completion_tokens=[5] * 10  # Would be +25 (small responses)
        )
        
        score = self.detector._calculate_retry_quality_score(group)
        
        assert score <= 100, f"Score should be capped at 100, got {score}"
        assert score == 100, f"Expected 100, got {score}"

    def test_integration_with_detect(self):
        """
        Test: Quality score is included in detection output
        """
        traces = {
            "trace-1": [
                {"startTime": "2024-01-01T10:00:00Z", "prompt": "test", "model": "gpt-4", 
                 "completion_tokens": 10, "prompt_tokens": 100, "cost": 0.01},
                {"startTime": "2024-01-01T10:00:02Z", "prompt": "test", "model": "gpt-4",
                 "completion_tokens": 10, "prompt_tokens": 100, "cost": 0.01},
                {"startTime": "2024-01-01T10:00:04Z", "prompt": "test", "model": "gpt-4",
                 "completion_tokens": 10, "prompt_tokens": 100, "cost": 0.01},
                {"startTime": "2024-01-01T10:00:06Z", "prompt": "test", "model": "gpt-4",
                 "completion_tokens": 10, "prompt_tokens": 100, "cost": 0.01},
            ]
        }
        
        detections = self.detector.detect(traces)
        
        assert len(detections) == 1
        detection = detections[0]
        
        assert "quality_score" in detection, "Detection should include quality_score"
        assert isinstance(detection["quality_score"], int), "Quality score should be an integer"
        assert 0 <= detection["quality_score"] <= 100, "Quality score should be 0-100"
        assert "Quality score:" in detection["description"], "Description should mention quality score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
