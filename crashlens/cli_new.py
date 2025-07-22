#!/usr/bin/env python3
"""
CrashLens CLI - Token Waste Detection Tool
Scans Langfuse-style JSONL logs for inefficient GPT API usage patterns.
Production-grade suppression and priority logic for accurate root cause attribution.
"""

import click
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Set, Tuple

from .parsers.langfuse import LangfuseParser
from .detectors.retry_loops import RetryLoopDetector
from .detectors.fallback_storm import FallbackStormDetector
from .detectors.fallback_failure import FallbackFailureDetector
from .detectors.overkill_model_detector import OverkillModelDetector
from .reporters.slack_formatter import SlackFormatter
from .reporters.markdown_formatter import MarkdownFormatter
from .reporters.summary_formatter import SummaryFormatter

# 🔢 1. DETECTOR PRIORITIES - Global constant used throughout
DETECTOR_PRIORITY = {
    'RetryLoopDetector': 1,      # Highest priority - fundamental issue
    'FallbackStormDetector': 2,  # Model switching chaos
    'FallbackFailureDetector': 3, # Unnecessary expensive calls
    'OverkillModelDetector': 4,   # Overkill for simple tasks - lowest priority
}

# Detector display names for human-readable output
DETECTOR_DISPLAY_NAMES = {
    'RetryLoopDetector': 'Retry Loop',
    'FallbackStormDetector': 'Fallback Storm', 
    'FallbackFailureDetector': 'Fallback Failure',
    'OverkillModelDetector': 'Overkill Model'
}


