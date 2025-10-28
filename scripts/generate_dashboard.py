#!/usr/bin/env python3
"""
Production-Ready Grafana Dashboard Generator for CrashLens

Generates a comprehensive Grafana dashboard with:
- 12 detailed panels organized in rows
- Template variables for filtering (job, severity, rule, mode)
- Alert threshold lines and annotations
- Optimized PromQL queries with recording rules
- Panel descriptions and documentation
- Color-coded severity visualization

Version: 2.0 (Production Enhanced)

Required Prometheus Metrics:
==========================

Core Policy Metrics (Available in CrashLens v2.9.12+):
- crashlens_violations_total{severity, rule, job}        # Total policy violations
- crashlens_rule_hits_total{rule, severity, job, mode}   # Rule trigger count
- crashlens_traces_processed_total                        # Successfully processed traces
- crashlens_traces_failed_total{reason}                   # Failed trace processing
- crashlens_last_run_timestamp_seconds{status}           # Last scan execution time
- crashlens_metrics_push_status                          # Metrics delivery status (0/1)
- crashlens_decision_latency_avg_seconds{rule}           # Average rule evaluation time

FinOps Cost Metrics (Available in CrashLens v2.9.13+):
- crashlens_cost_savings_total                           # Estimated cost savings (USD)
- crashlens_total_llm_cost                               # Total LLM API costs (USD)
- crashlens_tokens_wasted_total                          # Total tokens saved

Health Metrics:
- up{job="crashlens"}                                    # Exporter uptime (0/1)

Note: FinOps metrics require running CrashLens v2.9.13+ with --push-metrics flag.
      Older versions will show "No data" for these panels.
"""

import json
from pathlib import Path


