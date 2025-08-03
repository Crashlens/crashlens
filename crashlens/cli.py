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

# Detector display names for output formatting
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






def generate_detailed_reports(
    traces: Dict[str, List[Dict[str, Any]]], 
    detections: List[Dict[str, Any]], 
    output_dir: Path, 
    model_pricing: Dict[str, Any]
) -> int:
    """Generate detailed grouped JSON reports by detector category
    
    Args:
        traces: Dictionary of trace_id -> list of records
        detections: List of all detection results
        output_dir: Directory to save detailed reports
        model_pricing: Model pricing configuration
        
    Returns:
        Number of reports generated
    """
    import json
    from collections import defaultdict
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Group detections by detector type
    detections_by_type = defaultdict(list)
    for detection in detections:
        detector_type = detection.get('type', 'unknown')
        detections_by_type[detector_type].append(detection)
    
    # Generate detector display names mapping
    detector_display_names = {
        'retry_loop': 'Retry Loop Detector',
        'fallback_storm': 'Fallback Storm Detector',
        'fallback_failure': 'Fallback Failure Detector', 
        'overkill_model': 'Overkill Model Detector'
    }
    
    # Suggestion mappings
    detector_suggestions = {
        'retry_loop': [
            "Implement exponential backoff for retries",
            "Add circuit breakers to prevent retry storms",
            "Set maximum retry limits (e.g., 3 retries max)"
        ],
        'fallback_storm': [
            "Optimize model selection logic",
            "Use deterministic routing instead of chaotic fallbacks", 
            "Implement proper model prioritization"
        ],
        'fallback_failure': [
            "Remove redundant expensive fallback calls",
            "Use cheaper models as primary option",
            "Only fallback when cheaper models actually fail"
        ],
        'overkill_model': [
            "Route simple prompts to cheaper models (e.g., gpt-3.5-turbo)",
            "Implement prompt length-based model selection",
            "Use GPT-4 only for complex reasoning tasks"
        ]
    }
    
    reports_generated = 0
    
    # Process each detector type
    for detector_type, type_detections in detections_by_type.items():
        if not type_detections:
            continue
        
        detector_name = detector_display_names.get(detector_type, detector_type.title())
        
        # Format issues for this detector type
        issues = []
        total_waste_cost = 0.0
        total_waste_tokens = 0
        affected_traces = set()
        
        for detection in type_detections:
            trace_id = detection.get('trace_id', '')
            affected_traces.add(trace_id)
            
            issue = {
                'trace_id': trace_id,
                'problem': detection.get('description', 'Unknown issue'),
                'estimated_cost': round(detection.get('waste_cost', 0), 6),
                'waste_tokens': detection.get('waste_tokens', 0),
                'severity': detection.get('severity', 'medium')
            }
            
            # Add detector-specific details
            if detector_type == 'retry_loop':
                issue['retry_count'] = detection.get('retry_count', 0)
                issue['models_involved'] = detection.get('models_used', [])
            elif detector_type == 'fallback_storm':
                issue['models_used'] = detection.get('models_used', [])
                issue['num_calls'] = detection.get('num_calls', 0)
            elif detector_type == 'fallback_failure':
                issue['expensive_model'] = detection.get('model_used', '')
                issue['cheaper_model'] = detection.get('suggested_model', '')
            elif detector_type == 'overkill_model':
                issue['expensive_model'] = detection.get('model_used', '')
                issue['suggested_model'] = detection.get('suggested_model', '')
            
            issues.append(issue)
            total_waste_cost += detection.get('waste_cost', 0)
            total_waste_tokens += detection.get('waste_tokens', 0)
        
        # Calculate additional metadata
        models_involved = set()
        for trace_id in affected_traces:
            if trace_id in traces:
                for record in traces[trace_id]:
                    model = record.get('model', record.get('input', {}).get('model', 'unknown'))
                    models_involved.add(model)
        
        # Create grouped report
        report = {
            'detector_type': detector_name,
            'summary': {
                'total_issues': len(issues),
                'affected_traces': len(affected_traces),
                'total_waste_cost': round(total_waste_cost, 6),
                'total_waste_tokens': total_waste_tokens,
                'models_involved': sorted(list(models_involved))
            },
            'issues': issues,
            'suggestions': detector_suggestions.get(detector_type, []),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'detector_category': detector_type
            }
        }
        
        # Write report to file
        output_file = output_dir / f"{detector_type}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            reports_generated += 1
        except Exception as e:
            click.echo(f"⚠️  Warning: Failed to write {detector_type} report: {e}", err=True)
    
    return reports_generated


