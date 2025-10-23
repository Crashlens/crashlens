"""
Prometheus Metrics Implementation for CrashLens

This module implements lazy-loading Prometheus metrics collection with:
- Zero overhead when disabled
- Cardinality protection to prevent label explosion
- Kill switch via environment variable
- Self-monitoring of metrics system health

Design Decisions:
- Lazy imports: prometheus_client only loaded when enabled
- Gauges for latency: Simpler than histograms, sufficient for our use case
- Label limits: Prevents unbounded memory growth from dynamic rule names
- Overflow handling: Collapses excess labels to 'rule_overflow' sentinel

See Phase 0 benchmark results: -7.91% overhead (zero measurable impact)
"""

import os
import logging
import random
from typing import Optional, Set

# Lazy import - do NOT import prometheus_client at module level
_prometheus_available = False
_Counter = None
_Gauge = None
_CollectorRegistry = None
_REGISTRY = None

logger = logging.getLogger(__name__)

# Cardinality protection constants
SEVERITY_WHITELIST = {"critical", "high", "medium", "low", "info"}
OVERFLOW_SENTINEL = "rule_overflow"


class CrashLensMetrics:
    """
    Prometheus metrics collector for CrashLens policy enforcement.

    This class provides methods to record policy rule hits, violations,
    trace processing, and performance metrics.

    Cardinality Protection:
        - Severity: Whitelisted to 5 values
        - Rule names: Limited to max_rules (default 500)
        - Overflow: Excess rules collapsed to 'rule_overflow' label

    Attributes:
        max_rules: Maximum unique rule names before overflow
        _tracked_rules: Set of rule names currently being tracked

    Metrics Exposed:
        crashlens_rule_hits_total: Counter of rule triggers
        crashlens_violations_total: Counter of violations by severity
        crashlens_traces_processed_total: Counter of traces analyzed
        crashlens_traces_failed_total: Counter of failed traces
        crashlens_decision_latency_avg_seconds: Average rule evaluation time (sampled)
        crashlens_last_run_timestamp_seconds: Unix timestamp of last run
        crashlens_metrics_push_status: Push success indicator (1=success, 0=fail)
        crashlens_rule_label_overflow_total: Count of overflow events
    """

    def __init__(self, max_rules: int = 500, sample_rate: float = 1.0, per_rule_rates: Optional[dict] = None):
        """
        Initialize metrics collectors with optional sampling.

        Args:
            max_rules: Maximum number of unique rule names to track
            sample_rate: Global probability of recording each metric (0.0-1.0, default: 1.0)
                        1.0 = record all (100% sampling)
                        0.1 = record 10% (reduce overhead)
                        0.0 = record nothing (disable)
            per_rule_rates: Optional dict of rule_name -> sample_rate overrides
                           Allows different sampling rates for specific rules
                           Example: {"expensive_rule": 0.01, "rare_event": 1.0}

        Raises:
            RuntimeError: If prometheus_client is not available
            ValueError: If sample_rate is not between 0.0 and 1.0
        
        Note:
            Sampling is applied per-metric-call, not per-trace.
            Lower sample rates reduce overhead but decrease metric granularity.
            Counters remain statistically accurate with random sampling.
            Per-rule rates override the global sample_rate for specific rules.
        """
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError(f"sample_rate must be between 0.0 and 1.0, got {sample_rate}")
        
        if not _prometheus_available:
            raise RuntimeError(
                "prometheus_client is not available. "
                "Install with: pip install crashlens[metrics]"
            )

        self.max_rules = max_rules
        self._sample_rate = sample_rate
        self._per_rule_rates = per_rule_rates or {}
        self._tracked_rules: Set[str] = set()

        # Initialize all metrics
        self._init_counters()
        self._init_gauges()

    def _init_counters(self):
        """Initialize counter metrics."""
        # Guard against static analyzers / None at import time: ensure Counter callable exists
        if _Counter is None:
            raise RuntimeError(
                "Prometheus Counter class not initialized. "
                "Ensure _initialize_metrics_impl was called and prometheus_client was imported successfully."
            )
        Counter = _Counter

        # Rule hits counter
        self.rule_hits = Counter(
            "crashlens_rule_hits_total",
            "Total number of policy rule hits",
            ["rule", "severity", "mode"],
        )

        # Violations counter
        self.violations = Counter(
            "crashlens_violations_total",
            "Total number of policy violations by severity",
            ["severity"],
        )

        # Traces processed counter
        self.traces_processed = Counter(
            "crashlens_traces_processed_total", "Total number of traces processed"
        )

        # Traces failed counter
        self.traces_failed = Counter(
            "crashlens_traces_failed_total",
            "Total number of traces that failed processing",
            ["reason"],
        )

        # Label overflow counter (used to track cardinality collapse events)
        self.label_overflow = Counter(
            "crashlens_rule_label_overflow_total",
            "Count of rule label overflow events",
        )

    def _init_gauges(self):
        """Initialize gauge metrics."""
        # Guard against static analyzers / None at import time: ensure Gauge callable exists
        if _Gauge is None:
            raise RuntimeError(
                "Prometheus Gauge class not initialized. "
                "Ensure _initialize_metrics_impl was called and prometheus_client was imported successfully."
            )
        Gauge = _Gauge

        # Average latency gauge (sampled)
        self.decision_latency_avg = Gauge(
            "crashlens_decision_latency_avg_seconds",
            "Average rule evaluation latency in seconds (sampled)",
            ["rule"],
        )

        # Last run timestamp
        self.last_run_timestamp = Gauge(
            "crashlens_last_run_timestamp_seconds",
            "Unix timestamp of last CrashLens run",
            ["status"],
        )

        # Push status indicator
        self.metrics_push_status = Gauge(
            "crashlens_metrics_push_status",
            "Metrics push status (1=success, 0=failure)",
        )

    def normalize_severity(self, severity: str) -> str:
        """
        Normalize severity to whitelisted values.

        Args:
            severity: Raw severity string

        Returns:
            Normalized severity from whitelist, or 'info' if unknown
        """
        normalized = severity.lower().strip()
        if normalized in SEVERITY_WHITELIST:
            return normalized
        logger.warning(f"Unknown severity '{severity}', normalizing to 'info'")
        return "info"

    def _get_rule_label(self, rule_name: str) -> str:
        """
        Get rule label with cardinality protection.

        If we've already tracked max_rules unique names, return overflow sentinel.

        Args:
            rule_name: Original rule name

        Returns:
            Rule name if under limit, OVERFLOW_SENTINEL otherwise
        """
        if rule_name in self._tracked_rules:
            return rule_name

        if len(self._tracked_rules) >= self.max_rules:
            # Hit cardinality limit, use overflow sentinel
            self.label_overflow.inc()
            logger.warning(
                f"Rule cardinality limit reached ({self.max_rules}). "
                f"Collapsing '{rule_name}' to '{OVERFLOW_SENTINEL}'"
            )
            return OVERFLOW_SENTINEL

        # Track new rule
        self._tracked_rules.add(rule_name)
        return rule_name
    
    def _get_sample_rate(self, rule_name: str) -> float:
        """
        Get sampling rate for a specific rule.
        
        Returns per-rule rate if configured, otherwise returns global rate.
        
        Args:
            rule_name: Name of the rule to get rate for
        
        Returns:
            Sampling rate for the rule (0.0-1.0)
        
        Example:
            ```python
            metrics = CrashLensMetrics(
                sample_rate=0.1,
                per_rule_rates={"rare_event": 1.0, "common_event": 0.01}
            )
            
            # Common event uses custom 1% rate
            assert metrics._get_sample_rate("common_event") == 0.01
            
            # Rare event uses custom 100% rate
            assert metrics._get_sample_rate("rare_event") == 1.0
            
            # Unknown rule uses global 10% rate
            assert metrics._get_sample_rate("unknown_rule") == 0.1
            ```
        """
        return self._per_rule_rates.get(rule_name, self._sample_rate)

    def record_rule_hit(self, rule_name: str, severity: str, mode: str = "scan"):
        """
        Record a policy rule hit.

        Args:
            rule_name: Name of the rule that was triggered
            severity: Severity level (critical, high, medium, low, info)
            mode: Execution mode (scan, policy-check, etc.)
        
        Note:
            Sampling is applied per-rule. Use per_rule_rates to configure
            different sampling rates for specific rules.
        """
        # Sampling: Skip recording based on per-rule or global sample rate
        rate = self._get_sample_rate(rule_name)
        if random.random() >= rate:
            return
        
        rule_label = self._get_rule_label(rule_name)
        severity_label = self.normalize_severity(severity)
        self.rule_hits.labels(rule=rule_label, severity=severity_label, mode=mode).inc()

    def record_violation(self, severity: str):
        """
        Record a policy violation.

        Args:
            severity: Severity level of the violation
        """
        # Sampling: Skip recording based on sample rate
        if random.random() >= self._sample_rate:
            return
        
        severity_label = self.normalize_severity(severity)
        self.violations.labels(severity=severity_label).inc()

    def record_trace_processed(self, count: int = 1):
        """Record successfully processed traces.

        Args:
            count: Number of traces processed (default: 1)
        """
        # Sampling: Skip recording based on sample rate
        if random.random() >= self._sample_rate:
            return
        
        self.traces_processed.inc(count)

    def record_trace_failed(self, reason: str, count: int = 1):
        """
        Record that traces failed processing.

        Args:
            reason: Reason for failure (parse_error, missing_fields, validation_error, etc.)
            count: Number of traces that failed (default: 1)
        """
        # Sampling: Skip recording based on sample rate
        if random.random() >= self._sample_rate:
            return
        
        self.traces_failed.labels(reason=reason).inc(count)

    def update_decision_latency(
        self, rule_name: str, avg_seconds: float
    ):
        """
        Update average decision latency for a rule.

        Args:
            rule_name: Policy rule identifier
            avg_seconds: Average evaluation time in seconds
        
        Note:
            Max/min latency metrics removed due to sampling.
            With 10% sampling, max would miss 90% of outliers.
            Average remains directionally correct with sampling.
        """
        rule_label = self._get_rule_label(rule_name)
        self.decision_latency_avg.labels(rule=rule_label).set(avg_seconds)

    def update_run_timestamp(self, status: str = "success"):
        """
        Update the last run timestamp.

        Args:
            status: Run status (success, failure, partial)
        """
        import time

        self.last_run_timestamp.labels(status=status).set(time.time())

    def update_push_status(self, success: bool):
        """
        Update the metrics push status indicator.

        Args:
            success: Whether the push succeeded
        """
        self.metrics_push_status.set(1 if success else 0)


