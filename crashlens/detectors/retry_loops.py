"""
Retry Loop Detector
Detects patterns of repeated API calls that suggest retry loops using exact string matching.
<<<<<<< HEAD
Includes exponential backoff detection, improved severity logic, and robust cost calculation.
=======
This version removes all semantic similarity and embedding logic.
Now includes exponential backoff detection.
>>>>>>> origin/arnav2
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

<<<<<<< HEAD
                    total_tokens = sum(
                        r.get("prompt_tokens", 0) + r.get("completion_tokens", 0)
                        for r in group
                    )
=======
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
>>>>>>> origin/arnav2

                    total_cost = sum(
                        self._calculate_record_cost(r, model_pricing) for r in group
                    )

                    sample_prompt = group[0].get("prompt", "N/A")
                    sample_model = group[0].get("model", "N/A")

                    # Severity logic — lower if exponential backoff is used
                    severity = (
                        "low"
                        if has_exponential_backoff
                        else ("high" if len(group) > 5 else "medium")
                    )

                    detection = {
                        "type": "retry_loop",
                        "trace_id": trace_id,
                        "severity": severity,
                        "description": (
                            f"Retry loop detected with {len(group)} identical calls "
                            f"using {sample_model} for the same prompt. "
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
        sorted_records = sorted(
            [r for r in records if "startTime" in r], key=lambda r: r["startTime"]
        )
=======
        try:
            sorted_records = sorted(
                [r for r in records if "startTime" in r], key=lambda r: r["startTime"]
            )
        except (TypeError, ValueError):
            return []
>>>>>>> origin/arnav2

        if not sorted_records:
            return []

        all_groups = []
        current_group = [sorted_records[0]]

        for i in range(1, len(sorted_records)):
            prev = sorted_records[i - 1]
            curr = sorted_records[i]

<<<<<<< HEAD
            same_prompt = prev.get("prompt") == curr.get("prompt")
            same_model = prev.get("model") == curr.get("model")
=======
            prev_prompt = prev_record.get("prompt")
            curr_prompt = curr_record.get("prompt")
            prev_model = prev_record.get("model")
            curr_model = curr_record.get("model")
>>>>>>> origin/arnav2

            prev_time = datetime.fromisoformat(prev["startTime"].replace("Z", "+00:00"))
            curr_time = datetime.fromisoformat(curr["startTime"].replace("Z", "+00:00"))
            delta = curr_time - prev_time

<<<<<<< HEAD
            if same_prompt and same_model and delta <= self.time_window and delta <= self.max_retry_interval:
                current_group.append(curr)
            else:
                if len(current_group) > 1:
                    all_groups.append(current_group)
                current_group = [curr]

        if len(current_group) > 1:
            all_groups.append(current_group)

        return all_groups

    def _get_time_span(self, records: List[Dict[str, Any]]) -> float:
        timestamps = [
            datetime.fromisoformat(r["startTime"].replace("Z", "+00:00"))
            for r in records
            if "startTime" in r
        ]
=======
            prev_time = datetime.fromisoformat(
                prev_record["startTime"].replace("Z", "+00:00")
            )
            curr_time = datetime.fromisoformat(
                curr_record["startTime"].replace("Z", "+00:00")
            )
            time_diff = curr_time - prev_time
            is_within_time_window = time_diff <= self.time_window
            is_within_retry_interval = time_diff <= self.max_retry_interval

            if (
                are_same_prompt
                and are_same_model
                and is_within_time_window
                and is_within_retry_interval
            ):
                current_group.append(curr_record)
            else:
                all_groups.append(current_group)
                current_group = [curr_record]

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

>>>>>>> origin/arnav2
        if len(timestamps) < 2:
            return 0.0
        span = max(timestamps) - min(timestamps)
        return round(span.total_seconds(), 2)

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
=======
        if len(group) < 2:
            return True

>>>>>>> origin/arnav2
        for i in range(1, len(group)):
            prev_time = datetime.fromisoformat(group[i - 1]["startTime"].replace("Z", "+00:00"))
            curr_time = datetime.fromisoformat(group[i]["startTime"].replace("Z", "+00:00"))
            if (curr_time - prev_time) > self.max_retry_interval:
                return False
        return True

    def _is_exponential_backoff(self, group: List[Dict[str, Any]]) -> bool:
<<<<<<< HEAD
        if len(group) < 3:
            return False

        times = [datetime.fromisoformat(r["startTime"].replace("Z", "+00:00")) for r in group]
        intervals = [max((times[i] - times[i-1]).total_seconds(), 0.001) for i in range(1, len(times))]
=======
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
>>>>>>> origin/arnav2

        if len(intervals) < 2:
            return False

        ratios = [intervals[i]/intervals[i-1] for i in range(1, len(intervals)) if intervals[i-1] > 0]

        has_exp_step = any(1.5 <= r <= 3.0 for r in ratios)
        stable_or_increasing = all(r >= 1.0 for r in ratios)
        return has_exp_step and stable_or_increasing

    def _has_small_responses(self, group: List[Dict[str, Any]]) -> bool:
        completion_tokens = [r.get("completion_tokens", 0) for r in group]
        if not completion_tokens or max(completion_tokens) > 50:
            return False
        avg = sum(completion_tokens) / len(completion_tokens)
        variance = sum((x - avg)**2 for x in completion_tokens) / len(completion_tokens)
        return variance**0.5 < 20
