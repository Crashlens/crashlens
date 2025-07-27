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
    
    def __init__(self, suppression_config: Optional[Dict[str, Any]] = None):
        self.suppression_config = suppression_config or {}
        
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
            
            # Check trace ownership and priority (only if not disabled by config)
            if trace_id in self.trace_ownership:
                current_owner = self.trace_ownership[trace_id]
                current_priority = DETECTOR_PRIORITY.get(detector_name, 999)
                owner_priority = DETECTOR_PRIORITY.get(current_owner, 999)
                
                # 🧰 3. Suppression Hook: Priority-based suppression (configurable)
                if self._should_suppress_by_priority(detector_name, current_priority, owner_priority):
                    # Current detector has lower priority, suppress this detection
                    self._add_suppressed_detection(detection, detector_name, f"higher_priority_detector:{current_owner}")
                    continue
                elif current_priority < owner_priority:
                    # Current detector has higher priority, it takes ownership
                    # Move previous owner's detections to suppressed (only if priority suppression enabled)
                    if self._should_suppress_by_priority(current_owner, owner_priority, current_priority):
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
        # Get the detector config (remove 'Detector' suffix and convert to lowercase)
        config_key = detector_name.lower().replace('detector', '').replace('_', '')
        if config_key in ['retryloop']:
            config_key = 'retry_loop'
        elif config_key == 'fallbackstorm':
            config_key = 'fallback_storm'
        elif config_key == 'fallbackfailure':
            config_key = 'fallback_failure'
        elif config_key == 'overkillmodel':
            config_key = 'overkill_model'
        
        detector_config = self.suppression_config.get(config_key, {})
        
        # Check suppression rules
        if detector_config.get('suppress_if_retry_loop', False):
            return self.trace_ownership.get(trace_id) == 'RetryLoopDetector'
        
        return False
    
    def _should_suppress_by_priority(self, detector_name: str, current_priority: int, owner_priority: int) -> bool:
        """Check if detector should be suppressed by priority logic"""
        # Get the detector config
        config_key = detector_name.lower().replace('detector', '').replace('_', '')
        if config_key in ['retryloop']:
            config_key = 'retry_loop'
        elif config_key == 'fallbackstorm':
            config_key = 'fallback_storm'
        elif config_key == 'fallbackfailure':
            config_key = 'fallback_failure'
        elif config_key == 'overkillmodel':
            config_key = 'overkill_model'
        
        detector_config = self.suppression_config.get(config_key, {})
        
        # If suppress_if_retry_loop is False, allow coexistence (no priority suppression)
        if not detector_config.get('suppress_if_retry_loop', True):
            return False
        
        # Otherwise, use priority suppression
        return current_priority > owner_priority
    
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