def _initialize_metrics_impl(
    enabled: bool = False, max_rules: int = 500, sample_rate: float = 1.0, per_rule_rates: Optional[dict] = None
) -> Optional[CrashLensMetrics]:
    """
    Internal implementation of metrics initialization.

    This function handles:
    1. Kill switch check (CRASHLENS_DISABLE_METRICS)
    2. Lazy import of prometheus_client
    3. Metrics instance creation

    Args:
        enabled: Whether to enable metrics collection
        max_rules: Maximum number of unique rule names
        sample_rate: Global sampling probability (0.0-1.0, default: 1.0)
        per_rule_rates: Optional dict of rule_name -> sample_rate overrides

    Returns:
        CrashLensMetrics instance if enabled and available, None otherwise

    Raises:
        RuntimeError: If enabled=True but prometheus-client is not installed
    """
    global _prometheus_available, _Counter, _Gauge, _CollectorRegistry, _REGISTRY

    # Check kill switch first (highest precedence)
    if os.environ.get("CRASHLENS_DISABLE_METRICS", "").lower() == "true":
        logger.info(
            "Metrics disabled via CRASHLENS_DISABLE_METRICS environment variable"
        )
        return None

    # If not enabled, return None
    if not enabled:
        logger.debug("Metrics not enabled")
        return None

    # Lazy import prometheus_client
    if not _prometheus_available:
        try:
            from prometheus_client import Counter, Gauge, CollectorRegistry, REGISTRY

            _Counter = Counter
            _Gauge = Gauge
            _CollectorRegistry = CollectorRegistry
            _REGISTRY = REGISTRY
            _prometheus_available = True
            logger.info("prometheus_client imported successfully")
        except ImportError as e:
            raise RuntimeError(
                "Metrics enabled but prometheus_client is not installed. "
                "Install with: pip install crashlens[metrics] or pip install prometheus-client>=0.20.0"
            ) from e

    # Create and return metrics instance
    # Note: Multiple initialization calls will reuse existing metrics in REGISTRY
    # This is intentional - Prometheus metrics are singletons per registry
    per_rule_info = f", per_rule_rates={len(per_rule_rates or {})} rules" if per_rule_rates else ""
    logger.info(f"Initializing CrashLens metrics (max_rules={max_rules}, sample_rate={sample_rate}{per_rule_info})")
    try:
        return CrashLensMetrics(max_rules=max_rules, sample_rate=sample_rate, per_rule_rates=per_rule_rates)
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            # Metrics already registered - this is OK for testing
            # Return a new instance that will reuse existing collectors
            logger.warning("Metrics already registered, reusing existing collectors")
            # For production, we should only initialize once
            # For testing, we need to handle this gracefully
            return None  # Signal that metrics are already initialized
        raise


__all__ = [
    "CrashLensMetrics",
    "_initialize_metrics_impl",
]