class SuppressionEngine:
    """
    🧰 3. Production-grade suppression engine with trace-level ownership
    Ensures one "owner" per trace for accurate root cause attribution.
    """
    
    def __init__(self, suppression_config: Optional[Dict[str, Any]] = None, include_suppressed: bool = False):
        self.suppression_config = suppression_config or {}
        self.include_suppressed = include_suppressed
        
        # 🧠 2. Trace-Level Ownership: {trace_id: claimed_by_detector}
        self.trace_ownership: Dict[str, str] = {}
        self.suppressed_detections: List[Dict[str, Any]] = []
        self.active_detections: List[Dict[str, Any]] = []
    
    def process_detections(self, detector_name: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process detections with suppression logic
        Returns active detections, stores suppressed ones
        """
        active = []
        
        for detection in detections:
            trace_id = detection.get('trace_id')
            if not trace_id:
                active.append(detection)  # No trace_id, can't suppress
                continue
            
            # Check if this detector is suppressed by configuration
            if self._is_detector_suppressed(detector_name, trace_id):
                self._add_suppressed_detection(detection, detector_name, "disabled_by_config")
                continue
            
            # Check trace ownership and priority
            if trace_id in self.trace_ownership:
                current_owner = self.trace_ownership[trace_id]
                current_priority = DETECTOR_PRIORITY.get(detector_name, 999)
                owner_priority = DETECTOR_PRIORITY.get(current_owner, 999)
                
                # 🧰 3. Suppression Hook: Priority-based suppression
                if current_priority > owner_priority:
                    # Current detector has lower priority, suppress this detection
                    self._add_suppressed_detection(detection, detector_name, f"higher_priority_detector:{current_owner}")
                    continue
                elif current_priority < owner_priority:
                    # Current detector has higher priority, it takes ownership
                    # Move previous owner's detections to suppressed
                    self._transfer_ownership(trace_id, current_owner, detector_name)
            
            # This detection is active - claim ownership
            self.trace_ownership[trace_id] = detector_name
            detection['suppressed_by'] = None  # Mark as not suppressed
            active.append(detection)
        
        # Store active detections for this detector
        self.active_detections.extend(active)
        return active
    
    def _is_detector_suppressed(self, detector_name: str, trace_id: str) -> bool:
        """Check if detector is suppressed by configuration"""
        detector_config = self.suppression_config.get(detector_name.lower().replace('detector', ''), {})
        return detector_config.get('suppress_if_retry_loop', False) and self.trace_ownership.get(trace_id) == 'RetryLoopDetector'
    
    def _add_suppressed_detection(self, detection: Dict[str, Any], detector_name: str, reason: str):
        """Add detection to suppressed list with metadata"""
        suppressed = detection.copy()
        suppressed['suppressed_by'] = detector_name
        suppressed['suppression_reason'] = reason
        suppressed['detector'] = detector_name
        self.suppressed_detections.append(suppressed)
    
    def _transfer_ownership(self, trace_id: str, old_owner: str, new_owner: str):
        """Transfer ownership and move old detections to suppressed"""
        # Find active detections from old owner for this trace
        to_suppress = []
        remaining_active = []
        
        for detection in self.active_detections:
            if detection.get('trace_id') == trace_id and detection.get('type', '').replace('_', '').replace(' ', '').lower() in old_owner.lower():
                to_suppress.append(detection)
            else:
                remaining_active.append(detection)
        
        # Move old detections to suppressed
        for detection in to_suppress:
            self._add_suppressed_detection(detection, old_owner, f"superseded_by:{new_owner}")
        
        self.active_detections = remaining_active
    
    def get_suppression_summary(self) -> Dict[str, Any]:
        """Generate suppression summary for transparency"""
        total_traces = len(set(d.get('trace_id') for d in self.active_detections + self.suppressed_detections if d.get('trace_id')))
        active_issues = len(self.active_detections)
        suppressed_count = len(self.suppressed_detections)
        
        # Group suppressed by reason
        suppression_breakdown = {}
        for detection in self.suppressed_detections:
            reason = detection.get('suppression_reason', 'unknown')
            suppression_breakdown[reason] = suppression_breakdown.get(reason, 0) + 1
        
        return {
            'total_traces_analyzed': total_traces,
            'active_issues': active_issues,
            'suppressed_issues': suppressed_count,
            'suppression_breakdown': suppression_breakdown,
            'trace_ownership': self.trace_ownership.copy()
        }


def load_suppression_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """📜 4. Load suppression rules from crashlens-policy.yaml"""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "crashlens-policy.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            policy = yaml.safe_load(f)
            return policy.get('suppression_rules', {})
    except Exception:
        return {}  # Default to no suppression rules


def load_pricing_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load pricing configuration from YAML file"""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "pricing.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        click.echo(f"⚠️  Warning: Could not load pricing config: {e}", err=True)
        return {}


def _generate_transparent_output(active_detections: List[Dict[str, Any]], 
                                suppression_engine: SuppressionEngine, 
                                summary: Dict[str, Any]) -> str:
    """📊 5. Generate human-centric output with transparency"""
    
    formatter = SummaryFormatter()
    
    # Calculate totals
    total_waste_cost = sum(d.get('waste_cost', 0) for d in active_detections)
    total_waste_tokens = sum(d.get('waste_tokens', 0) for d in active_detections)
    
    # Build report
    lines = [
        "🚨 **CrashLens Token Waste Report**",
        "=" * 50,
        f"📅 **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"🔍 **Traces Analyzed**: {summary['total_traces_analyzed']}",
        f"🧾 **Total AI Spend**: ${total_waste_cost:.2f}",
        f"💰 **Total Potential Savings**: ${total_waste_cost:.4f}",
        f"🎯 **Wasted Tokens**: {total_waste_tokens}",
        f"📊 **Issues Found**: {summary['active_issues']}"
    ]
    
    # Group detections by type for reporting
    detections_by_type = {}
    for detection in active_detections:
        detector_name = detection.get('type', 'unknown')
        if detector_name not in detections_by_type:
            detections_by_type[detector_name] = []
        detections_by_type[detector_name].append(detection)
    
    # Add detection details
    for detector_type, detections in detections_by_type.items():
        if not detections:
            continue
        
        display_name = DETECTOR_DISPLAY_NAMES.get(detector_type + 'Detector', detector_type.title())
        icon = {"retry_loop": "🔄", "fallback_storm": "⚡", "fallback_failure": "📢", "overkill_model": "❓"}.get(detector_type, "⚠️")
        
        lines.append(f"{icon} **{display_name}** ({len(detections)} issues)")
        
        sample_prompts = [d.get('sample_prompt', '')[:30] + '...' for d in detections[:2] if d.get('sample_prompt')]
        if sample_prompts:
            lines.append(f"  • Sample prompts: {', '.join(sample_prompts)}")
        
        waste_cost = sum(d.get('waste_cost', 0) for d in detections)
        if waste_cost > 0:
            lines.append(f"  • Est. waste: ${waste_cost:.4f}")
    
    # ✅ Bonus: Show suppression summary for transparency
    if summary['suppressed_issues'] > 0:
        lines.append("")
        lines.append("🛑 **Suppression Summary**")
        lines.append(f"  • {summary['suppressed_issues']} issues suppressed by higher-priority detectors")
        
        # Show suppressed detections if requested
        if suppression_engine.include_suppressed:
            lines.append("")
            lines.append("📋 **Suppressed Detections** (for transparency)")
            for detection in suppression_engine.suppressed_detections:
                trace_id = detection.get('trace_id', 'unknown')
                reason = detection.get('suppression_reason', 'unknown')
                detector = detection.get('detector', 'unknown')
                lines.append(f"  ⚠️ {DETECTOR_DISPLAY_NAMES.get(detector, detector)} suppressed for trace {trace_id}")
                lines.append(f"     Reason: {reason.replace('_', ' ').replace(':', ' by ')}")
    
    # Monthly projection
    monthly_savings = total_waste_cost * 30
    lines.append(f"📈 **Monthly Projection**: ${monthly_savings:.2f} potential savings")
    
    return "\n".join(lines)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CrashLens - Detect token waste in GPT API logs with production-grade suppression"""
    pass


@click.command()
@click.option('--include-suppressed', is_flag=True, help='✅ Include suppressed detections in output for transparency')
@click.option('--config', type=click.Path(path_type=Path), help='Path to configuration file')
@click.argument('logfile', type=click.Path(exists=True, path_type=Path), required=False)
def scan(logfile: Optional[Path] = None, include_suppressed: bool = False, config: Optional[Path] = None) -> str:
    """
    🎯 Scan logs for token waste patterns with production-grade suppression logic
    
    We don't double count waste. We trace root causes — not symptoms.
    """
    
    # Load configurations
    pricing_config = load_pricing_config(config)
    suppression_config = load_suppression_config(config)
    
    # Initialize suppression engine
    suppression_engine = SuppressionEngine(suppression_config, include_suppressed)
    
    # Initialize parser and load logs
    parser = LangfuseParser()
    traces = parser.parse_file(logfile) if logfile else {}
    
    if not traces:
        click.echo("⚠️  No traces found in input")
        return ""
    
    click.echo("🔒 CrashLens runs 100% locally. No data leaves your system.")
    
    # Load thresholds from pricing config
    thresholds = pricing_config.get('thresholds', {})
    
    # 🔢 1. Run detectors in priority order with suppression
    detector_configs = [
        ('RetryLoopDetector', RetryLoopDetector(
            max_retries=thresholds.get('retry_loop', {}).get('max_retries', 3),
            time_window_minutes=thresholds.get('retry_loop', {}).get('time_window_minutes', 5),
            max_retry_interval_minutes=thresholds.get('retry_loop', {}).get('max_retry_interval_minutes', 2)
        )),
        ('FallbackStormDetector', FallbackStormDetector(
            min_calls=thresholds.get('fallback_storm', {}).get('min_calls', 3),
            min_models=thresholds.get('fallback_storm', {}).get('min_models', 2),
            max_trace_window_minutes=thresholds.get('fallback_storm', {}).get('max_trace_window_minutes', 3)
        )),
        ('FallbackFailureDetector', FallbackFailureDetector(
            time_window_seconds=thresholds.get('fallback_failure', {}).get('time_window_seconds', 300)
        )),
        ('OverkillModelDetector', OverkillModelDetector(
            max_prompt_tokens_for_overkill=thresholds.get('overkill', {}).get('max_prompt_tokens', 20),
            max_prompt_chars=thresholds.get('overkill', {}).get('max_prompt_chars', 150)
        ))
    ]
    
    all_active_detections = []
    
    # Process each detector in priority order
    for detector_name, detector in detector_configs:
        try:
            # Run detector
            if hasattr(detector, 'detect'):
                if 'already_flagged_ids' in detector.detect.__code__.co_varnames:
                    # Detector supports suppression
                    already_flagged = set(suppression_engine.trace_ownership.keys())
                    raw_detections = detector.detect(traces, pricing_config.get('models', {}), already_flagged)
                else:
                    # Basic detector
                    raw_detections = detector.detect(traces, pricing_config.get('models', {}))
            else:
                raw_detections = []
            
            # Process through suppression engine
            active_detections = suppression_engine.process_detections(detector_name, raw_detections)
            all_active_detections.extend(active_detections)
            
        except Exception as e:
            click.echo(f"⚠️  Warning: {detector_name} failed: {e}", err=True)
            continue
    
    # Get suppression summary
    summary = suppression_engine.get_suppression_summary()
    
    # Generate output with transparency
    output = _generate_transparent_output(all_active_detections, suppression_engine, summary)
    
    click.echo(output)
    return output


# Add the scan command to CLI
cli.add_command(scan)


if __name__ == "__main__":
    cli()
