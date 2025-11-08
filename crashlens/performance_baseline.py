#!/usr/bin/env python3
"""
Dynamic Performance Baseline Calculation

Calculates P95/P99 baselines from historical log data for adaptive
performance threshold monitoring instead of static thresholds.
"""

import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class PerformanceBaseline:
    """Calculate and compare against dynamic performance baselines"""
    
    def __init__(self, historical_logs: List[Dict[str, Any]]):
        """
        Initialize baseline calculator with historical data.
        
        Args:
            historical_logs: List of log entries from previous period
        """
        self.historical_logs = historical_logs
        self._baselines: Optional[Dict[str, float]] = None
    
    def calculate_baselines(self) -> Dict[str, float]:
        """
        Calculate P95 and P99 baselines for latency, cost, and error rate.
        
        Returns:
            Dictionary with baseline metrics:
            - latency_p95: 95th percentile response time in ms
            - latency_p99: 99th percentile response time in ms
            - cost_p95: 95th percentile cost in USD
            - cost_p99: 99th percentile cost in USD
            - error_rate: Historical error rate (0.0-1.0)
        
        Raises:
            ValueError: If historical logs are empty
        """
        if not self.historical_logs:
            raise ValueError("Cannot calculate baselines from empty historical logs")
        
        # Extract metrics
        latencies = []
        costs = []
        error_count = 0
        
        for entry in self.historical_logs:
            # Latency (response_time_ms or latency_ms)
            latency = entry.get("response_time_ms") or entry.get("latency_ms", 0)
            if latency > 0:
                latencies.append(latency)
            
            # Cost
            cost = entry.get("cost_usd", 0.0)
            if cost > 0:
                costs.append(cost)
            
            # Errors
            if entry.get("error", False) or entry.get("status") == "error":
                error_count += 1
        
        # Calculate percentiles
        baselines = {}
        
        if latencies:
            baselines['latency_p95'] = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            baselines['latency_p99'] = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        else:
            baselines['latency_p95'] = 0.0
            baselines['latency_p99'] = 0.0
        
        if costs:
            baselines['cost_p95'] = statistics.quantiles(costs, n=20)[18]
            baselines['cost_p99'] = statistics.quantiles(costs, n=100)[98]
        else:
            baselines['cost_p95'] = 0.0
            baselines['cost_p99'] = 0.0
        
        # Error rate
        baselines['error_rate'] = error_count / len(self.historical_logs) if self.historical_logs else 0.0
        
        # Cache baselines
        self._baselines = baselines
        
        return baselines
    
    def get_baselines(self) -> Dict[str, float]:
        """
        Get cached baselines (calculate if not already cached).
        
        Returns:
            Dictionary with baseline metrics
        """
        if self._baselines is None:
            self._baselines = self.calculate_baselines()
        return self._baselines
    
    def compare_to_baseline(
        self,
        current_logs: List[Dict[str, Any]],
        deviation_threshold: float = 0.50  # 50% deviation triggers alert
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Compare current logs against baseline with deviation threshold.
        
        Args:
            current_logs: List of log entries from current period
            deviation_threshold: Percentage deviation to trigger alert (0.0-1.0)
                                Default 0.50 means 50% worse than baseline
        
        Returns:
            Tuple of (has_violations, violations_list)
            - has_violations: True if any metric exceeds baseline + deviation
            - violations_list: List of violation dictionaries with details
        
        Example:
            >>> baseline = PerformanceBaseline(historical_logs)
            >>> has_violations, violations = baseline.compare_to_baseline(current_logs, 0.30)
            >>> if has_violations:
            ...     print(f"Found {len(violations)} baseline violations")
        """
        if not current_logs:
            return False, []
        
        baselines = self.get_baselines()
        violations = []
        
        # Calculate current metrics
        latencies = [
            entry.get("response_time_ms") or entry.get("latency_ms", 0)
            for entry in current_logs
            if (entry.get("response_time_ms", 0) > 0 or entry.get("latency_ms", 0) > 0)
        ]
        
        costs = [
            entry.get("cost_usd", 0.0)
            for entry in current_logs
            if entry.get("cost_usd", 0.0) > 0
        ]
        
        error_count = sum(
            1 for entry in current_logs
            if entry.get("error", False) or entry.get("status") == "error"
        )
        
        # Compare latency P95
        if latencies and baselines['latency_p95'] > 0:
            current_p95 = statistics.quantiles(latencies, n=20)[18]
            max_allowed = baselines['latency_p95'] * (1 + deviation_threshold)
            
            if current_p95 > max_allowed:
                pct_increase = ((current_p95 - baselines['latency_p95']) / baselines['latency_p95']) * 100
                violations.append({
                    'metric': 'latency_p95',
                    'baseline': baselines['latency_p95'],
                    'current': current_p95,
                    'deviation_threshold': deviation_threshold,
                    'percent_increase': pct_increase,
                    'description': f"P95 latency {current_p95:.0f}ms is {pct_increase:.1f}% above baseline {baselines['latency_p95']:.0f}ms"
                })
        
        # Compare latency P99
        if latencies and baselines['latency_p99'] > 0 and len(latencies) >= 100:
            current_p99 = statistics.quantiles(latencies, n=100)[98]
            max_allowed = baselines['latency_p99'] * (1 + deviation_threshold)
            
            if current_p99 > max_allowed:
                pct_increase = ((current_p99 - baselines['latency_p99']) / baselines['latency_p99']) * 100
                violations.append({
                    'metric': 'latency_p99',
                    'baseline': baselines['latency_p99'],
                    'current': current_p99,
                    'deviation_threshold': deviation_threshold,
                    'percent_increase': pct_increase,
                    'description': f"P99 latency {current_p99:.0f}ms is {pct_increase:.1f}% above baseline {baselines['latency_p99']:.0f}ms"
                })
        
        # Compare cost P95
        if costs and baselines['cost_p95'] > 0:
            current_p95 = statistics.quantiles(costs, n=20)[18]
            max_allowed = baselines['cost_p95'] * (1 + deviation_threshold)
            
            if current_p95 > max_allowed:
                pct_increase = ((current_p95 - baselines['cost_p95']) / baselines['cost_p95']) * 100
                violations.append({
                    'metric': 'cost_p95',
                    'baseline': baselines['cost_p95'],
                    'current': current_p95,
                    'deviation_threshold': deviation_threshold,
                    'percent_increase': pct_increase,
                    'description': f"P95 cost ${current_p95:.4f} is {pct_increase:.1f}% above baseline ${baselines['cost_p95']:.4f}"
                })
        
        # Compare cost P99
        if costs and baselines['cost_p99'] > 0 and len(costs) >= 100:
            current_p99 = statistics.quantiles(costs, n=100)[98]
            max_allowed = baselines['cost_p99'] * (1 + deviation_threshold)
            
            if current_p99 > max_allowed:
                pct_increase = ((current_p99 - baselines['cost_p99']) / baselines['cost_p99']) * 100
                violations.append({
                    'metric': 'cost_p99',
                    'baseline': baselines['cost_p99'],
                    'current': current_p99,
                    'deviation_threshold': deviation_threshold,
                    'percent_increase': pct_increase,
                    'description': f"P99 cost ${current_p99:.4f} is {pct_increase:.1f}% above baseline ${baselines['cost_p99']:.4f}"
                })
        
        # Compare error rate
        if baselines['error_rate'] > 0:
            current_error_rate = error_count / len(current_logs)
            # For error rate, any increase above baseline is concerning
            # Use absolute threshold (e.g., +10 percentage points) rather than relative
            absolute_threshold = 0.10  # 10 percentage points
            
            if current_error_rate > baselines['error_rate'] + absolute_threshold:
                pct_point_increase = (current_error_rate - baselines['error_rate']) * 100
                violations.append({
                    'metric': 'error_rate',
                    'baseline': baselines['error_rate'],
                    'current': current_error_rate,
                    'deviation_threshold': absolute_threshold,
                    'percent_increase': pct_point_increase,
                    'description': f"Error rate {current_error_rate:.2%} is {pct_point_increase:.1f} percentage points above baseline {baselines['error_rate']:.2%}"
                })
        
        return len(violations) > 0, violations
    
    def generate_synthetic_violations(
        self,
        current_logs: List[Dict[str, Any]],
        deviation_threshold: float = 0.50
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic violation records for baseline deviations.
        
        Creates violation objects compatible with guard report format that can be
        injected into the violations list for reporting.
        
        Args:
            current_logs: List of log entries from current period
            deviation_threshold: Percentage deviation to trigger alert (0.0-1.0)
        
        Returns:
            List of synthetic violation dictionaries in guard report format:
            {
                'id': str,           # e.g., 'baseline_latency_p95'
                'name': str,         # Human-readable name
                'severity': str,     # 'fatal' for baseline violations
                'description': str,  # Detailed description with metrics
                'count': int,        # Always 1 per violation type
                'examples': list,    # Empty (baseline violations don't have log examples)
                'baseline_value': float,      # Historical baseline
                'current_value': float,       # Current measured value
                'percent_increase': float,    # % over baseline
                'deviation_threshold': float  # Threshold that was exceeded
            }
        
        Example:
            >>> baseline = PerformanceBaseline(historical_logs)
            >>> violations = baseline.generate_synthetic_violations(current_logs, 0.30)
            >>> for v in violations:
            ...     print(f"{v['name']}: {v['description']}")
        """
        has_violations, raw_violations = self.compare_to_baseline(
            current_logs, deviation_threshold
        )
        
        if not has_violations:
            return []
        
        synthetic_violations = []
        
        for violation in raw_violations:
            metric = violation['metric']
            
            # Create guard-compatible violation record
            synthetic_violation = {
                'id': f"baseline_{metric}",
                'name': f"Baseline: {metric.upper().replace('_', ' ')}",
                'severity': 'fatal',
                'description': violation['description'],
                'count': 1,
                'examples': [],
                # Additional baseline-specific fields
                'baseline_value': violation['baseline'],
                'current_value': violation['current'],
                'percent_increase': violation['percent_increase'],
                'deviation_threshold': violation['deviation_threshold']
            }
            
            synthetic_violations.append(synthetic_violation)
        
        return synthetic_violations
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of baselines.
        
        Returns:
            Formatted string with baseline metrics
        """
        baselines = self.get_baselines()
        
        summary = "Dynamic Performance Baselines\n"
        summary += "=" * 40 + "\n"
        summary += f"Historical samples: {len(self.historical_logs):,}\n\n"
        summary += f"Latency P95: {baselines['latency_p95']:.0f}ms\n"
        summary += f"Latency P99: {baselines['latency_p99']:.0f}ms\n"
        summary += f"Cost P95: ${baselines['cost_p95']:.4f}\n"
        summary += f"Cost P99: ${baselines['cost_p99']:.4f}\n"
        summary += f"Error Rate: {baselines['error_rate']:.2%}\n"
        
        return summary


def load_baseline_from_file(filepath: Path) -> PerformanceBaseline:
    """
    Load historical logs from JSONL file and create baseline calculator.
    
    Args:
        filepath: Path to JSONL file with historical log data
    
    Returns:
        PerformanceBaseline instance ready for comparison
    
    Raises:
        FileNotFoundError: If filepath doesn't exist
        ValueError: If file is empty or invalid JSONL
    """
    from .guard import load_jsonl
    
    if not filepath.exists():
        raise FileNotFoundError(f"Baseline file not found: {filepath}")
    
    logs = list(load_jsonl(str(filepath)))
    
    if not logs:
        raise ValueError(f"Baseline file is empty: {filepath}")
    
    return PerformanceBaseline(logs)