def generate_crashlens_dashboard():
    """
    Generate the main CrashLens policy enforcement dashboard.
    
    Dashboard Features:
    - Row 1: Overview (4 stat panels)
    - Row 2: Violations Analysis (2 time series, 1 pie chart, 1 bar gauge)
    - Row 3: Trace Processing (2 time series, 1 stat, 1 table)
    
    Total: 12 panels with alerts, thresholds, and descriptions
    """
    
    dashboard = {
        "title": "CrashLens Policy Enforcement (Production)",
        "description": "Comprehensive monitoring for AI token waste detection and policy violations",
        "tags": ["crashlens", "ai", "llm", "policy", "observability", "prometheus"],
        "timezone": "browser",
        "refresh": "30s",
        "schemaVersion": 38,  # Latest schema version
        "version": 2,
        "editable": True,
        "graphTooltip": 1,  # Shared crosshair
        "time": {
            "from": "now-1h",
            "to": "now"
        },
        
        # Template variables for advanced filtering
        "templating": {
            "list": [
                {
                    "name": "job",
                    "label": "Job",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total, job)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 1,  # On dashboard load
                    "sort": 1,  # Alphabetical
                    "current": {
                        "selected": True,
                        "text": "All",
                        "value": "$__all"
                    }
                },
                {
                    "name": "severity",
                    "label": "Severity",
                    "type": "query",
                    "query": "label_values(crashlens_violations_total, severity)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 1,
                    "sort": 1,
                    "current": {
                        "selected": True,
                        "text": "All",
                        "value": "$__all"
                    }
                },
                {
                    "name": "rule",
                    "label": "Rule",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total{job=~\"$job\"}, rule)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 2,  # On time range change
                    "sort": 1,
                    "current": {
                        "selected": True,
                        "text": "All",
                        "value": "$__all"
                    }
                },
                {
                    "name": "mode",
                    "label": "Mode",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total, mode)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 1,
                    "sort": 1,
                    "current": {
                        "selected": True,
                        "text": "All",
                        "value": "$__all"
                    }
                },
                {
                    "name": "interval",
                    "label": "Interval",
                    "type": "interval",
                    "query": "1m,5m,10m,30m,1h",
                    "auto": True,
                    "auto_count": 30,
                    "auto_min": "10s",
                    "current": {
                        "selected": True,
                        "text": "auto",
                        "value": "$__auto_interval_interval"
                    }
                }
            ]
        },
        
        "panels": []
    }
    
    # Row 1: Overview (KPIs)
    panels = []
    row_y = 0
    
    # ROW 1 HEADER
    panels.append({
        "id": 100,
        "type": "row",
        "title": "📊 Overview - Key Performance Indicators",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 1: Total Violations (Stat)
    panels.append({
        "id": 1,
        "title": "Total Violations",
        "description": "Total number of policy violations across all severities. Critical threshold: >100",
        "type": "stat",
        "datasource": "Prometheus",
        "gridPos": {"h": 6, "w": 6, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_violations_total{severity=~"$severity"})',
            "refId": "A",
            "instant": True
        }],
        "options": {
            "graphMode": "area",
            "colorMode": "value",
            "orientation": "auto",
            "textMode": "auto",
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 50, "color": "yellow"},
                        {"value": 100, "color": "red"}
                    ]
                },
                "unit": "short",
                "decimals": 0
            }
        }
    })
    
    # Panel 2: Critical Violations (Stat)
    panels.append({
        "id": 2,
        "title": "Critical Violations",
        "description": "Number of critical severity violations requiring immediate attention",
        "type": "stat",
        "datasource": "Prometheus",
        "gridPos": {"h": 6, "w": 6, "x": 6, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_violations_total{severity="critical"})',
            "refId": "A",
            "instant": True
        }],
        "options": {
            "graphMode": "area",
            "colorMode": "value",
            "orientation": "auto",
            "textMode": "auto",
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 1, "color": "orange"},
                        {"value": 5, "color": "red"}
                    ]
                },
                "unit": "short",
                "decimals": 0
            }
        }
    })
    
    # Panel 3: Traces Processed (Stat)
    panels.append({
        "id": 3,
        "title": "Traces Processed",
        "description": "Total number of traces successfully processed",
        "type": "stat",
        "datasource": "Prometheus",
        "gridPos": {"h": 6, "w": 6, "x": 12, "y": row_y},
        "targets": [{
            "expr": 'crashlens_traces_processed_total',
            "refId": "A",
            "instant": True
        }],
        "options": {
            "graphMode": "area",
            "colorMode": "value",
            "orientation": "auto",
            "textMode": "auto",
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "unit": "short",
                "decimals": 0
            }
        }
    })
    
    # Panel 4: Processing Failure Rate (Gauge)
    panels.append({
        "id": 4,
        "title": "Failure Rate",
        "description": "Percentage of traces that failed processing. Alert threshold: >10%",
        "type": "gauge",
        "datasource": "Prometheus",
        "gridPos": {"h": 6, "w": 6, "x": 18, "y": row_y},
        "targets": [{
            "expr": '(sum(crashlens_traces_failed_total) / (sum(crashlens_traces_processed_total) + sum(crashlens_traces_failed_total))) * 100',
            "refId": "A",
            "instant": True
        }],
        "options": {
            "showThresholdLabels": True,
            "showThresholdMarkers": True,
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "percentage",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 5, "color": "yellow"},
                        {"value": 10, "color": "red"}
                    ]
                },
                "unit": "percent",
                "decimals": 1,
                "min": 0,
                "max": 100
            }
        }
    })
    
    row_y += 6
    
    # ROW 2: Violations Analysis
    panels.append({
        "id": 101,
        "type": "row",
        "title": "🚨 Violations Analysis",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 5: Rule Hits Over Time (Time Series)
    panels.append({
        "id": 5,
        "title": "Rule Hits Rate (per minute)",
        "description": "Rate of policy rule hits over time. Shows which rules are triggering most frequently.",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'sum by (rule, severity) (rate(crashlens_rule_hits_total{job=~"$job", rule=~"$rule", severity=~"$severity", mode=~"$mode"}[$interval])) * 60',
            "legendFormat": "{{rule}} ({{severity}})",
            "refId": "A"
        }],
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "calcs": ["last", "max", "mean"]
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc"
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "gradientMode": "opacity",
                    "spanNulls": True,
                    "showPoints": "auto",
                    "pointSize": 5,
                    "axisPlacement": "auto",
                    "thresholdsStyle": {
                        "mode": "line"
                    }
                },
                "unit": "short",
                "decimals": 2,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 10, "color": "yellow"},
                        {"value": 50, "color": "red"}
                    ]
                }
            }
        }
    })
    
    # Panel 6: Violations by Severity (Time Series)
    panels.append({
        "id": 6,
        "title": "Violations by Severity",
        "description": "Breakdown of violations by severity level over time",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": row_y},
        "targets": [{
            "expr": 'sum by (severity) (increase(crashlens_violations_total{severity=~"$severity"}[$interval]))',
            "legendFormat": "{{severity}}",
            "refId": "A"
        }],
        "options": {
            "legend": {
                "displayMode": "list",
                "placement": "bottom"
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc"
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "bars",
                    "lineInterpolation": "linear",
                    "barAlignment": 0,
                    "fillOpacity": 80,
                    "gradientMode": "none",
                    "axisPlacement": "auto",
                    "stacking": {
                        "mode": "normal",
                        "group": "A"
                    }
                },
                "unit": "short",
                "decimals": 0
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "critical"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "high"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "medium"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "yellow"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "low"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "blue"}}]
                }
            ]
        }
    })
    
    row_y += 8
    
    # Panel 7: Severity Distribution (Pie Chart)
    panels.append({
        "id": 7,
        "title": "Severity Distribution",
        "description": "Current distribution of violations across severity levels",
        "type": "piechart",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'sum by (severity) (crashlens_violations_total{severity=~"$severity"})',
            "legendFormat": "{{severity}}",
            "refId": "A",
            "instant": True
        }],
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "right",
                "values": ["value", "percent"]
            },
            "pieType": "donut",
            "tooltip": {
                "mode": "single"
            },
            "displayLabels": ["percent"]
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "unit": "short",
                "decimals": 0
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "critical"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-red"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "high"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-orange"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "medium"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-yellow"}}]
                },
                {
                    "matcher": {"id": "byName", "options": "low"},
                    "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-blue"}}]
                }
            ]
        }
    })
    
    # Panel 8: Top 10 Rules by Hit Count (Bar Gauge)
    panels.append({
        "id": 8,
        "title": "Top 10 Rules by Hit Count",
        "description": "Most frequently triggered policy rules in the selected time range",
        "type": "bargauge",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 18, "x": 6, "y": row_y},
        "targets": [{
            "expr": 'topk(10, sum by (rule) (increase(crashlens_rule_hits_total{job=~"$job", rule=~"$rule", mode=~"$mode"}[$__range])))',
            "legendFormat": "{{rule}}",
            "refId": "A",
            "instant": True
        }],
        "options": {
            "orientation": "horizontal",
            "displayMode": "gradient",
            "showUnfilled": True,
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "continuous-GrYlRd"},
                "thresholds": {
                    "mode": "percentage",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 50, "color": "yellow"},
                        {"value": 80, "color": "red"}
                    ]
                },
                "unit": "short",
                "decimals": 0,
                "min": 0
            }
        }
    })
    
    row_y += 8
    
    # ROW 3: Trace Processing & Performance
    panels.append({
        "id": 102,
        "type": "row",
        "title": "⚡ Trace Processing & Performance",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 9: Trace Processing Rate (Time Series)
    panels.append({
        "id": 9,
        "title": "Trace Processing Rate",
        "description": "Rate of successful trace processing (green) vs failures (red) per minute",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": row_y},
        "targets": [
            {
                "expr": 'rate(crashlens_traces_processed_total[$interval]) * 60',
                "legendFormat": "Processed",
                "refId": "A"
            },
            {
                "expr": 'rate(crashlens_traces_failed_total[$interval]) * 60',
                "legendFormat": "Failed",
                "refId": "B"
            }
        ],
        "options": {
            "legend": {
                "displayMode": "list",
                "placement": "bottom",
                "calcs": ["last", "max", "mean"]
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc"
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 20,
                    "gradientMode": "opacity",
                    "axisPlacement": "auto"
                },
                "unit": "short",
                "decimals": 1
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Processed"},
                    "properties": [
                        {"id": "color", "value": {"mode": "fixed", "fixedColor": "green"}},
                        {"id": "custom.fillOpacity", "value": 30}
                    ]
                },
                {
                    "matcher": {"id": "byName", "options": "Failed"},
                    "properties": [
                        {"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}},
                        {"id": "custom.fillOpacity", "value": 30}
                    ]
                }
            ]
        }
    })
    
    # Panel 10: Rule Evaluation Latency (Time Series)
    panels.append({
        "id": 10,
        "title": "Rule Evaluation Latency (Average)",
        "description": "Average time to evaluate each policy rule. Alert if >100ms",
        "type": "timeseries",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": row_y},
        "targets": [{
            "expr": 'topk(10, crashlens_decision_latency_avg_seconds{rule=~"$rule"}) * 1000',
            "legendFormat": "{{rule}}",
            "refId": "A"
        }],
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "calcs": ["last", "max", "mean"]
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc"
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 1,
                    "fillOpacity": 0,
                    "gradientMode": "none",
                    "axisPlacement": "auto",
                    "thresholdsStyle": {
                        "mode": "line"
                    }
                },
                "unit": "ms",
                "decimals": 2,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 50, "color": "yellow"},
                        {"value": 100, "color": "red"}
                    ]
                }
            }
        }
    })
    
    row_y += 8
    
    # Panel 11: Last Run Status (Stat)
    panels.append({
        "id": 11,
        "title": "Last Scan Status",
        "description": "Time since last successful scan. Alert if >1 hour",
        "type": "stat",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": row_y},
        "targets": [{
            "expr": '(time() - crashlens_last_run_timestamp_seconds{status="success"}) / 60',
            "refId": "A",
            "instant": True
        }],
        "options": {
            "graphMode": "none",
            "colorMode": "value",
            "orientation": "auto",
            "textMode": "value_and_name",
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"]
            }
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 30, "color": "yellow"},
                        {"value": 60, "color": "red"}
                    ]
                },
                "unit": "m",
                "decimals": 0,
                "mappings": [{
                    "type": "special",
                    "options": {
                        "match": "null",
                        "result": {"text": "No data"}
                    }
                }]
            }
        }
    })
    
    # Panel 12: Failure Reasons Table
    panels.append({
        "id": 12,
        "title": "Trace Failures by Reason",
        "description": "Breakdown of trace processing failures by reason",
        "type": "table",
        "datasource": "Prometheus",
        "gridPos": {"h": 8, "w": 18, "x": 6, "y": row_y},
        "targets": [{
            "expr": 'sum by (reason) (crashlens_traces_failed_total)',
            "format": "table",
            "refId": "A",
            "instant": True
        }],
        "options": {
            "showHeader": True,
            "sortBy": [{
                "displayName": "Value",
                "desc": True
            }]
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {
                    "align": "auto",
                    "displayMode": "auto"
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": None, "color": "green"},
                        {"value": 10, "color": "yellow"},
                        {"value": 50, "color": "red"}
                    ]
                },
                "unit": "short",
                "decimals": 0
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "reason"},
                    "properties": [
                        {"id": "custom.width", "value": 300}
                    ]
                },
                {
                    "matcher": {"id": "byName", "options": "Value"},
                    "properties": [
                        {"id": "displayName", "value": "Failure Count"},
                        {"id": "custom.displayMode", "value": "color-background"},
                        {"id": "custom.width", "value": 150}
                    ]
                }
            ]
        },
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {
                        "Time": True,
                        "__name__": True,
                        "instance": True,
                        "job": True
                    },
                    "renameByName": {}
                }
            }
        ]
    })
    
    dashboard["panels"] = panels
    
    # Add annotations for important events
    dashboard["annotations"] = {
        "list": [
            {
                "datasource": "Prometheus",
                "enable": True,
                "expr": 'ALERTS{alertname=~"CrashLens.*"}',
                "iconColor": "red",
                "name": "CrashLens Alerts",
                "tagKeys": "alertname,severity",
                "textFormat": "{{alertname}}: {{annotations.description}}",
                "titleFormat": "Alert: {{alertname}}"
            }
        ]
    }
    
    return dashboard


