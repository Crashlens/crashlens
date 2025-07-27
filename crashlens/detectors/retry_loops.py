"""
Retry Loop Detector
Detects patterns of repeated API calls that suggest retry loops using exact string matching.
This version removes all semantic similarity and embedding logic.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

class RetryLoopDetector:
    """
    Detects retry loops in API call traces using exact string matching.

    This detector identifies when the same prompt is sent
    multiple times using the same model within a short time window for the same trace ID.
    """
    def __init__(self, max_retries: int = 3, time_window_minutes: int = 5, max_retry_interval_minutes: int = 2):
        """
        Initializes the detector with configurable thresholds.

        Args:
            max_retries (int): The number of calls (original + retries)
                               that must be exceeded to trigger a detection.
                               A value of 3 means 4+ calls will be flagged.
            time_window_minutes (int): The maximum time in minutes from first to last retry.
            max_retry_interval_minutes (int): Maximum time between consecutive retries.
        """
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1.")
        
        self.max_retries = max_retries
        self.time_window = timedelta(minutes=time_window_minutes)
        self.max_retry_interval = timedelta(minutes=max_retry_interval_minutes)

    def detect(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Analyzes all traces and detects retry loops based on exact string matching.

        Args:
            traces (Dict[str, List[Dict[str, Any]]]): A dictionary where keys are
                                                      trace_ids and values are lists
                                                      of log records.

        Returns:
            List[Dict[str, Any]]: A list of detection dictionaries, one for each
                                  identified retry loop.
        """
        detections = []
        for trace_id, records in traces.items():
            # Optimization: a loop cannot occur if the number of records
            # is not greater than the retry threshold.
            if len(records) <= self.max_retries:
                continue

            # Find groups of consecutive, exactly matching prompts.
            prompt_groups = self._find_retry_groups(records)

            for group in prompt_groups:
                # A loop is detected if the number of calls in a group
                # exceeds the configured maximum.
                if len(group) > self.max_retries:
                    # Check if this group meets all retry loop criteria
                    if not self._is_valid_retry_loop(group):
                        continue
                    
                    total_tokens = 0
                    for r in group:
                        # Handle both flattened (from parser) and nested (original) structures
                        if 'usage' in r:
                            usage = r.get('usage', {})
                            prompt_tokens = usage.get('prompt_tokens', 0)
                            completion_tokens = usage.get('completion_tokens', 0)
                        else:
                            prompt_tokens = r.get('prompt_tokens', 0)
                            completion_tokens = r.get('completion_tokens', 0)
                        total_tokens += prompt_tokens + completion_tokens
                    total_cost = sum(self._calculate_record_cost(r, model_pricing) for r in group)
                    
                    # The first record in the group is a good sample.
                    sample_prompt = group[0].get('prompt', 'N/A')
                    sample_model = group[0].get('model', 'N/A')

                    detection = {
                        'type': 'retry_loop',
                        'trace_id': trace_id,
                        'severity': 'high' if len(group) > 5 else 'medium',
                        'description': (
                            f"Retry loop detected with {len(group)} identical calls "
                            f"using {sample_model} for the same prompt."
                        ),
                        'waste_tokens': total_tokens,
                        'waste_cost': total_cost,
                        'retry_count': len(group),
                        'model': sample_model,
                        'time_span': f"{self._get_time_span(group):.1f} seconds",
                        'sample_prompt': sample_prompt[:150] + ('...' if len(sample_prompt) > 150 else ''),
                        'detection_method': 'exact_match',
                        'has_small_responses': self._has_small_responses(group),
                        'records': group
                    }
                    detections.append(detection)

        return detections

    def _find_retry_groups(self, records: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Groups consecutive records that have exactly the same prompt and model within the time window.
        This is the core logic for identifying potential retry loops.

        Args:
            records (List[Dict[str, Any]]): The list of log records for a single trace.

        Returns:
            List[List[Dict[str, Any]]]: A list of groups, where each group is a list of
                                        records considered to be part of a retry sequence.
        """
        # Ensure records are sorted by time to process them chronologically.
        try:
            sorted_records = sorted(
                [r for r in records if 'startTime' in r], 
                key=lambda r: r['startTime']
            )
        except (TypeError, ValueError):
            # Handle cases with malformed timestamps.
            return []

        if not sorted_records:
            return []

        all_groups = []
        current_group = [sorted_records[0]]

        for i in range(1, len(sorted_records)):
            prev_record = sorted_records[i-1]
            curr_record = sorted_records[i]

            # Check if the two consecutive records are exactly the same prompt and model.
            prev_prompt = prev_record.get('prompt')
            curr_prompt = curr_record.get('prompt')
            prev_model = prev_record.get('model')
            curr_model = curr_record.get('model')
            
            are_same_prompt = prev_prompt == curr_prompt
            are_same_model = prev_model == curr_model

            # Check the time window constraint.
            prev_time = datetime.fromisoformat(prev_record['startTime'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(curr_record['startTime'].replace('Z', '+00:00'))
            time_diff = curr_time - prev_time
            is_within_time_window = time_diff <= self.time_window
            is_within_retry_interval = time_diff <= self.max_retry_interval

            if are_same_prompt and are_same_model and is_within_time_window and is_within_retry_interval:
                # If same prompt, same model, and within the time limit, extend the current group.
                current_group.append(curr_record)
            else:
                # If not same prompt/model or outside the time window, the current loop has ended.
                # Store the completed group and start a new one.
                all_groups.append(current_group)
                current_group = [curr_record]
        
        # Add the last group after the loop finishes.
        all_groups.append(current_group)

        return all_groups

    def _get_time_span(self, records: List[Dict[str, Any]]) -> float:
        """Calculates the total time span of a group of records in seconds."""
        if len(records) < 2:
            return 0.0
        
        # Parse timestamps, ignoring potential errors.
        timestamps = []
        for r in records:
            try:
                timestamps.append(datetime.fromisoformat(r['startTime'].replace('Z', '+00:00')))
            except (KeyError, ValueError):
                continue
        
        if len(timestamps) < 2:
            return 0.0
            
        span = max(timestamps) - min(timestamps)
        return round(span.total_seconds(), 2)

    def _calculate_record_cost(self, record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]]) -> float:
        if not model_pricing:
            return record.get('cost', 0.0)
        model = record.get('model', 'gpt-3.5-turbo')
        input_tokens = record.get('prompt_tokens', 0)
        output_tokens = record.get('completion_tokens', 0)
        if 'cost' in record and record['cost'] is not None:
            return record['cost']
        model_config = model_pricing.get(model, {})
        if model_config:
            input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
            output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
            return input_cost + output_cost
        return 0.0
    
    def _is_valid_retry_loop(self, group: List[Dict[str, Any]]) -> bool:
        """
        Validates that a group of records represents a true retry loop.
        Checks that consecutive retries are within the retry interval.
        """
        if len(group) < 2:
            return True
        
        # Check that all consecutive calls are within retry interval
        for i in range(1, len(group)):
            prev_time = datetime.fromisoformat(group[i-1]['startTime'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(group[i]['startTime'].replace('Z', '+00:00'))
            
            if (curr_time - prev_time) > self.max_retry_interval:
                return False
        
        return True
    
    def _has_small_responses(self, group: List[Dict[str, Any]]) -> bool:
        """
        Checks if the group has consistently small response sizes,
        indicating retries aren't adding real value.
        """
        completion_tokens = [r.get('completion_tokens', 0) for r in group]
        
        # Consider responses small if they're all under 50 tokens
        # and don't vary significantly (standard deviation < 20)
        if not completion_tokens or max(completion_tokens) > 50:
            return False
        
        # Check variance - small responses should be similar in size
        if len(completion_tokens) > 1:
            avg = sum(completion_tokens) / len(completion_tokens)
            variance = sum((x - avg) ** 2 for x in completion_tokens) / len(completion_tokens)
            std_dev = variance ** 0.5
            return std_dev < 20
        
        return True 