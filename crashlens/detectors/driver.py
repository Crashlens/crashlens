"""
Detector Driver for CrashLens

Orchestrates running waste detectors on log batches in constant-memory mode.
Supports three modes: none, precomputed, and inline.

This module is critical for Step 3 of the guard/policy-check merge.
"""

import time
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from collections import defaultdict

try:
    from crashlens.detectors.retry_loops import RetryLoopDetector
    from crashlens.detectors.fallback_storm import FallbackStormDetector
    HAS_DETECTORS = True
except ImportError:
    HAS_DETECTORS = False


DetectorMode = Literal["none", "precomputed", "inline"]


@dataclass
class DetectorMetrics:
    """Metrics for detector execution."""
    detector_time_ms: float = 0.0
    records_processed: int = 0
    detections_found: int = 0
    detector_runs: Optional[Dict[str, float]] = None  # detector_name -> time_ms
    
    def __post_init__(self):
        if self.detector_runs is None:
            self.detector_runs = {}


class DetectorDriver:
    """
    Runs waste detectors on log batches and enriches records with detection metadata.
    
    Designed for constant-memory operation by processing batches only.
    
    Usage:
        driver = DetectorDriver(mode='inline')
        enriched_batch = driver.run_detectors_on_batch(batch)
        metrics = driver.get_metrics()
    """
    
    def __init__(
        self,
        mode: DetectorMode = "none",
        detector_config: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
    ):
        """Initialize detector driver.
        
        Args:
            mode: Detection mode:
                - "none": No detection, pass through records unchanged
                - "precomputed": Records already have detector.* fields, validate only
                - "inline": Run detectors now on this batch (CPU intensive)
            detector_config: Configuration for detectors (thresholds, etc.)
            verbose: Print diagnostic information
        """
        if mode not in ("none", "precomputed", "inline"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'none', 'precomputed', or 'inline'")
        
        self.mode = mode
        self.detector_config = detector_config or {}
        self.verbose = verbose
        self._metrics = DetectorMetrics()
        
        # Initialize detectors if inline mode
        self._detectors = []
        if mode == "inline":
            if not HAS_DETECTORS:
                raise RuntimeError(
                    "Cannot use inline detector mode: detector modules not available. "
                    "Use mode='none' or mode='precomputed' instead."
                )
            self._initialize_detectors()
    
    def _initialize_detectors(self) -> None:
        """Initialize all available detectors with config."""
        retry_config = self.detector_config.get("retry_loop", {})
        self._detectors.append(
            ("retry_loop", RetryLoopDetector(
                max_retries=retry_config.get("max_retries", 3),
                time_window_minutes=retry_config.get("time_window_minutes", 5),
            ))
        )
        
        fallback_config = self.detector_config.get("fallback_storm", {})
        self._detectors.append(
            ("fallback_storm", FallbackStormDetector(
                min_calls=fallback_config.get("min_calls", 3),
                min_models=fallback_config.get("min_models", 2),
                max_trace_window_minutes=fallback_config.get("max_trace_window_minutes", 3),
            ))
        )
        
        if self.verbose:
            print(f"Initialized {len(self._detectors)} detectors for inline mode")
    
    def run_detectors_on_batch(
        self,
        batch: List[Dict[str, Any]],
        model_pricing: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run detectors on a batch and return enriched records.
        
        Args:
            batch: List of log records (single batch from LogIterator)
            model_pricing: Optional pricing data for cost calculations
        
        Returns:
            Enriched batch with detector.* fields added to records
            
        Note:
            - mode="none": Returns batch unchanged
            - mode="precomputed": Validates detector fields exist, returns batch
            - mode="inline": Runs detectors, enriches batch, returns enriched records
        """
        if not batch:
            return batch
        
        self._metrics.records_processed += len(batch)
        
        if self.mode == "none":
            return batch
        
        if self.mode == "precomputed":
            return self._validate_precomputed(batch)
        
        # mode == "inline"
        return self._run_inline_detectors(batch, model_pricing)
    
    def _validate_precomputed(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate that precomputed detector fields exist."""
        for record in batch:
            # Check if at least one detector field exists
            has_detector_fields = any(
                key.startswith("detector.") for key in record.keys()
            )
            if not has_detector_fields and self.verbose:
                print(f"Warning: Record {record.get('id', 'unknown')} missing detector.* fields in precomputed mode")
        
        return batch
    
    def _run_inline_detectors(
        self,
        batch: List[Dict[str, Any]],
        model_pricing: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run detectors inline on this batch."""
        start_time = time.perf_counter()
        
        # Group by trace_id for detector processing
        traces: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for record in batch:
            trace_id = record.get("traceId") or record.get("trace_id") or "unknown"
            traces[trace_id].append(record)
        
        # Run each detector
        all_detections = []
        already_flagged = set()
        
        for detector_name, detector in self._detectors:
            detector_start = time.perf_counter()
            
            try:
                detections = detector.detect(
                    traces,
                    model_pricing=model_pricing,
                    already_flagged_ids=already_flagged,
                )
                all_detections.extend(detections)
                
                # Update flagged IDs to avoid double-counting
                for detection in detections:
                    already_flagged.add(detection.get("trace_id"))
                
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Detector {detector_name} failed: {e}")
                detections = []
            
            detector_elapsed = (time.perf_counter() - detector_start) * 1000
            if self._metrics.detector_runs is not None:
                self._metrics.detector_runs[detector_name] = detector_elapsed
            
            if self.verbose:
                print(f"Detector {detector_name}: {len(detections)} detections in {detector_elapsed:.2f}ms")
        
        # Enrich batch with detection metadata
        enriched_batch = self._enrich_batch_with_detections(batch, all_detections)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._metrics.detector_time_ms += elapsed_ms
        self._metrics.detections_found += len(all_detections)
        
        if self.verbose:
            print(f"Detector driver: {len(all_detections)} total detections in {elapsed_ms:.2f}ms")
        
        return enriched_batch
    
    def _enrich_batch_with_detections(
        self,
        batch: List[Dict[str, Any]],
        detections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add detector metadata to batch records.
        
        Enrichment schema:
            detector.retry_loop.detected: bool
            detector.retry_loop.severity: str
            detector.retry_loop.waste_cost: float
            detector.retry_loop.quality_score: float
            detector.fallback_storm.detected: bool
            detector.fallback_storm.severity: str
            detector.fallback_storm.cascade_depth: int
        """
        # Build trace_id -> detections map
        detection_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for detection in detections:
            trace_id = detection.get("trace_id")
            if trace_id:
                detection_map[trace_id].append(detection)
        
        # Enrich each record
        enriched = []
        for record in batch:
            enriched_record = record.copy()
            trace_id = record.get("traceId") or record.get("trace_id")
            
            if trace_id and trace_id in detection_map:
                for detection in detection_map[trace_id]:
                    detection_type = detection.get("type", "unknown")
                    
                    # Add detector fields
                    enriched_record[f"detector.{detection_type}.detected"] = True
                    enriched_record[f"detector.{detection_type}.severity"] = detection.get("severity", "unknown")
                    enriched_record[f"detector.{detection_type}.waste_cost"] = detection.get("waste_cost", 0.0)
                    
                    # Type-specific fields
                    if detection_type == "retry_loop":
                        enriched_record[f"detector.{detection_type}.quality_score"] = detection.get("quality_score", 0)
                        enriched_record[f"detector.{detection_type}.retry_count"] = detection.get("retry_count", 0)
                    
                    elif detection_type == "fallback_storm":
                        enriched_record[f"detector.{detection_type}.cascade_depth"] = detection.get("cascade_depth", 0)
            
            enriched.append(enriched_record)
        
        return enriched
    
    def get_metrics(self) -> DetectorMetrics:
        """Get detector execution metrics."""
        return self._metrics
    
    def reset_metrics(self) -> None:
        """Reset metrics for new run."""
        self._metrics = DetectorMetrics()


def run_detectors_on_batch(
    batch: List[Dict[str, Any]],
    mode: DetectorMode = "none",
    detector_config: Optional[Dict[str, Any]] = None,
    model_pricing: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Convenience function to run detectors on a single batch.
    
    Args:
        batch: List of log records
        mode: Detection mode ('none', 'precomputed', 'inline')
        detector_config: Detector configuration
        model_pricing: Model pricing data
        verbose: Print diagnostics
    
    Returns:
        Enriched batch
    
    Example:
        enriched = run_detectors_on_batch(batch, mode='inline')
    """
    driver = DetectorDriver(mode=mode, detector_config=detector_config, verbose=verbose)
    return driver.run_detectors_on_batch(batch, model_pricing=model_pricing)