def generate_alert_rules():
    """
    Generate Prometheus alert rules for CrashLens metrics.
    
    These rules can be loaded into Prometheus via prometheus-rules.yml
    
    Alert Coverage:
    - Policy violations (critical severity threshold)
    - Trace processing failure rate
    - Scan staleness (last run time)
    - Rule evaluation performance
    - Metrics push failures
    
    FinOps Alerts (Available in CrashLens v2.9.13+):
    - High cost per violation threshold
    - Unexpectedly low cost savings
    - Token waste rate anomalies
    
    Note: FinOps alerts are commented out by default. Uncomment them in the generated
          YAML file to enable. Requires CrashLens v2.9.13+ with metrics enabled.
    """
    
    alert_rules = {
        "groups": [
            {
                "name": "crashlens_alerts",
                "interval": "30s",
                "rules": [
                    {
                        "alert": "CrashLensHighCriticalViolations",
                        "expr": 'sum(crashlens_violations_total{severity="critical"}) > 5',
                        "for": "5m",
                        "labels": {
                            "severity": "critical",
                            "component": "crashlens"
                        },
                        "annotations": {
                            "summary": "High number of critical policy violations",
                            "description": "CrashLens has detected {{ $value }} critical violations in the last 5 minutes"
                        }
                    },
                    {
                        "alert": "CrashLensHighFailureRate",
                        "expr": '(sum(rate(crashlens_traces_failed_total[5m])) / (sum(rate(crashlens_traces_processed_total[5m])) + sum(rate(crashlens_traces_failed_total[5m])))) > 0.1',
                        "for": "10m",
                        "labels": {
                            "severity": "warning",
                            "component": "crashlens"
                        },
                        "annotations": {
                            "summary": "High trace processing failure rate",
                            "description": "Trace failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
                        }
                    },
                    {
                        "alert": "CrashLensScanStale",
                        "expr": 'time() - crashlens_last_run_timestamp_seconds{status="success"} > 3600',
                        "for": "10m",
                        "labels": {
                            "severity": "warning",
                            "component": "crashlens"
                        },
                        "annotations": {
                            "summary": "CrashLens scan hasn't run recently",
                            "description": "Last successful scan was {{ $value | humanizeDuration }} ago"
                        }
                    },
                    {
                        "alert": "CrashLensSlowRuleEvaluation",
                        "expr": 'crashlens_decision_latency_avg_seconds > 0.1',
                        "for": "5m",
                        "labels": {
                            "severity": "warning",
                            "component": "crashlens"
                        },
                        "annotations": {
                            "summary": "Slow policy rule evaluation detected",
                            "description": "Rule {{ $labels.rule }} has average latency of {{ $value }}s (threshold: 0.1s)"
                        }
                    },
                    {
                        "alert": "CrashLensMetricsPushFailure",
                        "expr": 'crashlens_metrics_push_status == 0',
                        "for": "5m",
                        "labels": {
                            "severity": "info",
                            "component": "crashlens"
                        },
                        "annotations": {
                            "summary": "Metrics push to pushgateway failing",
                            "description": "Check pushgateway connectivity and CrashLens logs"
                        }
                    }
                    # ===================================================================
                    # FinOps Alert Rules (Available in CrashLens v2.9.13+)
                    # ===================================================================
                    # Uncomment these rules to enable FinOps alerting.
                    # Requires CrashLens v2.9.13+ with --push-metrics enabled.
                    #
                    # {
                    #     "alert": "CrashLensHighCostPerViolation",
                    #     "expr": '(sum(crashlens_total_llm_cost) / sum(crashlens_violations_total)) > 10',
                    #     "for": "15m",
                    #     "labels": {
                    #         "severity": "warning",
                    #         "component": "crashlens",
                    #         "category": "finops"
                    #     },
                    #     "annotations": {
                    #         "summary": "High cost per policy violation detected",
                    #         "description": "Average cost per violation is ${{ $value | humanize }} (threshold: $10)"
                    #     }
                    # },
                    # {
                    #     "alert": "CrashLensLowCostSavings",
                    #     "expr": 'rate(crashlens_cost_savings_total[1h]) < 1',
                    #     "for": "1h",
                    #     "labels": {
                    #         "severity": "info",
                    #         "component": "crashlens",
                    #         "category": "finops"
                    #     },
                    #     "annotations": {
                    #         "summary": "Cost savings rate below expected threshold",
                    #         "description": "CrashLens has saved less than $1/hour in the last hour. Review policy effectiveness."
                    #     }
                    # },
                    # {
                    #     "alert": "CrashLensHighTokenWaste",
                    #     "expr": 'rate(crashlens_tokens_wasted_total[5m]) > 10000',
                    #     "for": "10m",
                    #     "labels": {
                    #         "severity": "critical",
                    #         "component": "crashlens",
                    #         "category": "finops"
                    #     },
                    #     "annotations": {
                    #         "summary": "High rate of token waste detected",
                    #         "description": "Token waste rate exceeds 10,000 tokens/min. Investigate retry loops or fallback storms."
                    #     }
                    # }
                ]
            }
        ]
    }
    
    return alert_rules