def _format_human_readable(active_detections: List[Dict[str, Any]], total_waste_cost: float, traces: Dict[str, List[Dict[str, Any]]] = None, model_pricing: Dict[str, Any] = None) -> str:
    """📊 Generate comprehensive human-centric output with detailed information"""
    
    # Calculate additional metrics
    total_traces = len(traces) if traces else 0
    total_waste_tokens = sum(d.get('waste_tokens', 0) for d in active_detections)
    
    # Calculate model breakdown
    model_costs = {}
    if traces and model_pricing:
        for trace_id, records in traces.items():
            for record in records:
                model = record.get('model') or record.get('input', {}).get('model', 'unknown')
                if 'usage' in record:
                    usage = record.get('usage', {})
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)
                else:
                    prompt_tokens = record.get('prompt_tokens', 0)
                    completion_tokens = record.get('completion_tokens', 0)
                
                if model in model_pricing:
                    model_config = model_pricing[model]
                    input_cost_per_1k = model_config.get('input_cost_per_1k', 0)
                    output_cost_per_1k = model_config.get('output_cost_per_1k', 0)
                    input_cost_per_1m = model_config.get('input_cost_per_1m', 0)
                    output_cost_per_1m = model_config.get('output_cost_per_1m', 0)
                    
                    if input_cost_per_1k > 0:
                        input_cost = input_cost_per_1k / 1000
                    else:
                        input_cost = input_cost_per_1m / 1000000
                        
                    if output_cost_per_1k > 0:
                        output_cost = output_cost_per_1k / 1000
                    else:
                        output_cost = output_cost_per_1m / 1000000
                    
                    cost = (prompt_tokens * input_cost) + (completion_tokens * output_cost)
                    model_costs[model] = model_costs.get(model, 0) + cost
    
    lines = [
        "🚨 **CrashLens Token Waste Report**",
        "=" * 60,
        f"📅 **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"🔍 **Traces Analyzed**: {total_traces:,}",
        f"💰 **Total AI Spend**: ${sum(model_costs.values()):.4f}",
        f"💸 **Total Potential Savings**: ${total_waste_cost:.4f}",
        f"📊 **Issues Found**: {len(active_detections)}",
        f"🎯 **Wasted Tokens**: {total_waste_tokens:,}",
        ""
    ]
    
    # Add model breakdown
    if model_costs:
        lines.append("📈 **Cost by Model**:")
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
        for model, cost in sorted_models[:5]:  # Top 5 models
            percentage = (cost / sum(model_costs.values())) * 100
            lines.append(f"  • {model}: ${cost:.4f} ({percentage:.1f}%)")
        lines.append("")
    
    # Group detections by type for reporting
    detections_by_type = {}
    for detection in active_detections:
        detector_name = detection.get('type', 'unknown')
        if detector_name not in detections_by_type:
            detections_by_type[detector_name] = []
        detections_by_type[detector_name].append(detection)
    
    # Add detection details
    lines.append("🔍 **Issue Breakdown**:")
    for detector_type, detections in detections_by_type.items():
        if not detections:
            continue
        
        display_name = DETECTOR_DISPLAY_NAMES.get(detector_type + 'Detector', detector_type.title())
        icon = {"retry_loop": "🔄", "fallback_storm": "⚡", "fallback_failure": "📢", "overkill_model": "❓"}.get(detector_type, "⚠️")
        
        waste_cost = sum(d.get('waste_cost', 0) for d in detections)
        waste_tokens = sum(d.get('waste_tokens', 0) for d in detections)
        
        lines.append(f"{icon} **{display_name}** ({len(detections)} issues)")
        lines.append(f"  💰 Waste Cost: ${waste_cost:.4f}")
        lines.append(f"  🎯 Waste Tokens: {waste_tokens:,}")
        
        # Add sample prompts
        sample_prompts = [d.get('sample_prompt', '')[:50] + '...' for d in detections[:3] if d.get('sample_prompt')]
        if sample_prompts:
            lines.append(f"  📝 Sample prompts: {', '.join(sample_prompts)}")
        
        # Add trace IDs for first few
        trace_ids = [d.get('trace_id', '') for d in detections[:5] if d.get('trace_id')]
        if trace_ids:
            lines.append(f"  🔗 Sample traces: {', '.join(trace_ids)}")
        
        lines.append("")
    
    # Add recommendations
    lines.append("💡 **Recommendations**:")
    if detections_by_type.get('overkill_model'):
        lines.append("  • Consider using cheaper models for simple tasks")
    if detections_by_type.get('retry_loop'):
        lines.append("  • Implement exponential backoff for retries")
    if detections_by_type.get('fallback_storm'):
        lines.append("  • Optimize model selection strategy")
    if detections_by_type.get('fallback_failure'):
        lines.append("  • Remove unnecessary fallbacks")
    
    lines.append("")
    lines.append("📊 **Monthly Projection**:")
    monthly_savings = total_waste_cost * 30
    lines.append(f"  💰 Potential monthly savings: ${monthly_savings:.2f}")
    
    return "\n".join(lines)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CrashLens - Detect token waste in GPT API logs with production-grade suppression"""
    pass


@click.command()
@click.argument('logfile', type=click.Path(path_type=Path), required=False)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['slack', 'markdown', 'json', 'human'], case_sensitive=False),
              default='slack', help='Output format')
@click.option('--config', '-c', type=click.Path(path_type=Path),
              help='Custom pricing config file path')
@click.option('--demo', is_flag=True, help='Use built-in demo data')
@click.option('--stdin', is_flag=True, help='Read from standard input')
@click.option('--paste', is_flag=True, help='Read JSONL data from clipboard')
@click.option('--summary', is_flag=True, help='Show cost summary with breakdown')
@click.option('--summary-only', is_flag=True, help='Summary without trace IDs')
def scan(logfile: Optional[Path] = None, output_format: str = 'slack', config: Optional[Path] = None, 
         demo: bool = False, stdin: bool = False, paste: bool = False, summary: bool = False, 
         summary_only: bool = False) -> str:
    """🎯 Scan logs for token waste patterns with production-grade suppression logic

    Examples:
      crashlens scan logs.jsonl              # Scan a specific file
      crashlens scan --demo                              # Use built-in demo data
      cat logs.jsonl | crashlens scan --stdin            # Read from pipe
      crashlens scan --paste                             # Read from clipboard"""
    
    # Validate input options
    input_count = sum([bool(logfile), demo, stdin, paste])
    if input_count == 0:
        click.echo("❌ Error: Must specify input source: file path, --demo, --stdin, or --paste")
        click.echo("💡 Try: crashlens scan --help")
        sys.exit(1)
    elif input_count > 1:
        click.echo("❌ Error: Cannot use multiple input sources simultaneously")
        click.echo("💡 Choose one: file path, --demo, --stdin, or --paste")
        sys.exit(1)
    
    # Validate summary options
    if summary and summary_only:
        click.echo("❌ Error: Cannot use --summary and --summary-only together")
        click.echo("💡 Choose one: --summary OR --summary-only")
        sys.exit(1)

    # File existence check for logfile
    if logfile and not logfile.exists():
        click.echo(f"❌ Error: File not found: {logfile}", err=True)
        sys.exit(1)
    
    # Load configurations
    pricing_config = load_pricing_config(config)
    suppression_config = load_suppression_config(config)
    
    # Initialize suppression engine
    suppression_engine = SuppressionEngine(suppression_config)
    
    # Initialize parser and load logs based on input source
    parser = LangfuseParser()
    traces = {}
    
    try:
        if demo:
            # Use built-in demo data
            demo_file = Path(__file__).parent.parent / "examples" / "demo-logs.jsonl"
            if not demo_file.exists():
                click.echo("❌ Error: Demo file not found. Please check installation.")
                sys.exit(1)
            click.echo("🎬 Running analysis on built-in demo data...")
            traces = parser.parse_file(demo_file)
        
        elif stdin:
            # Read from standard input
            click.echo("📥 Reading JSONL data from standard input...")
            try:
                traces = parser.parse_stdin()
            except KeyboardInterrupt:
                click.echo("\n⚠️  Input cancelled by user")
                sys.exit(1)
        
        elif paste:
            # Clipboard paste mode - automatically read from clipboard
            try:
                import pyperclip
                click.echo("📋 Reading JSONL data from clipboard...")
                
                # Get data from clipboard
                clipboard_text = pyperclip.paste()
                
                if not clipboard_text.strip():
                    click.echo("❌ Error: Clipboard is empty or contains no data")
                    click.echo("💡 Copy some JSONL data to your clipboard first, then run this command")
                    sys.exit(1)
                
                # Split into lines and filter empty lines
                lines = [line.strip() for line in clipboard_text.splitlines() if line.strip()]
                
                if not lines:
                    click.echo("❌ Error: No valid JSONL lines found in clipboard")
                    click.echo("💡 Make sure your clipboard contains JSONL data (one JSON object per line)")
                    sys.exit(1)
                
                click.echo(f"📊 Processing {len(lines)} lines from clipboard...")
                
                # Join lines and parse as string
                jsonl_text = '\n'.join(lines)
                traces = parser.parse_string(jsonl_text)
                
            except ImportError:
                click.echo("❌ Error: pyperclip library not available")
                click.echo("💡 Install with: pip install pyperclip")
                sys.exit(1)
            except Exception as e:
                click.echo(f"❌ Error reading from clipboard: {e}", err=True)
                click.echo("💡 Make sure your clipboard contains valid JSONL data")
                sys.exit(1)
        
        elif logfile:
            # Read from specified file
            traces = parser.parse_file(logfile)
        
    except Exception as e:
        click.echo(f"❌ Error reading input: {e}", err=True)
        sys.exit(1)
    
    if not traces:
        source = "demo data" if demo else "standard input" if stdin else "pasted data" if paste else "log file"
        click.echo(f"⚠️  No traces found in {source}")
        return ""
    
    click.echo("🔒 CrashLens runs 100% locally. No data leaves your system.")
    
    # Handle summary modes
    if summary or summary_only:
        # Run detectors to get waste analysis
        all_active_detections = []
        
        # Load thresholds from pricing config
        thresholds = pricing_config.get('thresholds', {})
        
        # Run detectors in priority order
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
                max_prompt_tokens=thresholds.get('overkill_model', {}).get('max_prompt_tokens', 20),
                max_prompt_chars=thresholds.get('overkill_model', {}).get('max_prompt_chars', 150)
            ))
        ]
        
        # Process each detector
        for detector_name, detector in detector_configs:
            try:
                if hasattr(detector, 'detect'):
                    if 'already_flagged_ids' in detector.detect.__code__.co_varnames:
                        already_flagged = set(suppression_engine.trace_ownership.keys())
                        raw_detections = detector.detect(traces, pricing_config.get('models', {}), already_flagged)
                    else:
                        raw_detections = detector.detect(traces, pricing_config.get('models', {}))
                else:
                    raw_detections = []
                
                # Process through suppression engine
                active_detections = suppression_engine.process_detections(detector_name, raw_detections)
                all_active_detections.extend(active_detections)
                
            except Exception as e:
                click.echo(f"⚠️  Warning: {detector_name} failed: {e}", err=True)
                continue
        
        # Use SummaryFormatter for cost breakdown with waste analysis
        summary_formatter = SummaryFormatter()
        output = summary_formatter.format(traces, pricing_config.get('models', {}), summary_only, all_active_detections)
        
        # Write to report.md
        report_path = Path.cwd() / "report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        summary_type = "Summary-only" if summary_only else "Summary"
        click.echo(f"✅ {summary_type} report written to {report_path}")
        click.echo(output)
        return output
    
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
            max_prompt_tokens=thresholds.get('overkill_model', {}).get('max_prompt_tokens', 20),
            max_prompt_chars=thresholds.get('overkill_model', {}).get('max_prompt_chars', 150)
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
    
    # Generate report based on format and write to report.md
    report_path = Path.cwd() / "report.md"
    
    if output_format == 'json':
        # Machine-readable JSON output
        import json
        json_output = []
        for detection in all_active_detections:
            json_detection = {
                'type': detection.get('type'),
                'severity': detection.get('severity'),
                'description': detection.get('description'),
                'waste_cost': f"{detection.get('waste_cost', 0):.6f}",
                'suppression_notes': detection.get('suppression_notes', {})
            }
            if 'trace_id' in detection:
                json_detection['trace_id'] = detection['trace_id']
            json_output.append(json_detection)
        
        output = json.dumps(json_output, indent=2)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(output)
        click.echo(f"✅ JSON report written to {report_path}")
        click.echo(output)
        return output
    elif output_format == 'human':
        # Human-readable terminal output
        total_waste_cost = sum(d.get('waste_cost', 0) for d in all_active_detections)
        output = _format_human_readable(all_active_detections, total_waste_cost, traces, pricing_config.get('models', {}))
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(output)
        click.echo(f"✅ Human-readable report written to {report_path}")
        click.echo(output)
        return output
    elif output_format == 'markdown':
        # Markdown format
        formatter = MarkdownFormatter()
        output = formatter.format(all_active_detections, traces, pricing_config.get('models', {}), summary_only=False)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(output)
        click.echo(f"✅ Markdown report written to {report_path}")
        click.echo(output)
        return output
    else:
        # Default Slack format
        formatter = SlackFormatter()
        output = formatter.format(all_active_detections, traces, pricing_config.get('models', {}))
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(output)
        click.echo(f"✅ Slack report written to {report_path}")
        click.echo(output)
        return output


# Add the scan command to CLI
cli.add_command(scan)


if __name__ == "__main__":
    cli()