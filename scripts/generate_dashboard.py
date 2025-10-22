#!/usr/bin/env python3
"""
Grafana Dashboard Generator for CrashLens Policy Enforcement

Generates a Grafana dashboard JSON for visualizing:
- Policy rule trigger rates
- Violation counts by severity
- Top failing rules
- Token waste trends
"""

import json
from pathlib import Path


def generate_crashlens_dashboard():
    """Generate the main CrashLens policy enforcement dashboard using manual JSON."""
    
    dashboard = {
        "title": "CrashLens Policy Enforcement",
        "description": "Monitor AI token waste detection and policy violations",
        "tags": ["crashlens", "ai", "llm", "policy"],
        "timezone": "browser",
        "refresh": "30s",
        "schemaVersion": 27,
        "version": 1,
        
        # Template variables for filtering
        "templating": {
            "list": [
                {
                    "name": "detector",
                    "label": "Detector",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total, detector)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                },
                {
                    "name": "severity",
                    "label": "Severity",
                    "type": "query",
                    "query": "label_values(crashlens_rule_hits_total, severity)",
                    "datasource": "Prometheus",
                    "multi": True,
                    "includeAll": True,
                }
            ]
        },
        
        "panels": [
            # Panel 1: Rule Trigger Rate
            {
                "id": 1,
                "title": "Rule Trigger Rate (5m avg)",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": 'rate(crashlens_rule_hits_total{detector=~"$detector", severity=~"$severity"}[5m])',
                        "legendFormat": "{{rule_id}} ({{severity}})",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "short", "label": "Triggers/sec"},
                    {"format": "short"}
                ]
            },
            
            # Panel 2: Total Violations by Severity
            {
                "id": 2,
                "title": "Violations by Severity",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "targets": [
                    {
                        "expr": 'sum by (severity) (crashlens_rule_hits_total{detector=~"$detector"})',
                        "legendFormat": "{{severity}}",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "short", "label": "Total Violations"},
                    {"format": "short"}
                ]
            },
            
            # Panel 3: Token Waste Detected
            {
                "id": 3,
                "title": "Token Waste Detected (tokens/min)",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {
                        "expr": 'rate(crashlens_waste_tokens_total{detector=~"$detector"}[5m]) * 60',
                        "legendFormat": "{{detector}}",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "short", "label": "Tokens/min"},
                    {"format": "short"}
                ]
            },
            
            # Panel 4: Cost Savings Potential
            {
                "id": 4,
                "title": "Potential Cost Savings ($/min)",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {
                        "expr": 'rate(crashlens_waste_cost_total{detector=~"$detector"}[5m]) * 60',
                        "legendFormat": "{{detector}}",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "short", "label": "$/min"},
                    {"format": "short"}
                ]
            },
            
            # Panel 5: Rule Evaluation Time
            {
                "id": 5,
                "title": "Rule Evaluation Time (p95)",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {
                        "expr": 'histogram_quantile(0.95, rate(crashlens_rule_evaluation_seconds_bucket[5m]))',
                        "legendFormat": "{{rule_id}}",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "s", "label": "Evaluation Time"},
                    {"format": "short"}
                ]
            },
            
            # Panel 6: Top Failing Rules
            {
                "id": 6,
                "title": "Top 10 Failing Rules",
                "type": "graph",
                "datasource": "Prometheus",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {
                        "expr": 'topk(10, sum by (rule_id) (rate(crashlens_rule_hits_total{action="fail"}[5m])))',
                        "legendFormat": "{{rule_id}}",
                        "refId": "A"
                    }
                ],
                "yaxes": [
                    {"format": "short", "label": "Failures/sec"},
                    {"format": "short"}
                ]
            }
        ]
    }
    
    return dashboard


def save_dashboard(dashboard, output_path: Path):
    """Save dashboard to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    print(f"✓ Dashboard saved to: {output_path}")
    print(f"  Size: {output_path.stat().st_size:,} bytes")
    print(f"  Panels: {len(dashboard.get('panels', []))}")


if __name__ == '__main__':
    print("=" * 70)
    print("Grafana Dashboard Generator for CrashLens")
    print("=" * 70)
    
    # Create dashboards directory if it doesn't exist
    dashboards_dir = Path(__file__).parent.parent / 'dashboards'
    dashboards_dir.mkdir(exist_ok=True)
    
    # Generate main dashboard
    print("\nGenerating CrashLens Policy Enforcement dashboard...")
    dashboard = generate_crashlens_dashboard()
    output_path = dashboards_dir / 'crashlens-policy-enforcement.json'
    save_dashboard(dashboard, output_path)
    
    print("\n" + "=" * 70)
    print("Dashboard Generation Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("  1. Start Grafana:")
    print("     docker run -d -p 3000:3000 grafana/grafana")
    print()
    print("  2. Access Grafana:")
    print("     http://localhost:3000 (admin/admin)")
    print()
    print("  3. Add Prometheus data source:")
    print("     Configuration → Data Sources → Add Prometheus")
    print("     URL: http://host.docker.internal:9090")
    print()
    print("  4. Import dashboard:")
    print(f"     Dashboards → Import → Upload JSON file")
    print(f"     File: {output_path}")
    print()
    print("=" * 70)
