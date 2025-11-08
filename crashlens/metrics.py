"""
CrashLens Metrics Collection for Prometheus

Collects and pushes metrics about guard runs to Prometheus Pushgateway.
"""

from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, push_to_gateway
import time
from typing import Dict, Any, Optional
import click


class MetricsCollector:
    """Collects metrics from guard runs and pushes to Pushgateway."""
    
    def __init__(self, pushgateway_url: str = 'localhost:9091', job_name: str = 'crashlens-guard'):
        """
        Initialize metrics collector.
        
        Args:
            pushgateway_url: URL of Prometheus Pushgateway
            job_name: Job name for metrics grouping
        """
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name
        self.registry = CollectorRegistry()
        
        # Define metrics
        self.guard_runs_total = Counter(
            'crashlens_guard_runs_total',
            'Total number of guard command executions',
            ['status', 'severity'],
            registry=self.registry
        )
        
        self.guard_violations_total = Counter(
            'crashlens_guard_violations_total',
            'Total policy violations detected',
            ['rule_id', 'severity'],
            registry=self.registry
        )
        
        self.guard_duration_seconds = Histogram(
            'crashlens_guard_duration_seconds',
            'Time spent executing guard command',
            registry=self.registry
        )
        
        self.guard_logs_processed = Counter(
            'crashlens_guard_logs_processed_total',
            'Total log entries processed',
            registry=self.registry
        )
        
        self.guard_rules_evaluated = Counter(
            'crashlens_guard_rules_evaluated_total',
            'Total rules evaluated',
            ['rule_id'],
            registry=self.registry
        )
        
        self.guard_last_run_timestamp = Gauge(
            'crashlens_guard_last_run_timestamp',
            'Timestamp of last guard run',
            registry=self.registry
        )
        
        self.guard_active_rules = Gauge(
            'crashlens_guard_active_rules',
            'Number of active rules in last run',
            registry=self.registry
        )
    
    def record_guard_run(
        self,
        status: str,
        violations: Dict[str, Any],
        duration: float,
        logs_processed: int,
        severity: str = 'error',
        rules_count: int = 0
    ):
        """
        Record metrics from a guard run.
        
        Args:
            status: 'success' or 'failure'
            violations: Dict of rule_id -> violation data
            duration: Execution time in seconds
            logs_processed: Number of log entries processed
            severity: Severity threshold used
            rules_count: Number of rules evaluated
        """
        # Record run
        self.guard_runs_total.labels(status=status, severity=severity).inc()
        
        # Record duration
        self.guard_duration_seconds.observe(duration)
        
        # Record logs processed
        self.guard_logs_processed.inc(logs_processed)
        
        # Record violations
        for rule_id, rule_data in violations.items():
            rule_severity = rule_data.get('severity', 'unknown')
            violation_count = rule_data.get('count', 0)
            
            if violation_count > 0:
                self.guard_violations_total.labels(
                    rule_id=rule_id,
                    severity=rule_severity
                ).inc(violation_count)
            
            # Record rule evaluation
            self.guard_rules_evaluated.labels(rule_id=rule_id).inc()
        
        # Update gauges
        self.guard_last_run_timestamp.set_to_current_time()
        if rules_count > 0:
            self.guard_active_rules.set(rules_count)
    
    def push(self):
        """Push metrics to Pushgateway."""
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=self.job_name,
                registry=self.registry
            )
            click.echo(f"✅ Metrics pushed to {self.pushgateway_url}", err=True)
        except Exception as e:
            click.echo(f"⚠️  Failed to push metrics: {e}", err=True)
            # Don't fail the application if metrics push fails


def test_metrics():
    """Test metrics collection and push."""
    collector = MetricsCollector()
    
    # Simulate a guard run
    collector.record_guard_run(
        status='success',
        violations={
            'RL001': {'severity': 'fatal', 'count': 3},
            'RL002': {'severity': 'error', 'count': 5}
        },
        duration=2.5,
        logs_processed=100,
        severity='error',
        rules_count=6
    )
    
    collector.push()


if __name__ == '__main__':
    test_metrics()
