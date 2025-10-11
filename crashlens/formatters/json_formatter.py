"""
JSON formatter for CrashLens - produces structured JSON output for frontend consumption
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class JSONFormatter:
    """
    Formats CrashLens analysis results into structured JSON for frontend integration.
    
    Output structure:
    {
        "metadata": {...},
        "summary": {...},
        "issues": [...],
        "traces": [...],
        "models": {...},
        "timeline": [...],
        "recommendations": [...],
        "alerts": [...],
        "export_options": {...}
    }
    """
    
    def __init__(self, analysis_results: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the JSON formatter.
        
        Args:
            analysis_results: Results from detector execution including:
                - detectors: List of detector results
                - log_file: Path to analyzed log file
                - total_traces: Total number of traces processed
                - parse_errors: Number of parse errors encountered
                - start_time: Analysis start timestamp
                - end_time: Analysis end timestamp
            config: Optional configuration for formatting options
        """
        self.analysis_results = analysis_results
        self.config = config or {}
        self.detectors = analysis_results.get('detectors', [])
        
    def format(self) -> str:
        """
        Generate complete JSON output.
        
        Returns:
            JSON string with all formatted sections
        """
        output = {
            "metadata": self._format_metadata(),
            "summary": self._format_summary(),
            "issues": self._format_issues(),
            "traces": self._format_traces(),
            "models": self._format_models(),
            "timeline": self._format_timeline(),
            "recommendations": self._format_recommendations(),
            "alerts": self._format_alerts(),
            "export_options": self._format_export_options()
        }
        
        return json.dumps(output, indent=2, default=str)
    
    def _format_metadata(self) -> Dict[str, Any]:
        """
        Format metadata section with scan context.
        
        Returns:
            {
                "scan_time": ISO timestamp,
                "log_file": str,
                "total_traces": int,
                "parse_errors": int,
                "duration_ms": int,
                "crashlens_version": str,
                "health_score": float (0-100)
            }
        """
        start_time = self.analysis_results.get('start_time', datetime.now())
        end_time = self.analysis_results.get('end_time', datetime.now())
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
            
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "scan_time": end_time.isoformat(),
            "log_file": self.analysis_results.get('log_file', 'unknown'),
            "total_traces": self.analysis_results.get('total_traces', 0),
            "parse_errors": self.analysis_results.get('parse_errors', 0),
            "duration_ms": duration_ms,
            "crashlens_version": "1.0.0",  # TODO: Import from package version
            "health_score": self._calculate_health_score()
        }
    
    def _format_summary(self) -> Dict[str, Any]:
        """
        Format summary section with issue counts and cost overview.
        
        Returns:
            {
                "total_issues": int,
                "critical": int,
                "high": int,
                "medium": int,
                "low": int,
                "total_cost": float,
                "potential_savings": float,
                "cost_currency": str
            }
        """
        issues = self._get_all_issues()
        
        # Count by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        total_cost = 0.0
        potential_savings = 0.0
        
        for issue in issues:
            severity = issue.get('severity', 'low').lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
            
            # Accumulate costs
            cost = issue.get('cost', {})
            if isinstance(cost, dict):
                total_cost += cost.get('total', 0.0)
                potential_savings += cost.get('wasted', 0.0)
        
        return {
            "total_issues": len(issues),
            "critical": severity_counts['critical'],
            "high": severity_counts['high'],
            "medium": severity_counts['medium'],
            "low": severity_counts['low'],
            "total_cost": round(total_cost, 6),
            "potential_savings": round(potential_savings, 6),
            "cost_currency": "USD"
        }
    
    def _format_issues(self) -> List[Dict[str, Any]]:
        """
        Format issues section with detailed problem list.
        
        Returns:
            [
                {
                    "id": str,
                    "type": str,
                    "severity": str,
                    "title": str,
                    "description": str,
                    "trace_id": str,
                    "model": str,
                    "cost": {
                        "total": float,
                        "wasted": float,
                        "currency": str
                    },
                    "metrics": {
                        "tokens": int,
                        "calls": int,
                        "latency_ms": int
                    },
                    "recommendation": str,
                    "timestamp": ISO timestamp
                }
            ]
        """
        issues = []
        
        for detector_result in self.detectors:
            detector_name = detector_result.get('name', 'unknown')
            findings = detector_result.get('findings', [])
            
            for idx, finding in enumerate(findings):
                issue = {
                    "id": f"{detector_name}_{idx}_{finding.get('trace_id', 'unknown')}",
                    "type": self._normalize_detector_name(detector_name),
                    "severity": finding.get('severity', 'medium'),
                    "title": finding.get('title', finding.get('message', 'Issue detected')),
                    "description": finding.get('message', ''),
                    "trace_id": finding.get('trace_id', 'unknown'),
                    "model": finding.get('model', 'unknown'),
                    "cost": self._format_cost(finding.get('cost', {})),
                    "metrics": {
                        "tokens": finding.get('tokens', {}).get('total', 0),
                        "calls": finding.get('calls', 0),
                        "latency_ms": finding.get('latency_ms', 0)
                    },
                    "recommendation": finding.get('recommendation', ''),
                    "timestamp": finding.get('timestamp', datetime.now().isoformat())
                }
                
                issues.append(issue)
        
        # Sort by severity priority
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: severity_order.get(x['severity'].lower(), 4))
        
        return issues
    
    def _format_traces(self) -> List[Dict[str, Any]]:
        """
        Format traces section with trace-level aggregation.
        
        Returns:
            [
                {
                    "trace_id": str,
                    "issue_count": int,
                    "total_cost": float,
                    "models_used": [str],
                    "start_time": ISO timestamp,
                    "duration_ms": int,
                    "status": str
                }
            ]
        """
        # Aggregate issues by trace_id
        trace_map: Dict[str, Dict[str, Any]] = {}
        
        for detector_result in self.detectors:
            findings = detector_result.get('findings', [])
            
            for finding in findings:
                trace_id = finding.get('trace_id', 'unknown')
                
                if trace_id not in trace_map:
                    trace_map[trace_id] = {
                        "trace_id": trace_id,
                        "issue_count": 0,
                        "total_cost": 0.0,
                        "models_used": set(),
                        "start_time": finding.get('timestamp', datetime.now().isoformat()),
                        "duration_ms": 0,
                        "status": "completed"
                    }
                
                trace = trace_map[trace_id]
                trace['issue_count'] += 1
                
                cost = finding.get('cost', {})
                if isinstance(cost, dict):
                    trace['total_cost'] += cost.get('total', 0.0)
                
                model = finding.get('model')
                if model and model != 'unknown':
                    trace['models_used'].add(model)
                
                # Update duration if available
                if 'latency_ms' in finding:
                    trace['duration_ms'] = max(trace['duration_ms'], finding['latency_ms'])
        
        # Convert sets to lists and format
        traces = []
        for trace_id, trace_data in trace_map.items():
            trace_data['models_used'] = sorted(list(trace_data['models_used']))
            trace_data['total_cost'] = round(trace_data['total_cost'], 6)
            traces.append(trace_data)
        
        # Sort by cost descending
        traces.sort(key=lambda x: x['total_cost'], reverse=True)
        
        return traces
    
    def _format_models(self) -> Dict[str, Any]:
        """
        Format models section with usage and cost by model.
        
        Returns:
            {
                "by_provider": {
                    "openai": {
                        "models": [
                            {
                                "name": str,
                                "calls": int,
                                "tokens": int,
                                "cost": float,
                                "avg_latency_ms": int
                            }
                        ],
                        "total_cost": float
                    }
                },
                "top_models": [...]
            }
        """
        model_stats: Dict[str, Dict[str, Any]] = {}
        
        # Collect stats from all findings
        for detector_result in self.detectors:
            findings = detector_result.get('findings', [])
            
            for finding in findings:
                model = finding.get('model', 'unknown')
                if model == 'unknown':
                    continue
                
                if model not in model_stats:
                    model_stats[model] = {
                        "name": model,
                        "calls": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "total_latency_ms": 0,
                        "latency_count": 0
                    }
                
                stats = model_stats[model]
                stats['calls'] += finding.get('calls', 1)
                
                tokens = finding.get('tokens', {})
                if isinstance(tokens, dict):
                    stats['tokens'] += tokens.get('total', 0)
                
                cost = finding.get('cost', {})
                if isinstance(cost, dict):
                    stats['cost'] += cost.get('total', 0.0)
                
                if 'latency_ms' in finding and finding['latency_ms'] > 0:
                    stats['total_latency_ms'] += finding['latency_ms']
                    stats['latency_count'] += 1
        
        # Calculate averages and group by provider
        by_provider: Dict[str, Dict[str, Any]] = {}
        
        for model, stats in model_stats.items():
            provider = self._get_provider_from_model(model)
            
            if provider not in by_provider:
                by_provider[provider] = {
                    "models": [],
                    "total_cost": 0.0
                }
            
            avg_latency = 0
            if stats['latency_count'] > 0:
                avg_latency = stats['total_latency_ms'] // stats['latency_count']
            
            model_data = {
                "name": model,
                "calls": stats['calls'],
                "tokens": stats['tokens'],
                "cost": round(stats['cost'], 6),
                "avg_latency_ms": avg_latency
            }
            
            by_provider[provider]['models'].append(model_data)
            by_provider[provider]['total_cost'] += stats['cost']
        
        # Round provider totals
        for provider_data in by_provider.values():
            provider_data['total_cost'] = round(provider_data['total_cost'], 6)
            # Sort models by cost descending
            provider_data['models'].sort(key=lambda x: x['cost'], reverse=True)
        
        # Get top models overall
        all_models = []
        for provider_data in by_provider.values():
            all_models.extend(provider_data['models'])
        all_models.sort(key=lambda x: x['cost'], reverse=True)
        
        return {
            "by_provider": by_provider,
            "top_models": all_models[:5]  # Top 5 by cost
        }
    
    def _format_timeline(self) -> List[Dict[str, Any]]:
        """
        Format timeline section with chronological issue events.
        
        Returns:
            [
                {
                    "timestamp": ISO timestamp,
                    "event_type": str,
                    "trace_id": str,
                    "model": str,
                    "severity": str,
                    "description": str
                }
            ]
        """
        events = []
        
        for detector_result in self.detectors:
            detector_name = detector_result.get('name', 'unknown')
            findings = detector_result.get('findings', [])
            
            for finding in findings:
                event = {
                    "timestamp": finding.get('timestamp', datetime.now().isoformat()),
                    "event_type": self._normalize_detector_name(detector_name),
                    "trace_id": finding.get('trace_id', 'unknown'),
                    "model": finding.get('model', 'unknown'),
                    "severity": finding.get('severity', 'medium'),
                    "description": finding.get('message', '')
                }
                events.append(event)
        
        # Sort chronologically
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def _format_recommendations(self) -> List[Dict[str, Any]]:
        """
        Format recommendations section with actionable fixes.
        
        Returns:
            [
                {
                    "priority": int (1-5),
                    "category": str,
                    "title": str,
                    "description": str,
                    "estimated_savings": float,
                    "effort": str (low/medium/high),
                    "impact": str (low/medium/high)
                }
            ]
        """
        recommendations = []
        
        # Generate recommendations based on issue types
        issue_counts = self._count_issues_by_type()
        
        if issue_counts.get('retry_loop', 0) > 0:
            recommendations.append({
                "priority": 1,
                "category": "reliability",
                "title": "Reduce retry loops",
                "description": f"Found {issue_counts['retry_loop']} retry loops. Implement exponential backoff and add circuit breakers.",
                "estimated_savings": self._estimate_savings_for_type('retry_loop'),
                "effort": "medium",
                "impact": "high"
            })
        
        if issue_counts.get('fallback_storm', 0) > 0:
            recommendations.append({
                "priority": 2,
                "category": "performance",
                "title": "Optimize fallback chains",
                "description": f"Detected {issue_counts['fallback_storm']} fallback storms. Review fallback order and add caching.",
                "estimated_savings": self._estimate_savings_for_type('fallback_storm'),
                "effort": "medium",
                "impact": "high"
            })
        
        if issue_counts.get('overkill_model', 0) > 0:
            recommendations.append({
                "priority": 3,
                "category": "cost",
                "title": "Use appropriate model sizes",
                "description": f"Found {issue_counts['overkill_model']} instances of oversized models. Switch to smaller models for simple tasks.",
                "estimated_savings": self._estimate_savings_for_type('overkill_model'),
                "effort": "low",
                "impact": "medium"
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'])
        
        return recommendations
    
    def _format_alerts(self) -> List[Dict[str, Any]]:
        """
        Format alerts section for critical issues requiring immediate attention.
        
        Returns:
            [
                {
                    "level": str (critical/warning),
                    "title": str,
                    "message": str,
                    "action_required": bool,
                    "related_traces": [str]
                }
            ]
        """
        alerts = []
        
        summary = self._format_summary()
        
        # Critical cost alert
        if summary['total_cost'] > 10.0:
            alerts.append({
                "level": "critical",
                "title": "High cost detected",
                "message": f"Total cost of ${summary['total_cost']:.2f} exceeds threshold. Immediate review recommended.",
                "action_required": True,
                "related_traces": []
            })
        
        # High severity issues alert
        if summary['critical'] > 0:
            critical_traces = [
                issue['trace_id'] for issue in self._get_all_issues()
                if issue.get('severity', '').lower() == 'critical'
            ]
            alerts.append({
                "level": "critical",
                "title": f"{summary['critical']} critical issues found",
                "message": "Critical issues require immediate attention to prevent service degradation.",
                "action_required": True,
                "related_traces": critical_traces[:5]  # Limit to first 5
            })
        
        # Potential savings alert
        if summary['potential_savings'] > 1.0:
            alerts.append({
                "level": "warning",
                "title": "Significant cost savings available",
                "message": f"Potential savings of ${summary['potential_savings']:.2f} identified through optimization.",
                "action_required": False,
                "related_traces": []
            })
        
        return alerts
    
    def _format_export_options(self) -> Dict[str, Any]:
        """
        Format export options section with available output formats and links.
        
        Returns:
            {
                "formats": [str],
                "detailed_reports": {
                    "json": str,
                    "markdown": str,
                    "csv": str
                },
                "filters": {
                    "by_severity": [str],
                    "by_type": [str],
                    "by_model": [str]
                }
            }
        """
        issue_types = set()
        models = set()
        
        for issue in self._get_all_issues():
            issue_types.add(issue['type'])
            if issue['model'] != 'unknown':
                models.add(issue['model'])
        
        return {
            "formats": ["json", "markdown", "csv", "slack"],
            "detailed_reports": {
                "json": "crashlens-report.json",
                "markdown": "crashlens-report.md",
                "csv": "crashlens-report.csv"
            },
            "filters": {
                "by_severity": ["critical", "high", "medium", "low"],
                "by_type": sorted(list(issue_types)),
                "by_model": sorted(list(models))
            }
        }
    
    # ========== Helper Methods ==========
    
    def _format_cost(self, cost_data: Any) -> Dict[str, Any]:
        """Format cost data into standardized structure."""
        if not isinstance(cost_data, dict):
            return {"total": 0.0, "wasted": 0.0, "currency": "USD"}
        
        return {
            "total": round(cost_data.get('total', 0.0), 6),
            "wasted": round(cost_data.get('wasted', 0.0), 6),
            "currency": "USD"
        }
    
    def _get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all issues from all detectors."""
        if not hasattr(self, '_cached_issues'):
            self._cached_issues = self._format_issues()
        return self._cached_issues
    
    def _count_issues_by_type(self) -> Dict[str, int]:
        """Count issues grouped by type."""
        counts: Dict[str, int] = {}
        
        for issue in self._get_all_issues():
            issue_type = issue['type']
            counts[issue_type] = counts.get(issue_type, 0) + 1
        
        return counts
    
    def _calculate_health_score(self) -> float:
        """
        Calculate overall health score (0-100).
        
        Formula: 100 - (critical*10 + high*5 + medium*2 + low*1)
        Clamped to 0-100 range.
        """
        summary = self._format_summary()
        
        penalty = (
            summary['critical'] * 10 +
            summary['high'] * 5 +
            summary['medium'] * 2 +
            summary['low'] * 1
        )
        
        score = max(0, min(100, 100 - penalty))
        return round(score, 1)
    
    def _estimate_savings_for_type(self, issue_type: str) -> float:
        """Estimate potential savings for a specific issue type."""
        total_savings = 0.0
        
        for issue in self._get_all_issues():
            if issue['type'] == issue_type:
                total_savings += issue['cost']['wasted']
        
        return round(total_savings, 6)
    
    def _normalize_detector_name(self, detector_name: str) -> str:
        """Normalize detector name to issue type."""
        name_map = {
            'RetryLoopDetector': 'retry_loop',
            'FallbackStormDetector': 'fallback_storm',
            'OverkillModelDetector': 'overkill_model',
            'retry_loops': 'retry_loop',
            'fallback_storm': 'fallback_storm',
            'overkill_model': 'overkill_model'
        }
        
        return name_map.get(detector_name, detector_name.lower().replace(' ', '_'))
    
    def _get_provider_from_model(self, model: str) -> str:
        """Extract provider name from model string."""
        model_lower = model.lower()
        
        if 'gpt' in model_lower or 'openai' in model_lower:
            return 'openai'
        elif 'claude' in model_lower or 'anthropic' in model_lower:
            return 'anthropic'
        elif 'gemini' in model_lower or 'google' in model_lower:
            return 'google'
        elif 'llama' in model_lower or 'meta' in model_lower:
            return 'meta'
        elif 'mistral' in model_lower:
            return 'mistral'
        elif 'cohere' in model_lower:
            return 'cohere'
        else:
            return 'other'