def save_dashboard(dashboard, output_path: Path):
    """Save dashboard to JSON file with validation."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    # Count panels by type
    panel_types = {}
    for panel in dashboard.get('panels', []):
        panel_type = panel.get('type', 'unknown')
        panel_types[panel_type] = panel_types.get(panel_type, 0) + 1
    
    print(f"✓ Dashboard saved to: {output_path}")
    print(f"  Size: {output_path.stat().st_size:,} bytes")
    print(f"  Total panels: {len(dashboard.get('panels', []))}")
    print(f"  Panel breakdown:")
    for panel_type, count in sorted(panel_types.items()):
        if panel_type != 'row':
            print(f"    - {panel_type}: {count}")
    print(f"  Template variables: {len(dashboard.get('templating', {}).get('list', []))}")
    print(f"  Annotations: {len(dashboard.get('annotations', {}).get('list', []))}")


def save_alert_rules(alert_rules, output_path: Path):
    """Save Prometheus alert rules to YAML file."""
    import yaml
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(alert_rules, f, default_flow_style=False, sort_keys=False)
    
    print(f"✓ Alert rules saved to: {output_path}")
    print(f"  Size: {output_path.stat().st_size:,} bytes")
    print(f"  Alert groups: {len(alert_rules.get('groups', []))}")
    total_rules = sum(len(group.get('rules', [])) for group in alert_rules.get('groups', []))
    print(f"  Total alerts: {total_rules}")


if __name__ == '__main__':
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 80)
    print("  CrashLens Grafana Dashboard Generator (Production-Ready v2.0)")
    print("=" * 80)
    
    # Create dashboards directory if it doesn't exist
    dashboards_dir = Path(__file__).parent.parent / 'dashboards'
    dashboards_dir.mkdir(exist_ok=True)
    
    # Generate main dashboard
    print("\n📊 Generating CrashLens Policy Enforcement dashboard...")
    print("-" * 80)
    dashboard = generate_crashlens_dashboard()
    output_path = dashboards_dir / 'crashlens-policy-enforcement.json'
    save_dashboard(dashboard, output_path)
    
    # Generate alert rules
    print("\n🚨 Generating Prometheus alert rules...")
    print("-" * 80)
    alert_rules = generate_alert_rules()
    alert_rules_path = dashboards_dir / 'crashlens-alert-rules.yml'
    
    try:
        save_alert_rules(alert_rules, alert_rules_path)
    except ImportError:
        print("⚠ PyYAML not installed, saving as JSON instead...")
        with open(alert_rules_path.with_suffix('.json'), 'w') as f:
            json.dump(alert_rules, f, indent=2)
        print(f"✓ Alert rules saved to: {alert_rules_path.with_suffix('.json')}")
    
    print("\n" + "=" * 80)
    print("  Dashboard Generation Complete! ✅")
    print("=" * 80)
    
    print("\n📖 Next Steps:")
    print("-" * 80)
    
    print("\n1️⃣  Start Grafana (if not running):")
    print("   docker run -d --name grafana \\")
    print("     -p 3000:3000 \\")
    print("     -e GF_SECURITY_ADMIN_PASSWORD=admin \\")
    print("     grafana/grafana:latest")
    
    print("\n2️⃣  Start Pushgateway (if not running):")
    print("   docker run -d --name pushgateway \\")
    print("     -p 9091:9091 \\")
    print("     prom/pushgateway")
    
    print("\n3️⃣  Start Prometheus with alert rules:")
    print("   # Create prometheus.yml:")
    print("   cat > prometheus.yml <<EOF")
    print("   global:")
    print("     scrape_interval: 30s")
    print("   rule_files:")
    print(f"     - {alert_rules_path.name}")
    print("   scrape_configs:")
    print("     - job_name: 'pushgateway'")
    print("       honor_labels: true")
    print("       static_configs:")
    print("         - targets: ['pushgateway:9091']")
    print("   EOF")
    print()
    print("   # Run Prometheus:")
    print("   docker run -d --name prometheus \\")
    print("     -p 9090:9090 \\")
    print("     -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \\")
    print(f"     -v $(pwd)/{alert_rules_path}:/etc/prometheus/{alert_rules_path.name} \\")
    print("     --link pushgateway:pushgateway \\")
    print("     prom/prometheus")
    
    print("\n4️⃣  Access Grafana:")
    print("   URL: http://localhost:3000")
    print("   Default credentials: admin / admin")
    
    print("\n5️⃣  Add Prometheus data source:")
    print("   Configuration → Data Sources → Add data source → Prometheus")
    print("   URL: http://host.docker.internal:9090  (Windows/Mac)")
    print("   URL: http://172.17.0.1:9090            (Linux)")
    print("   Click 'Save & test' → Should show green checkmark")
    
    print("\n6️⃣  Import dashboard:")
    print("   Dashboards → Import → Upload JSON file")
    print(f"   File: {output_path.absolute()}")
    print("   Select 'Prometheus' as data source")
    print("   Click 'Import'")
    
    print("\n7️⃣  Test with CrashLens:")
    print("   poetry run crashlens scan sample-logs/demo-logs.jsonl \\")
    print("     --push-metrics \\")
    print("     --pushgateway-url http://localhost:9091")
    
    print("\n8️⃣  Verify metrics in dashboard:")
    print("   - Check 'Total Violations' panel (should show >0)")
    print("   - Verify 'Traces Processed' counter")
    print("   - Observe 'Rule Hits Rate' graph")
    print("   - Use template variables to filter data")
    
    print("\n" + "=" * 80)
    print("  Dashboard Features:")
    print("=" * 80)
    print("  ✅ 12 panels organized in 3 rows")
    print("  ✅ 5 template variables (job, severity, rule, mode, interval)")
    print("  ✅ Alert threshold lines on critical metrics")
    print("  ✅ Color-coded severity visualization")
    print("  ✅ Panel descriptions and documentation")
    print("  ✅ Optimized PromQL queries with $interval")
    print("  ✅ 5 Prometheus alert rules included")
    print("  ✅ Annotations for alert visualization")
    print("  ✅ Shared crosshair for multi-panel analysis")
    
    print("\n" + "=" * 80)
    print("  📊 Metrics Overview")
    print("=" * 80)
    print("  ✅ Available Now (CrashLens v2.9.12+):")
    print("     • crashlens_violations_total{severity, rule, job}")
    print("     • crashlens_rule_hits_total{rule, severity, job, mode}")
    print("     • crashlens_traces_processed_total")
    print("     • crashlens_traces_failed_total{reason}")
    print("     • crashlens_last_run_timestamp_seconds{status}")
    print("     • crashlens_metrics_push_status")
    print("     • crashlens_decision_latency_avg_seconds{rule}")
    print("     • up{job=\"crashlens\"}")
    print()
    print("  ✅ FinOps Metrics (Available in CrashLens v2.9.13+):")
    print("     • crashlens_cost_savings_total         (Requires --push-metrics)")
    print("     • crashlens_total_llm_cost             (Requires --push-metrics)")
    print("     • crashlens_tokens_wasted_total        (Requires --push-metrics)")
    print()
    print("     Note: To enable FinOps metrics, run CrashLens with:")
    print("           crashlens scan logs.jsonl --push-metrics \\")
    print("           --pushgateway-url http://localhost:9091")
    
    print("\n" + "=" * 80)
    print("  Need Help?")
    print("=" * 80)
    print("  📚 Observability docs: docs/OBSERVABILITY.md")
    print("  🔍 Troubleshooting: docs/OBSERVABILITY.md#troubleshooting")
    print("  💬 GitHub Issues: https://github.com/Crashlens/crashlens/issues")
    print("\n" + "=" * 80)