def _calculate_trace_time_span(records: List[Dict[str, Any]]) -> float:
    """Calculate time span of trace records in minutes"""
    if len(records) < 2:
        return 0.0
    
    try:
        timestamps = []
        for record in records:
            ts_str = record.get('startTime', '')
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return 0.0
        
        span = max(timestamps) - min(timestamps)
        return round(span.total_seconds() / 60, 2)
        
    except (ValueError, TypeError):
        return 0.0


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CrashLens - Detect token waste in GPT API logs with production-grade suppression"""
    pass


@click.command()
@click.argument('logfile', type=click.Path(path_type=Path), required=False)
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['slack', 'markdown', 'json'], case_sensitive=False),
              default='slack', help='Output format')
@click.option('--config', '-c', type=click.Path(path_type=Path),
              help='Custom pricing config file path')
@click.option('--log-format', default='langfuse-v1',
              help='Specify the input log format version (e.g., langfuse-v1, langfuse-v2)')
@click.option('--demo', is_flag=True, help='Use built-in demo data')
@click.option('--stdin', is_flag=True, help='Read from standard input')
@click.option('--paste', is_flag=True, help='Read JSONL data from clipboard')
@click.option('--summary', is_flag=True, help='Show cost summary with breakdown')
@click.option('--summary-only', is_flag=True, help='Summary without trace IDs')
@click.option('--detailed', is_flag=True, help='Generate detailed per-trace JSON reports')
@click.option('--detailed-dir', type=click.Path(path_type=Path), default='detailed_output', 
              help='Directory for detailed reports (default: detailed_output)')
@click.option('--contract-check', is_flag=True, help='Validate logs against schema contract and exit')
@click.option('--contract-info', is_flag=True, help='Show schema contract information and exit')
@click.option('--output', type=click.Choice(['text', 'json'], case_sensitive=False), 
              default='text', help='Output format for contract validation results')
def scan(logfile: Optional[Path] = None, output_format: str = 'slack', config: Optional[Path] = None, 
         log_format: str = 'langfuse-v1', demo: bool = False, stdin: bool = False, paste: bool = False, 
         summary: bool = False, summary_only: bool = False, detailed: bool = False, 
         detailed_dir: Path = Path('detailed_output'), contract_check: bool = False, 
         contract_info: bool = False, output: str = 'text') -> str:
    """Scan logs for token waste patterns with production-grade suppression logic

    Examples:

  crashlens scan logs.jsonl                    # Scan a specific log file
  crashlens scan --demo                        # Run on built-in sample logs
  cat logs.jsonl | crashlens scan --stdin      # Pipe logs via stdin
  crashlens scan --paste                       # Read logs from clipboard
  crashlens scan --detailed                    # Generate traces JSON reports
  crashlens scan --summary                     # Cost summary with categories
  crashlens scan --summary-only                # Show summary only
  
  Schema Contract Validation:
  crashlens scan --contract-check logs.jsonl   # Validate schema contracts
  crashlens scan --contract-info               # Show contract requirements
  crashlens scan --contract-check --output json logs.jsonl  # JSON output format
  cat logs.jsonl | crashlens scan --contract-check --stdin  # Validate via stdin

    """
    
    # Validate input options (skip for contract-info which doesn't need input)
    if not contract_info:
        input_count = sum([bool(logfile), demo, stdin, paste])
        if input_count == 0:
            click.echo("Error: Must specify input source: file path, --demo, --stdin, or --paste")
            click.echo("Try: crashlens scan --help")
            sys.exit(1)
        elif input_count > 1:
            click.echo("Error: Cannot use multiple input sources simultaneously")
            click.echo("💡 Choose one: file path, --demo, --stdin, or --paste")
            sys.exit(1)
    
    # Handle contract check mode - exit early if requested
    if contract_check or contract_info:
        from .cli_runner import run_contract_check_cli
        
        # Determine verbose mode from any existing verbose flags (future-proofing)
        verbose_mode = False  # Can be enhanced later with explicit --verbose flag
        
        # Map input sources for contract check
        source_file = str(logfile) if logfile else None
        
        exit_code = run_contract_check_cli(
            logfile=source_file,
            log_format=log_format,
            stdin_mode=stdin,
            paste_mode=paste,
            verbose=verbose_mode,
            show_info=contract_info,
            output_format=output
        )
        sys.exit(exit_code)
    
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
    
    # Parse log format version and initialize version-aware parser
    if log_format.startswith("langfuse-"):
        schema_version = log_format.split("-")[1]  # extracts 'v1', 'v2', etc.
        click.echo(f"🔄 Using Langfuse parser with schema version: {schema_version}")
        parser = LangfuseParser(default_schema=schema_version)
    else:
        click.echo(f"❌ Error: Unsupported log format: {log_format}")
        click.echo("💡 Supported formats: langfuse-v1, langfuse-v2")
        sys.exit(1)
    
    # Initialize parser and load logs based on input source
    traces = {}
    
    try:
        if demo:
            # Use built-in demo data
            demo_file = Path(__file__).parent.parent / "examples-logs" / "demo-logs.jsonl"
            if not demo_file.exists():
                click.echo("❌ Error: Demo file not found. Please check installation.")
                sys.exit(1)
            click.echo("🎬 Running analysis on built-in demo data...")
            traces = parser.parse_file(demo_file) or {}
        
        elif stdin:
            # Read from standard input
            click.echo("📥 Reading JSONL data from standard input...")
            try:
                traces = parser.parse_stdin() or {}
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
                
                click.echo(f"Processing {len(lines)} lines from clipboard...")
                
                # Join lines and parse as string
                jsonl_text = '\n'.join(lines)
                traces = parser.parse_string(jsonl_text) or {}
                
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
            traces = parser.parse_file(logfile) or {}
        
    except Exception as e:
        click.echo(f"❌ Error reading input: {e}", err=True)
        sys.exit(1)
    
    if not traces:
        source = "demo data" if demo else "standard input" if stdin else "pasted data" if paste else "log file"
        click.echo(f"⚠️  No traces found in {source}")
        return ""
    
    # click.echo("🔒 CrashLens runs 100% locally. No data leaves your system.")
    
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
    suppression_summary = suppression_engine.get_suppression_summary()
    
    # Generate detailed per-trace reports if requested
    if detailed:
        detailed_count = generate_detailed_reports(
            traces, all_active_detections, detailed_dir, pricing_config.get('models', {})
        )
        click.echo(f"✅ Generated {detailed_count} detailed category reports in {detailed_dir}/")
    
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