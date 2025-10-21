"""
Retry Loop Detector
Detects patterns of repeated API calls that suggest retry loops using exact string matching.
This version removes all semantic similarity and embedding logic.
Now includes exponential backoff detection.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class RetryLoopDetector:
    """
    Detects retry loops in API call traces using exact string matching.

    This detector identifies when the same prompt is sent
    multiple times using the same model within a short time window for the same trace ID.
    """

    def __init__(
        self,
        max_retries: int = 3,
        time_window_minutes: int = 5,
        max_retry_interval_minutes: int = 2,
    ):
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1.")

        self.max_retries = max_retries
        self.time_window = timedelta(minutes=time_window_minutes)
        self.max_retry_interval = timedelta(minutes=max_retry_interval_minutes)

    def detect(
        self,
        traces: Dict[str, List[Dict[str, Any]]],
        model_pricing: Optional[Dict[str, Any]] = None,
        already_flagged_ids: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        if already_flagged_ids is None:
            already_flagged_ids = set()

        detections = []
        for trace_id, records in traces.items():
            if trace_id in already_flagged_ids:
                continue
            if len(records) <= self.max_retries:
                continue

            prompt_groups = self._find_retry_groups(records)

            for group in prompt_groups:
                if len(group) > self.max_retries:
                    if not self._is_valid_retry_loop(group):
                        continue

                    has_exponential_backoff = self._is_exponential_backoff(group)

                    total_tokens = 0
                    for r in group:
                        if "usage" in r:
                            usage = r.get("usage", {})
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                        else:
                            prompt_tokens = r.get("prompt_tokens", 0)
                            completion_tokens = r.get("completion_tokens", 0)
                        total_tokens += prompt_tokens + completion_tokens

                    total_cost = sum(
                        self._calculate_record_cost(r, model_pricing) for r in group
                    )

                    sample_prompt = group[0].get("prompt", "N/A")
                    sample_model = group[0].get("model", "N/A")

                    # Calculate quality score and derive severity
                    quality_score = self._calculate_retry_quality_score(group)
                    if quality_score >= 70:
                        severity = "high"
                    elif quality_score >= 40:
                        severity = "medium"
                    else:
                        severity = "low"

                    detection = {
                        "type": "retry_loop",
                        "trace_id": trace_id,
                        "severity": severity,
                        "quality_score": quality_score,
                        "description": (
                            f"Retry loop detected with {len(group)} identical calls "
                            f"using {sample_model} for the same prompt. "
<<<<<<< HEAD
                            f"Quality score: {quality_score}/100 (higher is worse). "
=======
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460
                            + (
                                "Exponential backoff detected."
                                if has_exponential_backoff
                                else "No exponential backoff detected."
                            )
                        ),
                        "waste_tokens": total_tokens,
                        "waste_cost": total_cost,
                        "retry_count": len(group),
                        "model": sample_model,
                        "time_span": f"{self._get_time_span(group):.1f} seconds",
                        "sample_prompt": sample_prompt[:150]
                        + ("..." if len(sample_prompt) > 150 else ""),
                        "detection_method": "exact_match",
                        "has_small_responses": self._has_small_responses(group),
                        "has_exponential_backoff": has_exponential_backoff,
                        "records": group,
                    }
                    detections.append(detection)

        return detections

    def _find_retry_groups(
        self, records: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
<<<<<<< HEAD
        # FIX: Validate required fields before processing
        valid_records = [
            r for r in records 
            if all(k in r for k in ["startTime", "prompt", "model"])
        ]
        
        if not valid_records:
            return []
        
=======
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460
        try:
            sorted_records = sorted(valid_records, key=lambda r: r["startTime"])
        except (TypeError, ValueError):
            return []

        if not sorted_records:
            return []

        all_groups = []
        current_group = [sorted_records[0]]

        for i in range(1, len(sorted_records)):
<<<<<<< HEAD
            prev = sorted_records[i - 1]
            curr = sorted_records[i]
=======
            prev_record = sorted_records[i - 1]
            curr_record = sorted_records[i]

            prev_prompt = prev_record.get("prompt")
            curr_prompt = curr_record.get("prompt")
            prev_model = prev_record.get("model")
            curr_model = curr_record.get("model")
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460

            prev_prompt = prev.get("prompt")
            curr_prompt = curr.get("prompt")
            prev_model = prev.get("model")
            curr_model = curr.get("model")
            
            are_same_prompt = prev_prompt == curr_prompt
            are_same_model = prev_model == curr_model

            prev_time = datetime.fromisoformat(
                prev["startTime"].replace("Z", "+00:00")
            )
            curr_time = datetime.fromisoformat(
                curr["startTime"].replace("Z", "+00:00")
            )
            time_diff = curr_time - prev_time
            # FIX: Remove redundant time_window check (max_retry_interval is stricter)
            is_within_retry_interval = time_diff <= self.max_retry_interval

            if (
                are_same_prompt
                and are_same_model
                and is_within_retry_interval
            ):
<<<<<<< HEAD
                current_group.append(curr)
=======
                current_group.append(curr_record)
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460
            else:
                all_groups.append(current_group)
                current_group = [curr]

        all_groups.append(current_group)
        return all_groups

    def _get_time_span(self, records: List[Dict[str, Any]]) -> float:
        if len(records) < 2:
            return 0.0

        timestamps = []
        for r in records:
            try:
                timestamps.append(
                    datetime.fromisoformat(r["startTime"].replace("Z", "+00:00"))
                )
            except (KeyError, ValueError):
                continue

        if len(timestamps) < 2:
            return 0.0
        span = max(timestamps) - min(timestamps)
        return round(span.total_seconds(), 2)

    def _calculate_retry_quality_score(self, group: List[Dict[str, Any]]) -> int:
        """
        Calculate retry wasteful-ness score (0-100). Higher score = worse retry behavior.
        
        Scoring factors:
        - No backoff: +30 penalty | Proper backoff: +15 (still wasteful)
        - Small/error responses: +25 (indicates failures)
        - High retry count (>7): +25 | Moderate (>5): +15
        - Tight loop (<30s): +20 | Quick loop (<60s): +15
        
        Returns:
            int: Quality score from 0-100, where higher is worse
        """
        score = 0
        
        # Penalty for no backoff (30) or bonus for proper backoff (15)
        if self._is_exponential_backoff(group):
            score += 15  # Still wasteful even with backoff
        else:
            score += 30  # Much worse without backoff
        
        # +25 for error responses (small/consistent tokens indicate failures)
        if self._has_small_responses(group):
            score += 25
        
        # +25 for many retries (>7), +15 for moderate (>5)
        retry_count = len(group)
        if retry_count > 7:
            score += 25
        elif retry_count > 5:
            score += 15
        
        # +20 for tight loop (< 30s), +15 for quick loop (< 60s)
        time_span = self._get_time_span(group)
        if time_span < 30:
            score += 20
        elif time_span < 60:
            score += 15
        
        return min(score, 100)

    def _calculate_record_cost(
        self, record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]]
    ) -> float:
        if not model_pricing:
            return record.get("cost", 0.0)

        model = record.get("model", "").strip().lower()
        pricing_keys = {k.lower(): v for k, v in model_pricing.items() if isinstance(k, str)}
        model_config = pricing_keys.get(model, {})

        input_tokens = record.get("prompt_tokens", 0)
        output_tokens = record.get("completion_tokens", 0)

        if record.get("cost", 0.0) > 0.0:
            return record["cost"]

        if model_config:
            input_cost = (input_tokens / 1000.0) * model_config.get("input_cost_per_1k", 0.0)
            output_cost = (output_tokens / 1000.0) * model_config.get("output_cost_per_1k", 0.0)
            return round(input_cost + output_cost, 8)

        return 0.0

    def _is_valid_retry_loop(self, group: List[Dict[str, Any]]) -> bool:
<<<<<<< HEAD
        """
        Validates retry characteristics by checking for retry signals.
        Accepts groups that show:
        - Small/consistent responses
        - Exponential backoff pattern
        - Increasing intervals (60% threshold)
        """
        if len(group) < 2:
            return True
        
        # Accept if shows retry signals
        if self._has_small_responses(group):
            return True
        
        if self._is_exponential_backoff(group):
            return True
        
        # Check for increasing intervals (retry backoff pattern)
        try:
            times = [
                datetime.fromisoformat(r["startTime"].replace("Z", "+00:00")) 
                for r in group
            ]
            intervals = [
                (times[i] - times[i-1]).total_seconds() 
                for i in range(1, len(times))
            ]
            
            if len(intervals) < 2:
                return True
            
            # Count intervals that increase (or stay roughly same, with 10% tolerance)
            increasing_count = sum(
                1 for i in range(1, len(intervals)) 
                if intervals[i] >= intervals[i-1] * 0.9
=======
        if len(group) < 2:
            return True

        for i in range(1, len(group)):
            prev_time = datetime.fromisoformat(
                group[i - 1]["startTime"].replace("Z", "+00:00")
            )
            curr_time = datetime.fromisoformat(
                group[i]["startTime"].replace("Z", "+00:00")
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460
            )
            
            # Accept if 60% of intervals show backoff pattern
            return increasing_count / (len(intervals) - 1) >= 0.6
        except Exception:
            return True

    def _is_exponential_backoff(self, group: List[Dict[str, Any]]) -> bool:
        """
        Checks if retry intervals approximately follow exponential backoff
        (each gap roughly doubles, within a small tolerance).
        At least 70% of ratios should show exponential growth (1.5-3x).
        """         
        if len(group) < 3:
            return False

        try:
            times = [
                datetime.fromisoformat(r["startTime"].replace("Z", "+00:00"))
                for r in group
            ]
        except Exception:
            return False

        intervals = [
            (times[i] - times[i - 1]).total_seconds() for i in range(1, len(times))
        ]
        if len(intervals) < 2:
            return False

        # FIX: Prevent division by zero
        ratios = [
            intervals[i] / intervals[i - 1] 
            for i in range(1, len(intervals)) 
            if intervals[i - 1] > 0
        ]
        
        if not ratios:
            return False

        # More tolerant: require 70% of ratios to show exponential growth
        exponential_ratios = [r for r in ratios if 1.5 <= r <= 3.0]
        stable_or_increasing = sum(1 for r in ratios if r >= 0.95) / len(ratios) >= 0.7
        
        return len(exponential_ratios) >= max(1, len(ratios) * 0.7) and stable_or_increasing

    def _is_exponential_backoff(self, group: List[Dict[str, Any]]) -> bool:
        """
        Checks if retry intervals approximately follow exponential backoff
        (each gap roughly doubles, within a small tolerance).
        """
        if len(group) < 3:
            return False

        try:
            times = [
                datetime.fromisoformat(r["startTime"].replace("Z", "+00:00"))
                for r in group
            ]
        except Exception:
            return False

        intervals = [
            (times[i] - times[i - 1]).total_seconds() for i in range(1, len(times))
        ]
        if len(intervals) < 2:
            return False

        ratios = [intervals[i] / intervals[i - 1] for i in range(1, len(intervals))]

        return all(1.7 <= r <= 2.3 for r in ratios)

    def _has_small_responses(self, group: List[Dict[str, Any]]) -> bool:
<<<<<<< HEAD
        """
        Check if response sizes are consistently small (indicating retries).
        Uses coefficient of variation (CV) for scale-independent variance check.
        """
        # Filter out None values
        completion_tokens = [
            r.get("completion_tokens", 0) 
            for r in group 
            if r.get("completion_tokens") is not None
        ]
        
        # FIX: Check actual value for single response
        if len(completion_tokens) == 0:
            return False
        
        if len(completion_tokens) == 1:
            return completion_tokens[0] <= 50  # Validate actual token count
        
        # Multiple responses - check consistency
        if max(completion_tokens) > 50:
            return False
        
        avg = sum(completion_tokens) / len(completion_tokens)
        
        # Handle all-zero responses (errors)
        if avg == 0:
            return True
        
        variance = sum((x - avg) ** 2 for x in completion_tokens) / len(completion_tokens)
        std_dev = variance**0.5
        
        # FIX: Use coefficient of variation (CV) instead of absolute threshold
        cv = std_dev / avg
        return cv < 0.4  # 40% variation threshold (scale-independent)
=======
        completion_tokens = [r.get("completion_tokens", 0) for r in group]

        if not completion_tokens or max(completion_tokens) > 50:
            return False

        if len(completion_tokens) > 1:
            avg = sum(completion_tokens) / len(completion_tokens)
            variance = sum((x - avg) ** 2 for x in completion_tokens) / len(
                completion_tokens
            )
            std_dev = variance**0.5
            return std_dev < 20

        return True
>>>>>>> b79f8e658d4214b5e7d9cbfc57fc5001dfa0e460
