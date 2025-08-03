"""
Advanced Retry & Fallback Detection Module
Detects retry loops and fallback overuse from Langfuse-style traces, 
even with out-of-order logs or partial data.

Implements the GitHub Copilot prompt guidelines for production-grade detection.
"""

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple


class RetryFallbackDetector:
    """
    Advanced detector for retry loops and fallback overuse patterns.
    
    Features:
    - Handles out-of-order logs by re-sequencing by timestamp
    - Groups traces by intent using parent_id clustering
    - Detects retry loops via prompt hash matching within time windows
    - Identifies fallback abuse patterns (model escalation)
    - Production-safe with strict validation to avoid false positives
    """
    
    def __init__(self, 
                 retry_window_seconds: int = 2,
                 max_retries_threshold: int = 3,
                 fallback_escalation_threshold: int = 1,
                 verbose: bool = False):
        """
        Initialize the detector with configurable thresholds.
        
        Args:
            retry_window_seconds: Time window for considering calls as retries
            max_retries_threshold: Max retries before flagging as problematic
            fallback_escalation_threshold: Max fallbacks before flagging abuse
            verbose: Enable debug logging
        """
        self.retry_window = timedelta(seconds=retry_window_seconds)
        self.max_retries_threshold = max_retries_threshold
        self.fallback_escalation_threshold = fallback_escalation_threshold
        self.verbose = verbose
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        
        # Model hierarchy for fallback detection (weaker -> stronger)
        self.model_hierarchy = {
            'gpt-3.5-turbo': 1,
            'gpt-3.5-turbo-16k': 1.5,
            'gpt-4': 2,
            'gpt-4-turbo': 2.5,
            'gpt-4o': 3,
            'claude-3-haiku': 1.5,
            'claude-3-sonnet': 2,
            'claude-3-opus': 3,
            'claude-3-5-sonnet': 2.5,
        }

    def detect(self, traces: Dict[str, List[Dict[str, Any]]], 
               model_pricing: Optional[Dict[str, Any]] = None,
               already_flagged_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        Main detection method that analyzes traces for retry and fallback patterns.
        
        Args:
            traces: Dictionary mapping trace_ids to lists of records
            model_pricing: Optional pricing configuration for cost calculation
            already_flagged_ids: Set of trace IDs already claimed by other detectors
            
        Returns:
            List of detection dictionaries with structured results
        """
        if already_flagged_ids is None:
            already_flagged_ids = set()
            
        # Step 1: Normalize and re-sequence all traces
        normalized_traces = self._normalize_and_sequence_traces(traces)
        
        # Step 2: Group traces by intent using parent_id clustering
        retry_clusters = self._group_traces_by_intent(normalized_traces)
        
        # Step 3: Detect patterns within each cluster
        detections = []
        
        for cluster_id, cluster_traces in retry_clusters.items():
            # Skip if already flagged by higher-priority detectors
            if any(trace.get('traceId') in already_flagged_ids for trace in cluster_traces):
                continue
                
            # Sort cluster traces by timestamp for chronological analysis
            cluster_traces.sort(key=lambda t: t.get('timestamp', datetime.min))
            
            # Detect retry loops
            retry_detections = self._detect_retry_loops(cluster_id, cluster_traces, model_pricing)
            detections.extend(retry_detections)
            
            # Detect fallback overuse
            fallback_detections = self._detect_fallback_overuse(cluster_id, cluster_traces, model_pricing)
            detections.extend(fallback_detections)
        
        return detections

    def _normalize_and_sequence_traces(self, traces: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Step 1: Normalize all traces and re-sequence by timestamp.
        
        Args:
            traces: Raw traces dictionary
            
        Returns:
            List of normalized trace records sorted by timestamp
        """
        normalized_traces = []
        
        for trace_id, records in traces.items():
            for record in records:
                # Normalize the record structure
                normalized = self._normalize_record(record, trace_id)
                if normalized:
                    normalized_traces.append(normalized)
        
        # Re-sequence by timestamp (critical for out-of-order logs)
        normalized_traces.sort(key=lambda t: t.get('timestamp', datetime.min))
        
        self.logger.debug(f"Normalized and sequenced {len(normalized_traces)} trace records")
        return normalized_traces

    def _normalize_record(self, record: Dict[str, Any], trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Normalize a single record to standard format with required fields.
        
        Args:
            record: Raw record from trace
            trace_id: Trace ID for this record
            
        Returns:
            Normalized record or None if invalid
        """
        try:
            # Extract timestamp
            timestamp_str = record.get('startTime')
            if not timestamp_str:
                return None
                
            timestamp = self._parse_timestamp(timestamp_str)
            if not timestamp:
                return None
            
            # Extract prompt and create hash
            prompt = record.get('prompt', '')
            if not prompt:
                # Try to get from input structure
                prompt = record.get('input', {}).get('prompt', '')
            
            prompt_hash = self._hash_prompt(prompt) if prompt else None
            
            # Extract model
            model = record.get('model')
            if not model:
                model = record.get('input', {}).get('model')
            
            # Create normalized record
            normalized = {
                'id': record.get('id', f"{trace_id}_{hash(str(record))}"),
                'traceId': trace_id,
                'timestamp': timestamp,
                'prompt': prompt,
                'prompt_hash': prompt_hash,
                'model': model,
                'parent_id': record.get('parent_id'),
                'prompt_tokens': record.get('prompt_tokens', 0) or record.get('usage', {}).get('prompt_tokens', 0),
                'completion_tokens': record.get('completion_tokens', 0) or record.get('usage', {}).get('completion_tokens', 0),
                'cost': record.get('cost', 0),
                'original_record': record  # Keep reference for detailed analysis
            }
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"Failed to normalize record: {e}")
            return None

    def _hash_prompt(self, prompt: str) -> str:
        """Create a hash of the prompt for exact matching."""
        if not prompt:
            return ""
        # Normalize whitespace and create hash
        normalized_prompt = ' '.join(prompt.split())
        return hashlib.md5(normalized_prompt.encode('utf-8')).hexdigest()

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
            
        try:
            # Handle various ISO formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', ''))
            except ValueError:
                self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
                return None

    def _group_traces_by_intent(self, normalized_traces: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Step 2: Group traces by intent using parent_id fallback strategy.
        
        Args:
            normalized_traces: List of normalized trace records
            
        Returns:
            Dictionary mapping cluster IDs to lists of related traces
        """
        retry_clusters = defaultdict(list)
        
        for trace in normalized_traces:
            # Use parent_id if available, otherwise use the trace's own ID
            cluster_key = trace.get('parent_id') or trace.get('traceId') or trace.get('id')
            retry_clusters[cluster_key].append(trace)
        
        self.logger.debug(f"Grouped traces into {len(retry_clusters)} intent clusters")
        return dict(retry_clusters)

    def _detect_retry_loops(self, cluster_id: str, cluster_traces: List[Dict[str, Any]], 
                           model_pricing: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3a: Detect retry loops within a cluster.
        
        Args:
            cluster_id: Identifier for the cluster
            cluster_traces: List of traces in this cluster
            model_pricing: Optional pricing data
            
        Returns:
            List of retry loop detections
        """
        detections = []
        
        if len(cluster_traces) < 2:
            return detections
        
        # Group by prompt hash and model for retry detection
        prompt_groups = defaultdict(list)
        
        for trace in cluster_traces:
            if trace.get('prompt_hash') and trace.get('model'):
                key = (trace['prompt_hash'], trace['model'])
                prompt_groups[key].append(trace)
        
        # Analyze each prompt group for retry patterns
        for (prompt_hash, model), traces in prompt_groups.items():
            if len(traces) < 2:
                continue
                
            # Sort by timestamp for chronological analysis
            traces.sort(key=lambda t: t['timestamp'])
            
            # Find retry sequences
            retry_sequences = self._find_retry_sequences(traces)
            
            for sequence in retry_sequences:
                if len(sequence) > self.max_retries_threshold:
                    detection = self._create_retry_detection(cluster_id, sequence, model_pricing)
                    detections.append(detection)
        
        return detections

    def _find_retry_sequences(self, traces: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Find sequences of retries within the time window.
        
        Args:
            traces: List of traces with same prompt hash and model
            
        Returns:
            List of retry sequences
        """
        if len(traces) < 2:
            return []
            
        sequences = []
        current_sequence = [traces[0]]
        
        for i in range(1, len(traces)):
            prev_trace = traces[i-1]
            curr_trace = traces[i]
            
            # Check if current trace is within retry window of previous
            time_diff = curr_trace['timestamp'] - prev_trace['timestamp']
            
            if time_diff <= self.retry_window:
                # Part of current sequence
                current_sequence.append(curr_trace)
            else:
                # Start new sequence if current one is significant
                if len(current_sequence) > 1:
                    sequences.append(current_sequence)
                current_sequence = [curr_trace]
        
        # Don't forget the last sequence
        if len(current_sequence) > 1:
            sequences.append(current_sequence)
            
        return sequences

    def _detect_fallback_overuse(self, cluster_id: str, cluster_traces: List[Dict[str, Any]], 
                                model_pricing: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3b: Detect fallback overuse patterns (model escalation).
        
        Args:
            cluster_id: Identifier for the cluster
            cluster_traces: List of traces in this cluster
            model_pricing: Optional pricing data
            
        Returns:
            List of fallback overuse detections
        """
        detections = []
        
        if len(cluster_traces) < 2:
            return detections
        
        # Group by prompt hash for fallback analysis
        prompt_groups = defaultdict(list)
        
        for trace in cluster_traces:
            if trace.get('prompt_hash'):
                prompt_groups[trace['prompt_hash']].append(trace)
        
        # Analyze each prompt group for fallback escalation
        for prompt_hash, traces in prompt_groups.items():
            if len(traces) < 2:
                continue
                
            # Sort by timestamp
            traces.sort(key=lambda t: t['timestamp'])
            
            # Check for model escalation pattern
            escalation_sequence = self._find_model_escalation(traces)
            
            if len(escalation_sequence) > self.fallback_escalation_threshold:
                detection = self._create_fallback_detection(cluster_id, escalation_sequence, model_pricing)
                detections.append(detection)
        
        return detections

    def _find_model_escalation(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find sequences where models escalate in power/cost.
        
        Args:
            traces: List of traces with same prompt
            
        Returns:
            List of traces showing escalation pattern
        """
        if len(traces) < 2:
            return []
            
        escalation_sequence = [traces[0]]
        last_model_strength = self._get_model_strength(traces[0].get('model', ''))
        
        for trace in traces[1:]:
            model_strength = self._get_model_strength(trace.get('model', ''))
            
            # Check if this model is stronger than the previous
            if model_strength > last_model_strength:
                escalation_sequence.append(trace)
                last_model_strength = model_strength
            else:
                # Reset sequence if model doesn't escalate
                if len(escalation_sequence) > 1:
                    break
                escalation_sequence = [trace]
                last_model_strength = model_strength
        
        return escalation_sequence if len(escalation_sequence) > 1 else []

    def _get_model_strength(self, model: str) -> float:
        """Get the strength/cost ranking of a model."""
        return self.model_hierarchy.get(model, 1.0)

    def _create_retry_detection(self, cluster_id: str, sequence: List[Dict[str, Any]], 
                               model_pricing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a structured retry detection result."""
        total_tokens = sum(
            trace.get('prompt_tokens', 0) + trace.get('completion_tokens', 0) 
            for trace in sequence
        )
        total_cost = sum(trace.get('cost', 0) for trace in sequence)
        
        time_span = (sequence[-1]['timestamp'] - sequence[0]['timestamp']).total_seconds()
        
        return {
            'type': 'retry_loop',
            'cluster_id': cluster_id,
            'trace_id': sequence[0].get('traceId'),
            'timestamp': sequence[0]['timestamp'].isoformat(),
            'severity': 'high' if len(sequence) > 5 else 'medium',
            'description': (
                f"Retry loop detected: {len(sequence)} identical calls "
                f"using {sequence[0].get('model', 'unknown')} within {time_span:.1f}s"
            ),
            'details': {
                'retry_count': len(sequence),
                'model': sequence[0].get('model'),
                'prompt_hash': sequence[0].get('prompt_hash'),
                'time_span_seconds': time_span,
                'waste_tokens': total_tokens,
                'waste_cost': total_cost,
                'detection_method': 'prompt_hash_clustering',
                'sample_prompt': sequence[0].get('prompt', '')[:150] + ('...' if len(sequence[0].get('prompt', '')) > 150 else ''),
                'trace_ids': [trace.get('traceId') for trace in sequence],
                'timestamps': [trace['timestamp'].isoformat() for trace in sequence]
            }
        }

    def _create_fallback_detection(self, cluster_id: str, sequence: List[Dict[str, Any]], 
                                  model_pricing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a structured fallback detection result."""
        total_tokens = sum(
            trace.get('prompt_tokens', 0) + trace.get('completion_tokens', 0) 
            for trace in sequence
        )
        total_cost = sum(trace.get('cost', 0) for trace in sequence)
        
        model_progression = [trace.get('model', 'unknown') for trace in sequence]
        
        return {
            'type': 'fallback_overuse',
            'cluster_id': cluster_id,
            'trace_id': sequence[0].get('traceId'),
            'timestamp': sequence[0]['timestamp'].isoformat(),
            'severity': 'medium',
            'description': (
                f"Fallback overuse detected: escalated through {len(sequence)} models "
                f"({' → '.join(model_progression)})"
            ),
            'details': {
                'escalation_count': len(sequence),
                'model_progression': model_progression,
                'prompt_hash': sequence[0].get('prompt_hash'),
                'waste_tokens': total_tokens,
                'waste_cost': total_cost,
                'detection_method': 'model_escalation_analysis',
                'sample_prompt': sequence[0].get('prompt', '')[:150] + ('...' if len(sequence[0].get('prompt', '')) > 150 else ''),
                'trace_ids': [trace.get('traceId') for trace in sequence],
                'model_strengths': [self._get_model_strength(trace.get('model', '')) for trace in sequence]
            }
        }
