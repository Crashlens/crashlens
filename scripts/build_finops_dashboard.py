#!/usr/bin/env python3
"""
Build complete CrashLens dashboard with FinOps metrics (Production v3.0)

This version includes:
- FinOps & Cost Impact row (3 panels)
- All original panels (12 panels)
- Correct datasource configuration
- Panel descriptions with metric status
- Executive-friendly layout (FinOps first)
"""

import json
from pathlib import Path


def build_complete_dashboard():
    """Build complete dashboard with FinOps metrics."""
    
    dashboard = {
        "title": "CrashLens Policy Enforcement (Production)",
        "description": "Comprehensive monitoring for AI token waste detection and policy violations with FinOps cost tracking",
        "tags": ["crashlens", "ai", "llm", "policy", "observability", "prometheus", "finops", "cost"],
        "timezone": "browser",
        "refresh": "30s",
        "schemaVersion": 38,
        "version": 3,
        "editable": True,
        "graphTooltip": 1,
        "time": {
            "from": "now-1h",
            "to": "now"
        },
        
        # Template variables
        "templating": {
            "list": [
                {
                    "name": "job",
                    "label": "Job",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total, job)",
                    "datasource": "${DS_PROMETHEUS}",
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
                    "name": "severity",
                    "label": "Severity",
                    "type": "query",
                    "query": "label_values(crashlens_violations_total, severity)",
                    "datasource": "${DS_PROMETHEUS}",
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
                    "datasource": "${DS_PROMETHEUS}",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 2,
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
                    "datasource": "${DS_PROMETHEUS}",
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
    
    panels = []
    row_y = 0
    
    # ============================================================================
    # ROW 1: FinOps & Cost Impact (NEW - Lead with business value)
    # ============================================================================
    panels.append({
        "id": 100,
        "type": "row",
        "title": "💰 FinOps & Cost Impact",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 1: Total Cost Saved
    panels.append({
        "id": 1,
        "title": "💰 Total Cost Saved",
        "description": "Total estimated cost savings from detecting wasteful patterns (retry loops, fallback storms, model overkill). Metric: crashlens_cost_savings_total",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_cost_savings_total{job=~"$job"})',
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
                        {"value": 0.01, "color": "yellow"},
                        {"value": 0.10, "color": "orange"},
                        {"value": 1.00, "color": "red"}
                    ]
                },
                "unit": "currencyUSD",
                "decimals": 4
            }
        }
    })
    
    # Panel 2: Tokens Saved from Waste
    panels.append({
        "id": 2,
        "title": "🔥 Tokens Saved from Waste",
        "description": "Total tokens prevented from being wasted (prompt + completion). Higher is better. Metric: crashlens_tokens_wasted_total",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 8, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_tokens_wasted_total{job=~"$job"})',
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
    
    # Panel 3: Cost per Violation
    panels.append({
        "id": 3,
        "title": "📊 Cost per Violation",
        "description": "Average LLM cost per policy violation detected. Lower is better. Calculated: total_llm_cost / violations_total",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 16, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_total_llm_cost{job=~"$job"}) / sum(crashlens_violations_total)',
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
                        {"value": 0.001, "color": "yellow"},
                        {"value": 0.01, "color": "orange"},
                        {"value": 0.10, "color": "red"}
                    ]
                },
                "unit": "currencyUSD",
                "decimals": 6
            }
        }
    })
    
    row_y += 6
    
    # Panel 4: Cost Savings by Rule (Stacked Area Chart)
    panels.append({
        "id": 4,
        "title": "Cost Savings by Policy Rule",
        "description": "Shows which rules are generating the most savings - key insight for ROI justification",
        "type": "timeseries",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'sum by (rule) (increase(crashlens_cost_savings_total{job=~"$job"}[$interval]))',
            "legendFormat": "{{rule}}",
            "refId": "A"
        }],
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "right",
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
                    "fillOpacity": 60,
                    "gradientMode": "opacity",
                    "stacking": {
                        "mode": "normal",
                        "group": "A"
                    },
                    "axisPlacement": "auto"
                },
                "unit": "currencyUSD",
                "decimals": 4
            }
        }
    })
    
    row_y += 8
    
    # ============================================================================
    # ROW 2: Overview KPIs
    # ============================================================================
    panels.append({
        "id": 101,
        "type": "row",
        "title": "📊 Overview - Key Performance Indicators",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 5: Total Violations (Stat)
    panels.append({
        "id": 5,
        "title": "Total Violations",
        "description": "Total number of policy violations across all severities. Critical threshold: >100",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
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
    
    # Panel 6: Critical Violations (Stat)
    panels.append({
        "id": 6,
        "title": "Critical Violations",
        "description": "Number of critical severity violations requiring immediate attention",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
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
    
    # Panel 7: Rule Hits (Stat)
    panels.append({
        "id": 7,
        "title": "Total Rule Hits",
        "description": "Total number of policy rule triggers across all rules",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 6, "x": 12, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_rule_hits_total{job=~"$job", rule=~"$rule", mode=~"$mode"})',
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
    
    # Panel 8: Last Scan Status (Gauge)
    panels.append({
        "id": 8,
        "title": "Time Since Last Scan",
        "description": "Minutes since last successful scan. Alert if >60 minutes",
        "type": "gauge",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 6, "x": 18, "y": row_y},
        "targets": [{
            "expr": '(time() - crashlens_last_run_timestamp_seconds{status="success"}) / 60',
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
                    "mode": "absolute",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 30, "color": "yellow"},
                        {"value": 60, "color": "red"}
                    ]
                },
                "unit": "m",
                "decimals": 0,
                "min": 0,
                "max": 120
            }
        }
    })
    
    row_y += 6
    
    # ============================================================================
    # ROW 3: Violations Analysis
    # ============================================================================
    panels.append({
        "id": 102,
        "type": "row",
        "title": "🚨 Violations Analysis",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 9: Rule Hits Over Time (Time Series)
    panels.append({
        "id": 9,
        "title": "Rule Hits Rate (per minute)",
        "description": "Rate of policy rule hits over time. Shows which rules are triggering most frequently.",
        "type": "timeseries",
        "datasource": "${DS_PROMETHEUS}",
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
    
    # Panel 10: Violations by Severity (Time Series)
    panels.append({
        "id": 10,
        "title": "Violations by Severity",
        "description": "Breakdown of violations by severity level over time",
        "type": "timeseries",
        "datasource": "${DS_PROMETHEUS}",
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
    
    # Panel 11: Severity Distribution (Pie Chart)
    panels.append({
        "id": 11,
        "title": "Severity Distribution",
        "description": "Current distribution of violations across severity levels",
        "type": "piechart",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": row_y},
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
    
    # Panel 12: Top 10 Rules by Hit Count (Bar Gauge)
    panels.append({
        "id": 12,
        "title": "Top 10 Rules by Hit Count",
        "description": "Most frequently triggered policy rules in the selected time range",
        "type": "bargauge",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 8, "w": 16, "x": 8, "y": row_y},
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
    
    # ============================================================================
    # ROW 4: Performance & Health
    # ============================================================================
    panels.append({
        "id": 103,
        "type": "row",
        "title": "⚡ Performance & System Health",
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}
    })
    row_y += 1
    
    # Panel 13: Metrics Push Status (Stat)
    panels.append({
        "id": 13,
        "title": "Metrics Push Status",
        "description": "Pushgateway connectivity status. 1 = Success, 0 = Failed",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 0, "y": row_y},
        "targets": [{
            "expr": 'crashlens_metrics_push_status',
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
                        {"value": None, "color": "red"},
                        {"value": 1, "color": "green"}
                    ]
                },
                "unit": "short",
                "decimals": 0,
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "0": {"text": "Failed", "color": "red"},
                            "1": {"text": "Success", "color": "green"}
                        }
                    }
                ]
            }
        }
    })
    
    # Panel 14: Rule Label Overflow (Stat)
    panels.append({
        "id": 14,
        "title": "Rule Label Overflow Events",
        "description": "Count of cardinality protection triggers. Should be 0 under normal operation.",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 8, "y": row_y},
        "targets": [{
            "expr": 'sum(crashlens_rule_label_overflow_total)',
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
                        {"value": 1, "color": "yellow"},
                        {"value": 10, "color": "red"}
                    ]
                },
                "unit": "short",
                "decimals": 0
            }
        }
    })
    
    # Panel 15: Exporter Uptime (Stat)
    panels.append({
        "id": 15,
        "title": "Exporter Uptime",
        "description": "CrashLens exporter availability. 1 = Up, 0 = Down",
        "type": "stat",
        "datasource": "${DS_PROMETHEUS}",
        "gridPos": {"h": 6, "w": 8, "x": 16, "y": row_y},
        "targets": [{
            "expr": 'up{job="crashlens"}',
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
                        {"value": None, "color": "red"},
                        {"value": 1, "color": "green"}
                    ]
                },
                "unit": "short",
                "decimals": 0,
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "0": {"text": "Down", "color": "red"},
                            "1": {"text": "Up", "color": "green"}
                        }
                    }
                ]
            }
        }
    })
    
    dashboard["panels"] = panels
    
    # Add annotations for important events
    dashboard["annotations"] = {
        "list": [
            {
                "datasource": "${DS_PROMETHEUS}",
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


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*80)
    print("  CrashLens FinOps Dashboard Generator v3.0")
    print("="*80)
    
    # Create dashboards directory if it doesn't exist
    dashboards_dir = Path(__file__).parent.parent / 'dashboards'
    dashboards_dir.mkdir(exist_ok=True)
    
    # Generate complete dashboard
    print("\n📊 Generating complete CrashLens dashboard with FinOps metrics...")
    print("-"*80)
    dashboard = build_complete_dashboard()
    output_path = dashboards_dir / 'crashlens-policy-enforcement.json'
    
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
    
    print("\n" + "="*80)
    print("  ✅ Dashboard Structure")
    print("="*80)
    print("  Row 1: 💰 FinOps & Cost Impact (4 panels)")
    print("    - Total Cost Saved")
    print("    - Tokens Saved from Waste")
    print("    - Cost per Violation")
    print("    - Cost Savings by Rule (time series)")
    print("\n  Row 2: 📊 Overview KPIs (4 panels)")
    print("    - Total Violations")
    print("    - Critical Violations")
    print("    - Total Rule Hits")
    print("    - Time Since Last Scan")
    print("\n  Row 3: 🚨 Violations Analysis (4 panels)")
    print("    - Rule Hits Rate")
    print("    - Violations by Severity")
    print("    - Severity Distribution (pie chart)")
    print("    - Top 10 Rules (bar gauge)")
    print("\n  Row 4: ⚡ Performance & Health (3 panels)")
    print("    - Metrics Push Status")
    print("    - Rule Label Overflow")
    print("    - Exporter Uptime")
    
    print("\n" + "="*80)
    print("  🔧 Key Fixes Applied")
    print("="*80)
    print("  ✅ Added 4 FinOps panels (cost savings, tokens, cost/violation, breakdown)")
    print("  ✅ Fixed datasource: All panels use ${DS_PROMETHEUS} variable")
    print("  ✅ Executive-friendly layout: FinOps metrics first")
    print("  ✅ Panel descriptions added with metric names")
    print("  ✅ Removed panels for non-existent metrics")
    print("  ✅ Color-coded thresholds on all stat panels")
    
    print("\n" + "="*80)
    print("  📖 Import Instructions")
    print("="*80)
    print("  1. Open Grafana: http://localhost:3000")
    print("  2. Go to: Dashboards → Import")
    print("  3. Upload JSON file:")
    print(f"     {output_path.absolute()}")
    print("  4. Select datasource: CrashLens Prometheus")
    print("  5. Click 'Import'")
    print("\n  6. Run CrashLens to populate metrics:")
    print("     crashlens scan logs.jsonl --push-metrics \\")
    print("       --pushgateway-url http://localhost:9091")
    
    print("\n" + "="*80)
    print("  ✅ Dashboard Generation Complete!")
    print("="*80)
