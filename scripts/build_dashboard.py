#!/usr/bin/env python3
"""
CrashLens Dashboard Builder
Generates production-ready Grafana dashboard aligned with FinOps + AI Governance specification
"""

import json

# Complete dashboard configuration
dashboard = {
    "title": "CrashLens Policy Enforcement",
    "description": "AI Governance dashboard - Policy enforcement reliability, FinOps cost impact, and diagnostic insights",
    "uid": "crashlens-policy-enforcement-v5",
    "tags": ["CrashLens", "AI Governance", "FinOps", "LLMOps"],
    "timezone": "browser",
    "refresh": "10s",
    "schemaVersion": 38,
    "version": 5,
    "editable": True,
    "graphTooltip": 1,
    "time": {"from": "now-1h", "to": "now"},
    
    "templating": {
        "list": [
            {
                "name": "job", "label": "Job", "type": "query",
                "query": "label_values(crashlens_rule_hits_total, job)",
                "datasource": "CrashLens Prometheus",
                "multi": True, "includeAll": True, "refresh": 1, "sort": 1,
                "current": {"selected": True, "text": "All", "value": "$__all"}
            },
            {
                "name": "severity", "label": "Severity", "type": "query",
                "query": "label_values(crashlens_violations_total, severity)",
                "datasource": "CrashLens Prometheus",
                "multi": True, "includeAll": True, "refresh": 1, "sort": 1,
                "current": {"selected": True, "text": "All", "value": "$__all"}
            },
            {
                "name": "rule", "label": "Rule", "type": "query",
                "query": "label_values(crashlens_rule_hits_total{job=~\"$job\"}, rule)",
                "datasource": "CrashLens Prometheus",
                "multi": True, "includeAll": True, "refresh": 2, "sort": 1,
                "current": {"selected": True, "text": "All", "value": "$__all"}
            }
        ]
    },
    
    "panels": [
        # ========================================
        # ROW 1: Policy Enforcement Overview
        # ========================================
        {"id": 100, "type": "row", "title": "🎯 Policy Enforcement Overview", "collapsed": False,
         "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0}},
        
        # Panel 1: Rule Hits by Policy & Severity (Stacked Bar Chart)
        {
            "id": 1, "title": "Rule Hits by Policy & Severity",
            "description": "Shows which policies are firing most frequently, broken down by severity level",
            "type": "barchart", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 1},
            "targets": [{
                "expr": "increase(crashlens_rule_hits_total{job=~\"$job\", severity=~\"$severity\", rule=~\"$rule\"}[5m])",
                "legendFormat": "{{rule}} - {{severity}}", "refId": "A"
            }],
            "options": {
                "legend": {"displayMode": "table", "placement": "right", "calcs": ["sum"]},
                "orientation": "horizontal",
                "showValue": "auto",
                "stacking": "normal",
                "tooltip": {"mode": "multi", "sort": "desc"}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {"axisCenteredZero": False, "axisPlacement": "auto"},
                    "unit": "short", "decimals": 0
                },
                "overrides": [
                    {"matcher": {"id": "byRegexp", "options": ".*critical.*"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]},
                    {"matcher": {"id": "byRegexp", "options": ".*high.*"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]},
                    {"matcher": {"id": "byRegexp", "options": ".*medium.*"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "yellow"}}]},
                    {"matcher": {"id": "byRegexp", "options": ".*low.*"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "blue"}}]}
                ]
            }
        },
        
        # Panel 2: Total Violations by Severity (Pie Chart)
        {
            "id": 2, "title": "Total Violations by Severity",
            "description": "Distribution of policy violations across severity levels",
            "type": "piechart", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 1},
            "targets": [{
                "expr": "sum by (severity) (crashlens_violations_total{severity=~\"$severity\"})",
                "legendFormat": "{{severity}}", "refId": "A", "instant": True
            }],
            "options": {
                "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]},
                "pieType": "donut",
                "tooltip": {"mode": "single"},
                "displayLabels": ["name", "percent"]
            },
            "fieldConfig": {
                "defaults": {"color": {"mode": "palette-classic"}, "unit": "short", "decimals": 0},
                "overrides": [
                    {"matcher": {"id": "byName", "options": "critical"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-red"}}]},
                    {"matcher": {"id": "byName", "options": "high"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-orange"}}]},
                    {"matcher": {"id": "byName", "options": "medium"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-yellow"}}]},
                    {"matcher": {"id": "byName", "options": "low"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "dark-blue"}}]}
                ]
            }
        },
        
        # ========================================
        # ROW 2: Enforcement Reliability
        # ========================================
        {"id": 101, "type": "row", "title": "⚙️ Enforcement Reliability", "collapsed": False,
         "gridPos": {"h": 1, "w": 24, "x": 0, "y": 9}},
        
        # Panel 3: Enforcement Success Ratio (Gauge)
        {
            "id": 3, "title": "Enforcement Success Ratio",
            "description": "Percentage of successful metric pushes - monitors overall enforcement reliability",
            "type": "gauge", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 8, "x": 0, "y": 10},
            "targets": [{
                "expr": "(sum(crashlens_metrics_push_status == 1) / count(crashlens_metrics_push_status)) * 100",
                "refId": "A", "instant": True
            }],
            "options": {
                "showThresholdLabels": True,
                "showThresholdMarkers": True,
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 80, "color": "yellow"},
                            {"value": 95, "color": "green"}
                        ]
                    },
                    "unit": "percent", "decimals": 1, "min": 0, "max": 100
                }
            }
        },
        
        # Panel 4: Last Enforcement Run (Stat with Timestamp)
        {
            "id": 4, "title": "Last Enforcement Run",
            "description": "Time of the most recent policy enforcement execution",
            "type": "stat", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 8, "x": 8, "y": 10},
            "targets": [{
                "expr": "crashlens_last_run_timestamp_seconds",
                "refId": "A", "instant": True
            }],
            "options": {
                "graphMode": "none",
                "colorMode": "value",
                "orientation": "auto",
                "textMode": "value",
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": None, "color": "green"}
                        ]
                    },
                    "unit": "dateTimeFromNow", "decimals": 0, "mappings": []
                }
            },
            "transformations": [{
                "id": "convertFieldType",
                "options": {
                    "conversions": [{"targetType": "time", "destinationType": "time"}],
                    "fields": {}
                }
            }]
        },
        
        # Panel 5: Enforcement Frequency (Line Chart)
        {
            "id": 5, "title": "Enforcement Frequency",
            "description": "Rate of enforcement executions - detects gaps or irregular schedules",
            "type": "timeseries", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 10},
            "targets": [{
                "expr": "rate(crashlens_last_run_timestamp_seconds[10m])",
                "legendFormat": "Enforcement rate", "refId": "A"
            }],
            "options": {
                "legend": {"displayMode": "list", "placement": "bottom"},
                "tooltip": {"mode": "single"}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "drawStyle": "line", "lineInterpolation": "smooth", "lineWidth": 2,
                        "fillOpacity": 20, "gradientMode": "opacity", "axisPlacement": "auto"
                    },
                    "unit": "reqps", "decimals": 4
                }
            }
        },
        
        # ========================================
        # ROW 3: FinOps & Cost Impact
        # ========================================
        {"id": 102, "type": "row", "title": "💰 FinOps & Cost Impact", "collapsed": False,
         "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18}},
        
        # Panel 6: Cost Savings Estimate (Stat + Trend)
        {
            "id": 6, "title": "Cost Savings Estimate",
            "description": "Estimated financial impact of policy enforcement (USD)",
            "type": "stat", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 6, "w": 8, "x": 0, "y": 19},
            "targets": [{
                "expr": "sum(crashlens_cost_savings_total)",
                "refId": "A", "instant": False
            }],
            "options": {
                "graphMode": "area",
                "colorMode": "value",
                "orientation": "auto",
                "textMode": "value_and_name",
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": None, "color": "green"},
                            {"value": 100, "color": "yellow"},
                            {"value": 1000, "color": "red"}
                        ]
                    },
                    "unit": "currencyUSD", "decimals": 2, "mappings": []
                }
            }
        },
        
        # Panel 7: Cost per Violation (Derived Metric)
        {
            "id": 7, "title": "Cost per Violation",
            "description": "Average cost impact per policy violation (total LLM cost / violations)",
            "type": "stat", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 6, "w": 8, "x": 8, "y": 19},
            "targets": [{
                "expr": "sum(crashlens_total_llm_cost) / sum(crashlens_violations_total)",
                "refId": "A", "instant": True
            }],
            "options": {
                "graphMode": "none",
                "colorMode": "value",
                "orientation": "auto",
                "textMode": "value_and_name",
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
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
                    "unit": "currencyUSD", "decimals": 4, "mappings": []
                }
            }
        },
        
        # Panel 8: Token Waste Prevented
        {
            "id": 8, "title": "Token Waste Prevented",
            "description": "Total tokens saved through policy enforcement",
            "type": "stat", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 6, "w": 8, "x": 16, "y": 19},
            "targets": [{
                "expr": "sum(crashlens_tokens_wasted_total)",
                "refId": "A", "instant": False
            }],
            "options": {
                "graphMode": "area",
                "colorMode": "value",
                "orientation": "auto",
                "textMode": "value_and_name",
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": None, "color": "blue"},
                            {"value": 10000, "color": "green"},
                            {"value": 100000, "color": "super-light-green"}
                        ]
                    },
                    "unit": "short", "decimals": 0, "mappings": []
                }
            }
        },
        
        # ========================================
        # ROW 4: Diagnostic Breakdown
        # ========================================
        {"id": 103, "type": "row", "title": "🧠 Diagnostic Breakdown", "collapsed": False,
         "gridPos": {"h": 1, "w": 24, "x": 0, "y": 25}},
        
        # Panel 9: Top Violating Rules (Table)
        {
            "id": 9, "title": "Top Violating Rules",
            "description": "Most problematic rules sorted by total hits and severity",
            "type": "table", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 26},
            "targets": [{
                "expr": "sum by (rule, severity) (crashlens_rule_hits_total{job=~\"$job\", severity=~\"$severity\", rule=~\"$rule\"})",
                "refId": "A", "instant": True, "format": "table"
            }],
            "options": {
                "showHeader": True,
                "sortBy": [{"displayName": "Value", "desc": True}]
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {"align": "auto", "displayMode": "auto"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": None, "color": "green"},
                            {"value": 10, "color": "yellow"},
                            {"value": 50, "color": "red"}
                        ]
                    },
                    "unit": "short", "decimals": 0, "mappings": []
                },
                "overrides": [
                    {"matcher": {"id": "byName", "options": "rule"},
                     "properties": [{"id": "custom.width", "value": 300}]},
                    {"matcher": {"id": "byName", "options": "severity"},
                     "properties": [{"id": "custom.width", "value": 120}]},
                    {"matcher": {"id": "byName", "options": "Value"},
                     "properties": [{"id": "displayName", "value": "Total Hits"}, {"id": "custom.width", "value": 150}]}
                ]
            },
            "transformations": [
                {"id": "organize", "options": {"excludeByName": {"Time": True}, "indexByName": {}, "renameByName": {}}}
            ]
        },
        
        # Panel 10: Violations Over Time (Line Chart)
        {
            "id": 10, "title": "Violations Over Time",
            "description": "Trend of policy violations - helps correlate spikes with deployments or prompt changes",
            "type": "timeseries", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 26},
            "targets": [{
                "expr": "increase(crashlens_violations_total{severity=~\"$severity\"}[5m])",
                "legendFormat": "{{severity}}", "refId": "A"
            }],
            "options": {
                "legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "max", "mean"]},
                "tooltip": {"mode": "multi", "sort": "desc"}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "drawStyle": "line", "lineInterpolation": "smooth", "lineWidth": 2,
                        "fillOpacity": 20, "gradientMode": "opacity", "axisPlacement": "auto"
                    },
                    "unit": "short", "decimals": 1
                },
                "overrides": [
                    {"matcher": {"id": "byName", "options": "critical"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]},
                    {"matcher": {"id": "byName", "options": "high"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "orange"}}]},
                    {"matcher": {"id": "byName", "options": "medium"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "yellow"}}]},
                    {"matcher": {"id": "byName", "options": "low"},
                     "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "blue"}}]}
                ]
            }
        },
        
        # ========================================
        # ROW 5: System Health
        # ========================================
        {"id": 104, "type": "row", "title": "🩺 System Health", "collapsed": False,
         "gridPos": {"h": 1, "w": 24, "x": 0, "y": 34}},
        
        # Panel 11: Metrics Push Health (Time-series with Value Mapping)
        {
            "id": 11, "title": "Metrics Push Health",
            "description": "Pattern of metric push success/failure (1=Success, 0=Failure)",
            "type": "timeseries", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 6, "w": 12, "x": 0, "y": 35},
            "targets": [{
                "expr": "crashlens_metrics_push_status",
                "legendFormat": "Push status", "refId": "A"
            }],
            "options": {
                "legend": {"displayMode": "list", "placement": "bottom"},
                "tooltip": {"mode": "single"}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {
                        "drawStyle": "line", "lineInterpolation": "stepAfter", "lineWidth": 2,
                        "fillOpacity": 50, "gradientMode": "none", "axisPlacement": "auto"
                    },
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 1, "color": "green"}
                        ]
                    },
                    "unit": "short", "decimals": 0,
                    "mappings": [
                        {"type": "value", "options": {"0": {"text": "Failure", "color": "red"}}},
                        {"type": "value", "options": {"1": {"text": "Success", "color": "green"}}}
                    ],
                    "min": 0, "max": 1
                }
            }
        },
        
        # Panel 12: Exporter Uptime (Gauge)
        {
            "id": 12, "title": "Exporter Uptime",
            "description": "Ensures the Prometheus exporter is running continuously",
            "type": "gauge", "datasource": "CrashLens Prometheus",
            "gridPos": {"h": 6, "w": 12, "x": 12, "y": 35},
            "targets": [{
                "expr": "up{job=~\"$job\"}",
                "refId": "A", "instant": True
            }],
            "options": {
                "showThresholdLabels": False,
                "showThresholdMarkers": True,
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]}
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 1, "color": "green"}
                        ]
                    },
                    "unit": "short", "decimals": 0,
                    "mappings": [
                        {"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}}},
                        {"type": "value", "options": {"1": {"text": "UP", "color": "green"}}}
                    ],
                    "min": 0, "max": 1
                }
            }
        }
    ],
    
    "annotations": {
        "list": [{
            "datasource": "CrashLens Prometheus",
            "enable": True,
            "expr": "ALERTS{alertname=~\"CrashLens.*\"}",
            "iconColor": "red",
            "name": "CrashLens Policy Alerts",
            "tagKeys": "alertname,severity",
            "textFormat": "{{alertname}}: {{annotations.description}}",
            "titleFormat": "Policy Alert: {{alertname}}"
        }]
    }
}

# Write dashboard JSON
with open('dashboards/crashlens-policy-enforcement.json', 'w', encoding='utf-8') as f:
    json.dump(dashboard, f, indent=2, ensure_ascii=False)

print("✅ Dashboard successfully generated!")
print(f"   • Title: {dashboard['title']}")
print(f"   • UID: {dashboard['uid']}")
print(f"   • Total panels: {len([p for p in dashboard['panels'] if p.get('type') != 'row'])}")
print(f"   • Rows: {len([p for p in dashboard['panels'] if p.get('type') == 'row'])}")
print(f"   • Template variables: {len(dashboard['templating']['list'])}")
print("\n📊 Panel Breakdown:")
print("   Row 1: Policy Enforcement Overview (2 panels)")
print("   Row 2: Enforcement Reliability (3 panels)")
print("   Row 3: FinOps & Cost Impact (3 panels)")
print("   Row 4: Diagnostic Breakdown (2 panels)")
print("   Row 5: System Health (2 panels)")
