#!/usr/bin/env python3
"""
CrashLens CLI - Token Waste Detection Tool
Scans Langfuse-style JSONL logs for inefficient GPT API usage patterns.
Production-grade suppression and priority logic for accurate root cause attribution.
"""

import click
import sys
import yaml
import os
import json
import random
import uuid
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Set, Tuple

# Optional imports for enhanced functionality
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False

# Optional imports for version detection
try:
    import importlib.metadata
    HAS_IMPORTLIB_METADATA = True
except ImportError:
    HAS_IMPORTLIB_METADATA = False

from .parsers.langfuse import LangfuseParser
from .detectors.retry_loops import RetryLoopDetector
from .detectors.fallback_storm import FallbackStormDetector
from .detectors.fallback_failure import FallbackFailureDetector
from .detectors.overkill_model_detector import OverkillModelDetector
from .reporters.slack_formatter import SlackFormatter
from .reporters.markdown_formatter import MarkdownFormatter
from .reporters.summary_formatter import SummaryFormatter
from .reporters.policy_report_markdown import PolicyReportMarkdown
from .reporters.policy_report_json import PolicyReportJSON
from .langfuse_client import LangfuseClient, save_logs_to_temp_file
from .helicone_client import HeliconeClient
from .policy.templates import get_template_manager
from .policy.engine import PolicyEngine


# =============================================================================
# Version Detection Function
# =============================================================================

def _get_current_cli_version() -> str:
    """Get the current CLI version."""
    try:
        # Use importlib.metadata (Python 3.8+)
        if HAS_IMPORTLIB_METADATA:
            return importlib.metadata.version('crashlens')
    except Exception:
        pass
    
    # Fallback version
    return "1.0.0"


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
                
                # Debug output
                # print(f"DEBUG: {detector_name} (priority {current_priority}) checking trace {trace_id} owned by {current_owner} (priority {owner_priority})")
                
                # 🧰 3. Suppression Hook: Priority-based suppression (configurable)
                if self._should_suppress_by_priority(detector_name, current_priority, owner_priority):
                    # Current detector has lower priority, suppress this detection
                    # print(f"DEBUG: Suppressing {detector_name} detection for {trace_id} - owned by higher priority {current_owner}")
                    self._add_suppressed_detection(detection, detector_name, f"higher_priority_detector:{current_owner}")
                    continue
                elif current_priority < owner_priority:
                    # Current detector has higher priority, it takes ownership
                    # Move previous owner's detections to suppressed (only if priority suppression enabled)
                    # print(f"DEBUG: {detector_name} taking ownership of {trace_id} from {current_owner}")
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
        
        # Otherwise, use priority suppression (lower number = higher priority)
        return current_priority > owner_priority
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
            suppression_rules = policy.get('suppression_rules', {})
            # Debug: Print loaded rules to verify they're loaded
            # print(f"DEBUG: Loaded suppression rules: {suppression_rules}")
            return suppression_rules
    except Exception as e:
        click.echo(f"⚠️  Warning: Could not load suppression config: {e}", err=True)
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
@click.version_option(version=_get_current_cli_version() or "unknown")
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
@click.option('--demo', is_flag=True, help='Use built-in demo data')
@click.option('--stdin', is_flag=True, help='Read from standard input')
@click.option('--paste', is_flag=True, help='Read JSONL data from clipboard')
@click.option('--summary', is_flag=True, help='Show cost summary with breakdown')
@click.option('--summary-only', is_flag=True, help='Summary without trace IDs')
@click.option('--detailed', is_flag=True, help='Generate detailed per-trace JSON reports')
@click.option('--detailed-dir', type=click.Path(path_type=Path), default='detailed_output', 
              help='Directory for detailed reports (default: detailed_output)')
@click.option('--from-langfuse', is_flag=True, help='Fetch traces from Langfuse API and analyze')
@click.option('--from-helicone', is_flag=True, help='Fetch requests from Helicone API and analyze')
@click.option('--hours-back', default=24, help='Hours back to fetch (for --from-langfuse/--from-helicone)')
@click.option('--limit', default=1000, help='Max traces/requests to fetch (for --from-langfuse/--from-helicone)')
@click.option('--policy-template', help='Use built-in policy template(s) (comma-separated or "all")')
@click.option('--policy-file', type=click.Path(path_type=Path), help='Use custom policy file')
@click.option('--list-templates', is_flag=True, help='List available policy templates and exit')
def scan(logfile: Optional[Path] = None, output_format: str = 'slack', config: Optional[Path] = None, 
         demo: bool = False, stdin: bool = False, paste: bool = False, summary: bool = False, 
         summary_only: bool = False, detailed: bool = False, detailed_dir: Path = Path('detailed_output'),
         from_langfuse: bool = False, from_helicone: bool = False, hours_back: int = 24, limit: int = 1000,
         policy_template: Optional[str] = None, policy_file: Optional[Path] = None, list_templates: bool = False) -> str:
    """🎯 Scan logs for token waste patterns with production-grade suppression logic

    📦 Examples:

  crashlens scan logs.jsonl                    # Scan a specific log file
  crashlens scan --demo                        # Run on built-in sample logs
  cat logs.jsonl | crashlens scan --stdin      # Pipe logs via stdin
  crashlens scan --paste                                 # Read logs from clipboard
  crashlens scan --detailed                    # Generate traces JSON reports
  crashlens scan --summary                     # Cost summary with categories
  crashlens scan --summary-only                # Show summary only 
  crashlens scan --from-langfuse               # Fetch from Langfuse API and analyze
  crashlens scan --from-helicone --hours-back 48 # Fetch from Helicone API (48h) and analyze
  crashlens scan --policy-template retry-loop-prevention logs.jsonl  # Use policy template
  crashlens scan --policy-template all logs.jsonl  # Use all templates
  crashlens scan --list-templates              # List available templates

    """
    
    # Handle template listing
    if list_templates:
        template_manager = get_template_manager()
        template_manager.list_templates()
        return ""
    
    # Validate input options
    input_count = sum([bool(logfile), demo, stdin, paste, from_langfuse, from_helicone])
    if input_count == 0:
        click.echo("❌ Error: Must specify input source: file path, --demo, --stdin, --paste, --from-langfuse, or --from-helicone")
        click.echo("💡 Try: crashlens scan --help")
        sys.exit(1)
    elif input_count > 1:
        click.echo("❌ Error: Cannot use multiple input sources simultaneously")
        click.echo("💡 Choose one: file path, --demo, --stdin, --paste, --from-langfuse, or --from-helicone")
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
                
                # Check for parsing errors and stop if there are problems
                if parser.has_parsing_errors():
                    parsing_stats = parser.get_parsing_stats()
                    error_msg = []
                    if parsing_stats['skipped_records'] > 0:
                        error_msg.append(f"❌ {parsing_stats['skipped_records']} lines had JSON parsing errors")
                    if parsing_stats['warning_records'] > 0:
                        error_msg.append(f"⚠️ {parsing_stats['warning_records']} records had data quality issues (missing fields)")
                    
                    click.echo("STOP: Data quality issues detected. Analysis cannot proceed.")
                    click.echo(" ".join(error_msg))
                    click.echo("HINT: Please fix the input data issues before running the analysis.")
                    click.echo("INFO: Check the error/warning messages above for specific line numbers and issues.")
                    sys.exit(1)
                    
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
                traces = parser.parse_string(jsonl_text) or {}
                
                # Check for parsing errors and stop if there are problems
                if parser.has_parsing_errors():
                    parsing_stats = parser.get_parsing_stats()
                    click.echo(f"❌ Parsing errors detected! {parsing_stats['skipped_records']} lines had errors.")
                    click.echo("💡 Please fix the malformed clipboard data before running the analysis.")
                    click.echo("🔍 Check the error messages above for specific line numbers and issues.")
                    sys.exit(1)
                
            except ImportError:
                click.echo("❌ Error: pyperclip library not available")
                click.echo("💡 Install with: pip install pyperclip")
                sys.exit(1)
            except Exception as e:
                click.echo(f"❌ Error reading from clipboard: {e}", err=True)
                click.echo("💡 Make sure your clipboard contains valid JSONL data")
                sys.exit(1)
        
        elif from_langfuse:
            # Fetch from Langfuse API
            try:
                click.echo(f"🔗 Fetching traces from Langfuse (last {hours_back} hours, max {limit} traces)...")
                client = LangfuseClient()
                logs = client.fetch_traces(hours_back=hours_back, limit=limit)
                
                if not logs:
                    click.echo("⚠️  No traces found in Langfuse for the specified time range.")
                    return ""
                
                click.echo(f"✅ Successfully fetched {len(logs)} traces from Langfuse")
                
                # Save to temporary file and parse
                temp_path = save_logs_to_temp_file(logs)
                traces = parser.parse_file(temp_path) or {}
                
                # Check for parsing errors and stop if there are problems
                if parser.has_parsing_errors():
                    parsing_stats = parser.get_parsing_stats()
                    error_msg = []
                    if parsing_stats['skipped_records'] > 0:
                        error_msg.append(f"❌ {parsing_stats['skipped_records']} lines had JSON parsing errors")
                    if parsing_stats['warning_records'] > 0:
                        error_msg.append(f"⚠️ {parsing_stats['warning_records']} records had data quality issues (missing fields)")
                    
                    click.echo("STOP: Data quality issues detected. Analysis cannot proceed.")
                    click.echo(" ".join(error_msg))
                    click.echo("HINT: Please fix the Langfuse data issues before running the analysis.")
                    click.echo("INFO: Check the error/warning messages above for specific line numbers and issues.")
                    # Clean up temp file
                    temp_path.unlink()
                    sys.exit(1)
                
                # Clean up temp file
                temp_path.unlink()
                
            except Exception as e:
                click.echo(f"❌ Error fetching from Langfuse: {e}", err=True)
                click.echo("💡 Make sure LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set")
                sys.exit(1)
        
        elif from_helicone:
            # Fetch from Helicone API
            try:
                click.echo(f"🔗 Fetching requests from Helicone (last {hours_back} hours, max {limit} requests)...")
                client = HeliconeClient()
                logs = client.fetch_requests(hours_back=hours_back, limit=limit)
                
                if not logs:
                    click.echo("⚠️  No requests found in Helicone for the specified time range.")
                    return ""
                
                click.echo(f"✅ Successfully fetched {len(logs)} requests from Helicone")
                
                # Save to temporary file and parse
                temp_path = save_logs_to_temp_file(logs)
                traces = parser.parse_file(temp_path) or {}
                
                # Check for parsing errors and stop if there are problems
                if parser.has_parsing_errors():
                    parsing_stats = parser.get_parsing_stats()
                    error_msg = []
                    if parsing_stats['skipped_records'] > 0:
                        error_msg.append(f"❌ {parsing_stats['skipped_records']} lines had JSON parsing errors")
                    if parsing_stats['warning_records'] > 0:
                        error_msg.append(f"⚠️ {parsing_stats['warning_records']} records had data quality issues (missing fields)")
                    
                    click.echo("STOP: Data quality issues detected. Analysis cannot proceed.")
                    click.echo(" ".join(error_msg))
                    click.echo("HINT: Please fix the Helicone data issues before running the analysis.")
                    click.echo("INFO: Check the error/warning messages above for specific line numbers and issues.")
                    # Clean up temp file
                    temp_path.unlink()
                    sys.exit(1)
                
                # Clean up temp file
                temp_path.unlink()
                
            except Exception as e:
                click.echo(f"❌ Error fetching from Helicone: {e}", err=True)
                click.echo("💡 Make sure HELICONE_API_KEY is set")
                sys.exit(1)
        
        elif logfile:
            # Read from specified file
            traces = parser.parse_file(logfile) or {}
            
            # Check for parsing errors and stop if there are problems
            if parser.has_parsing_errors():
                parsing_stats = parser.get_parsing_stats()
                error_msg = []
                if parsing_stats['skipped_records'] > 0:
                    error_msg.append(f"❌ {parsing_stats['skipped_records']} lines had JSON parsing errors")
                if parsing_stats['warning_records'] > 0:
                    error_msg.append(f"⚠️ {parsing_stats['warning_records']} records had data quality issues (missing fields)")
                
                click.echo("STOP: Data quality issues detected. Analysis cannot proceed.")
                click.echo(" ".join(error_msg))
                click.echo("HINT: Please fix the log file issues before running the analysis.")
                click.echo("INFO: Check the error/warning messages above for specific line numbers and issues.")
                sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Error reading input: {e}", err=True)
        sys.exit(1)
    
    if not traces:
        source = ("demo data" if demo else 
                 "standard input" if stdin else 
                 "pasted data" if paste else 
                 "Langfuse API" if from_langfuse else 
                 "Helicone API" if from_helicone else 
                 "log file")
        click.echo(f"⚠️  No traces found in {source}")
        return ""
    
    # Handle policy template enforcement
    policy_violations = []
    if policy_template or policy_file:
        try:
            policy_engine = None
            
            if policy_file:
                # Load custom policy file
                click.echo(f"📋 Loading custom policy from {policy_file}...")
                policy_engine = PolicyEngine(policy_file)
                
            elif policy_template:
                # Load built-in template(s)
                template_manager = get_template_manager()
                
                if policy_template.lower() == "all":
                    click.echo("📋 Loading all policy templates...")
                    policy_engine = template_manager.load_all_templates()
                else:
                    # Parse comma-separated template names
                    template_names = [name.strip() for name in policy_template.split(",")]
                    click.echo(f"📋 Loading policy templates: {', '.join(template_names)}...")
                    
                    if len(template_names) == 1:
                        policy_engine = template_manager.load_template(template_names[0])
                    else:
                        policy_engine = template_manager.load_multiple_templates(template_names)
            
            if policy_engine:
                # Convert traces to flat log entries for policy evaluation
                log_entries = []
                for trace_id, trace_data in traces.items():
                    if isinstance(trace_data, list):
                        log_entries.extend(trace_data)
                    else:
                        log_entries.append(trace_data)
                
                # Evaluate policies
                violations, skipped_rules = policy_engine.evaluate_logs(log_entries)
                policy_violations = violations
                
                if violations:
                    click.echo(f"⚠️  Found {len(violations)} policy violations!")
                    
                    # Show violations summary
                    violation_summary = {}
                    for violation in violations:
                        severity = violation.severity.value
                        if severity not in violation_summary:
                            violation_summary[severity] = 0
                        violation_summary[severity] += 1
                    
                    for severity, count in violation_summary.items():
                        emoji = "🚨" if severity == "critical" else "⚠️" if severity == "high" else "💡"
                        click.echo(f"  {emoji} {count} {severity} severity violations")
                
                if skipped_rules:
                    click.echo(f"ℹ️  Skipped {len(skipped_rules)} premium rules (upgrade for full policy coverage)")
                
                # For now, continue with normal analysis - policy violations will be included in reports
                click.echo("🔍 Running additional waste pattern analysis...")
                
            else:
                click.echo("❌ Could not load policy template(s)")
                
        except Exception as e:
            click.echo(f"❌ Error loading policy: {e}", err=True)
    
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
                min_calls=thresholds.get('fallback_storm', {}).get('min_calls', 3),  # type: ignore[call-arg]
                min_models=thresholds.get('fallback_storm', {}).get('min_models', 2),  # type: ignore[call-arg]
                max_trace_window_minutes=thresholds.get('fallback_storm', {}).get('max_trace_window_minutes', 3)  # type: ignore[call-arg]
            )),
            ('FallbackFailureDetector', FallbackFailureDetector(
                time_window_seconds=thresholds.get('fallback_failure', {}).get('time_window_seconds', 300)  # type: ignore[call-arg]
            )),
            ('OverkillModelDetector', OverkillModelDetector(
                max_prompt_tokens=thresholds.get('overkill_model', {}).get('max_prompt_tokens', 20),  # type: ignore[call-arg]
                max_prompt_chars=thresholds.get('overkill_model', {}).get('max_prompt_chars', 150)  # type: ignore[call-arg]
            ))
        ]
        
        # Process each detector
        for detector_name, detector in detector_configs:
            try:
                if hasattr(detector, 'detect'):
                    raw_detections = detector.detect(traces)
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
            max_retries=thresholds.get('retry_loop', {}).get('max_retries', 3),  # type: ignore[call-arg]
            time_window_minutes=thresholds.get('retry_loop', {}).get('time_window_minutes', 5),  # type: ignore[call-arg]
            max_retry_interval_minutes=thresholds.get('retry_loop', {}).get('max_retry_interval_minutes', 2)  # type: ignore[call-arg]
        )),
        ('FallbackStormDetector', FallbackStormDetector(
            min_calls=thresholds.get('fallback_storm', {}).get('min_calls', 3),  # type: ignore[call-arg]
            min_models=thresholds.get('fallback_storm', {}).get('min_models', 2),  # type: ignore[call-arg]
            max_trace_window_minutes=thresholds.get('fallback_storm', {}).get('max_trace_window_minutes', 3)  # type: ignore[call-arg]
        )),
        ('FallbackFailureDetector', FallbackFailureDetector(
            time_window_seconds=thresholds.get('fallback_failure', {}).get('time_window_seconds', 300)  # type: ignore[call-arg]
        )),
        ('OverkillModelDetector', OverkillModelDetector(
            max_prompt_tokens=thresholds.get('overkill_model', {}).get('max_prompt_tokens', 20),  # type: ignore[call-arg]
            max_prompt_chars=thresholds.get('overkill_model', {}).get('max_prompt_chars', 150)  # type: ignore[call-arg]
        ))
    ]
    
    all_active_detections = []
    
    # Process each detector in priority order
    for detector_name, detector in detector_configs:
        try:
            # Run detector
            if hasattr(detector, 'detect'):
                raw_detections = detector.detect(traces)
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


@click.command()
@click.option('--hours-back', default=24, help='Hours back to fetch traces (default: 24)')
@click.option('--limit', default=1000, help='Maximum number of traces to fetch (default: 1000)')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path (optional - if not provided, will analyze directly)')
@click.option('--analyze', is_flag=True, help='Analyze fetched traces immediately')
@click.option('--public-key', help='Langfuse public key (or use LANGFUSE_PUBLIC_KEY env var)')
@click.option('--secret-key', help='Langfuse secret key (or use LANGFUSE_SECRET_KEY env var)')
@click.option('--base-url', help='Langfuse base URL (or use LANGFUSE_HOST env var)')
def fetch_langfuse(hours_back: int, limit: int, output: Optional[Path], analyze: bool,
                   public_key: Optional[str], secret_key: Optional[str], base_url: Optional[str]):
    """🔗 Fetch traces from Langfuse API and optionally analyze them
    
    📦 Examples:
    
    crashlens fetch-langfuse                           # Fetch last 24h and analyze
    crashlens fetch-langfuse --hours-back 48          # Fetch last 48h  
    crashlens fetch-langfuse --output logs.jsonl      # Save to file
    crashlens fetch-langfuse --analyze --limit 500    # Fetch 500 traces and analyze
    """
    
    try:
        click.echo(f"🔗 Fetching traces from Langfuse (last {hours_back} hours, max {limit} traces)...")
        
        # Initialize client
        client = LangfuseClient(public_key, secret_key, base_url)
        
        # Fetch traces
        traces = client.fetch_traces(hours_back=hours_back, limit=limit)
        
        if not traces:
            click.echo("⚠️  No traces found in the specified time range.")
            return
        
        click.echo(f"✅ Successfully fetched {len(traces)} traces from Langfuse")
        
        # Handle output
        if output:
            # Save to file
            temp_path = save_logs_to_temp_file(traces)
            import shutil
            shutil.move(str(temp_path), str(output))
            click.echo(f"💾 Traces saved to {output}")
            
            # Analyze if requested
            if analyze:
                click.echo("🎯 Running analysis on fetched traces...")
                from crashlens.cli import analyze_traces_from_file
                analyze_traces_from_file(output)
        else:
            # Analyze directly (default behavior)
            click.echo("🎯 Running analysis on fetched traces...")
            temp_path = save_logs_to_temp_file(traces)
            from crashlens.cli import analyze_traces_from_file
            analyze_traces_from_file(temp_path)
            # Clean up temp file
            temp_path.unlink()
            
    except Exception as e:
        click.echo(f"❌ Error fetching from Langfuse: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option('--hours-back', default=24, help='Hours back to fetch requests (default: 24)')
@click.option('--limit', default=1000, help='Maximum number of requests to fetch (default: 1000)')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path (optional - if not provided, will analyze directly)')
@click.option('--analyze', is_flag=True, help='Analyze fetched requests immediately')
@click.option('--api-key', help='Helicone API key (or use HELICONE_API_KEY env var)')
@click.option('--base-url', help='Helicone base URL (defaults to production)')
def fetch_helicone(hours_back: int, limit: int, output: Optional[Path], analyze: bool,
                   api_key: Optional[str], base_url: Optional[str]):
    """🔗 Fetch requests from Helicone API and optionally analyze them
    
    📦 Examples:
    
    crashlens fetch-helicone                           # Fetch last 24h and analyze
    crashlens fetch-helicone --hours-back 48          # Fetch last 48h  
    crashlens fetch-helicone --output logs.jsonl      # Save to file
    crashlens fetch-helicone --analyze --limit 500    # Fetch 500 requests and analyze
    """
    
    try:
        click.echo(f"🔗 Fetching requests from Helicone (last {hours_back} hours, max {limit} requests)...")
        
        # Initialize client
        client = HeliconeClient(api_key, base_url)
        
        # Fetch requests
        requests = client.fetch_requests(hours_back=hours_back, limit=limit)
        
        if not requests:
            click.echo("⚠️  No requests found in the specified time range.")
            return
        
        click.echo(f"✅ Successfully fetched {len(requests)} requests from Helicone")
        
        # Handle output
        if output:
            # Save to file
            temp_path = save_logs_to_temp_file(requests)
            import shutil
            shutil.move(str(temp_path), str(output))
            click.echo(f"💾 Requests saved to {output}")
            
            # Analyze if requested
            if analyze:
                click.echo("🎯 Running analysis on fetched requests...")
                from crashlens.cli import analyze_traces_from_file
                analyze_traces_from_file(output)
        else:
            # Analyze directly (default behavior)
            click.echo("🎯 Running analysis on fetched requests...")
            temp_path = save_logs_to_temp_file(requests)
            from crashlens.cli import analyze_traces_from_file
            analyze_traces_from_file(temp_path)
            # Clean up temp file
            temp_path.unlink()
            
    except Exception as e:
        click.echo(f"❌ Error fetching from Helicone: {e}", err=True)
        sys.exit(1)


# Helper function to analyze traces from a file
def analyze_traces_from_file(logfile: Path):
    """Helper function to analyze traces from a file (reusable logic from scan command)"""
    
    # Load configurations
    pricing_config = load_pricing_config(None)
    suppression_config = load_suppression_config(None)
    
    # Initialize suppression engine
    suppression_engine = SuppressionEngine(suppression_config)
    
    # Initialize parser and load logs
    parser = LangfuseParser()
    traces = parser.parse_file(logfile) or {}
    
    if not traces:
        click.echo("⚠️  No valid traces found in fetched data")
        return
    
    # Load thresholds from pricing config
    thresholds = pricing_config.get('thresholds', {})
    
    # Run detectors in priority order with suppression (using same pattern as scan command)
    detector_configs = [
        ('RetryLoopDetector', RetryLoopDetector(
            max_retries=thresholds.get('retry_loop', {}).get('max_retries', 3),  # type: ignore[call-arg]
            time_window_minutes=thresholds.get('retry_loop', {}).get('time_window_minutes', 5),  # type: ignore[call-arg]
            max_retry_interval_minutes=thresholds.get('retry_loop', {}).get('max_retry_interval_minutes', 2)  # type: ignore[call-arg]
        )),
        ('FallbackStormDetector', FallbackStormDetector(
            min_calls=thresholds.get('fallback_storm', {}).get('min_calls', 3),  # type: ignore[call-arg]
            min_models=thresholds.get('fallback_storm', {}).get('min_models', 2),  # type: ignore[call-arg]
            max_trace_window_minutes=thresholds.get('fallback_storm', {}).get('max_trace_window_minutes', 3)  # type: ignore[call-arg]
        )),
        ('FallbackFailureDetector', FallbackFailureDetector(
            time_window_seconds=thresholds.get('fallback_failure', {}).get('time_window_seconds', 300)  # type: ignore[call-arg]
        )),
        ('OverkillModelDetector', OverkillModelDetector(
            max_prompt_tokens=thresholds.get('overkill_model', {}).get('max_prompt_tokens', 20),  # type: ignore[call-arg]
            max_prompt_chars=thresholds.get('overkill_model', {}).get('max_prompt_chars', 150)  # type: ignore[call-arg]
        ))
    ]
    
    all_active_detections = []
    
    # Process each detector
    for detector_name, detector in detector_configs:
        try:
            if hasattr(detector, 'detect'):
                raw_detections = detector.detect(traces)
            else:
                raw_detections = []
            
            # Process through suppression engine
            active_detections = suppression_engine.process_detections(detector_name, raw_detections)
            all_active_detections.extend(active_detections)
            
        except Exception as e:
            click.echo(f"⚠️  Warning: {detector_name} failed: {e}", err=True)
            continue
    
    # Generate report using SlackFormatter (default format)
    formatter = SlackFormatter()
    output = formatter.format(all_active_detections, traces, pricing_config.get('models', {}))
    
    click.echo("\n" + "="*80)
    click.echo("🎯 ANALYSIS RESULTS")
    click.echo("="*80)
    click.echo(output)


# Add new commands to CLI
cli.add_command(fetch_langfuse)
cli.add_command(fetch_helicone)


def _resolve_output_paths(out_report: Path, out_detailed: Path, out_dir: Optional[Path], 
                         detailed: bool, force: bool) -> Tuple[Path, Path]:
    """
    Resolve final output paths, handling --out-dir and file collision detection.
    
    Args:
        out_report: Original markdown report path
        out_detailed: Original detailed JSON path  
        out_dir: Optional output directory override
        detailed: Whether detailed report is requested
        force: Whether to overwrite existing files
        
    Returns:
        Tuple of (final_markdown_path, final_detailed_path)
    """
    from datetime import datetime
    
    # Handle --out-dir override
    if out_dir:
        # Use simple filenames when --out-dir is specified
        final_out_report = out_dir / "violations-summary.md"
        final_out_detailed = out_dir / "violations-detailed.json"
    else:
        final_out_report = out_report
        final_out_detailed = out_detailed
    
    # Handle file collision detection for markdown report
    if final_out_report.exists() and not force:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = final_out_report.stem
        suffix = final_out_report.suffix
        final_out_report = final_out_report.parent / f"{stem}-{timestamp}{suffix}"
    
    # Handle file collision detection for detailed report (if needed)
    if detailed and final_out_detailed.exists() and not force:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = final_out_detailed.stem
        suffix = final_out_detailed.suffix
        final_out_detailed = final_out_detailed.parent / f"{stem}-{timestamp}{suffix}"
    
    return final_out_report, final_out_detailed


@click.command()
@click.argument('logfile', type=click.Path(path_type=Path))
@click.option('--policy-template', help='Use built-in policy template(s) (comma-separated or "all")')
@click.option('--policy-file', type=click.Path(path_type=Path), help='Use custom policy file')
@click.option('--fail-on-violations', is_flag=True, help='Exit with error code if violations found')
@click.option('--severity-threshold', 
              type=click.Choice(['low', 'medium', 'high', 'critical'], case_sensitive=False),
              default='medium', help='Minimum severity level to report')
@click.option('--out-report', type=click.Path(path_type=Path), default='policy-violations/reports/violations-summary.md',
              help='Output path for markdown report')
@click.option('--detailed', is_flag=True, help='Generate detailed JSON report in addition to markdown')
@click.option('--out-detailed', type=click.Path(path_type=Path), default='policy-violations/traces/violations-detailed.json',
              help='Output path for detailed JSON report')
@click.option('--out-dir', type=click.Path(path_type=Path), 
              help='Output directory for both reports (overrides individual paths)')
@click.option('--force', is_flag=True, help='Overwrite existing files without timestamp suffix')
@click.option('--quiet', is_flag=True, help='Print only summary line to stdout')
@click.option('--no-content', is_flag=True, help='Exclude prompt/response content from reports')
@click.option('--strip-pii', is_flag=True, help='Remove personally identifiable information from reports')
def policy_check(logfile: Path, policy_template: Optional[str] = None, policy_file: Optional[Path] = None, 
                 fail_on_violations: bool = False, severity_threshold: str = 'medium',
                 out_report: Path = Path('policy-violations/reports/violations-summary.md'), detailed: bool = False, 
                 out_detailed: Path = Path('policy-violations/traces/violations-detailed.json'),
                 out_dir: Optional[Path] = None, force: bool = False,
                 quiet: bool = False, no_content: bool = False, strip_pii: bool = False):
    """🔍 Check logs against policy rules and generate reports
    
    📦 Examples:
    
    crashlens policy-check logs.jsonl --policy-template retry-loop-prevention
    crashlens policy-check logs.jsonl --policy-template all --fail-on-violations --detailed
    crashlens policy-check logs.jsonl --policy-file my-policy.yaml --severity-threshold high
    crashlens policy-check logs.jsonl --policy-file my-policy.yaml --detailed --out-report policy-violations/reports/custom-summary.md
    
    📁 Output Structure:
    - policy-violations/reports/violations-summary.md (default summary)
    - policy-violations/traces/violations-detailed.json (detailed analysis with --detailed)
    
    🗂️ New Directory Options:
    - --out-dir crashlens-reports/  (places both files in custom directory)
    - --force (overwrite existing files instead of adding timestamp)
    """
    
    # Validate inputs
    if not policy_template and not policy_file:
        click.echo("❌ Error: Must specify either --policy-template or --policy-file")
        sys.exit(1)
    
    if not logfile.exists():
        click.echo(f"❌ Error: File not found: {logfile}")
        sys.exit(1)
    
    try:
        # Load policy engine
        policy_engine = None
        
        if policy_file:
            if not quiet:
                click.echo(f"📋 Loading custom policy from {policy_file}...")
            policy_engine = PolicyEngine(policy_file)
            
        elif policy_template:
            template_manager = get_template_manager()
            
            if policy_template.lower() == "all":
                if not quiet:
                    click.echo("📋 Loading all policy templates...")
                policy_engine = template_manager.load_all_templates()
            else:
                template_names = [name.strip() for name in policy_template.split(",")]
                if not quiet:
                    click.echo(f"📋 Loading policy templates: {', '.join(template_names)}...")
                
                if len(template_names) == 1:
                    policy_engine = template_manager.load_template(template_names[0])
                else:
                    policy_engine = template_manager.load_multiple_templates(template_names)
        
        if not policy_engine:
            click.echo("❌ Could not load policy configuration")
            sys.exit(1)
        
        # Parse logs
        parser = LangfuseParser()
        traces = parser.parse_file(logfile) or {}
        
        if not traces:
            click.echo("⚠️  No traces found in log file")
            return
        
        # Convert traces to log entries
        log_entries = []
        for trace_id, trace_data in traces.items():
            if isinstance(trace_data, list):
                log_entries.extend(trace_data)
            else:
                log_entries.append(trace_data)
        
        if not quiet:
            click.echo(f"🔍 Checking {len(log_entries)} log entries against policy rules...")
        
        # Evaluate policies
        violations, skipped_rules = policy_engine.evaluate_logs(log_entries)
        
        # Filter by severity threshold
        severity_order = ['low', 'medium', 'high', 'critical']
        min_severity_index = severity_order.index(severity_threshold.lower())
        
        filtered_violations = [
            v for v in violations 
            if severity_order.index(v.severity.value) >= min_severity_index
        ]
        
        # Handle output directory and file collision detection
        final_out_report, final_out_detailed = _resolve_output_paths(
            out_report, out_detailed, out_dir, detailed, force
        )
        
        # Generate markdown report
        # Ensure output directory exists
        final_out_report.parent.mkdir(parents=True, exist_ok=True)
        
        markdown_writer = PolicyReportMarkdown(
            violations=filtered_violations,
            log_entries=log_entries,
            strip_pii=strip_pii,
            no_content=no_content
        )
        markdown_writer.generate_report(final_out_report)
        
        # Generate detailed JSON report if requested
        if detailed:
            # Ensure output directory exists
            final_out_detailed.parent.mkdir(parents=True, exist_ok=True)
            
            json_writer = PolicyReportJSON(
                violations=filtered_violations,
                log_entries=log_entries,
                strip_pii=strip_pii,
                no_content=no_content
            )
            json_writer.generate_report(final_out_detailed)
        
        # Output results to stdout
        if not quiet:
            if not filtered_violations:
                click.echo("✅ No policy violations found! Your usage patterns look compliant.")
                if skipped_rules:
                    click.echo(f"ℹ️  Note: Skipped {len(skipped_rules)} premium rules")
            else:
                # Show brief summary
                by_severity = {}
                for violation in filtered_violations:
                    severity = violation.severity.value
                    by_severity[severity] = by_severity.get(severity, 0) + 1
                
                severity_summary = []
                for severity in ['critical', 'high', 'medium', 'low']:
                    if severity in by_severity:
                        severity_summary.append(f"{severity}: {by_severity[severity]}")
                
                click.echo(f"⚠️  Found {len(filtered_violations)} policy violations ({', '.join(severity_summary)})")
                if skipped_rules:
                    click.echo(f"ℹ️  Skipped {len(skipped_rules)} premium rules")
        
        # Print output file locations
        if quiet:
            click.echo(f"Saved report to {final_out_report}")
            if detailed:
                click.echo(f"Saved detailed JSON to {final_out_detailed}")
        else:
            click.echo(f"📄 Saved markdown report to {final_out_report}")
            if detailed:
                click.echo(f"📊 Saved detailed JSON to {final_out_detailed}")
        
        # Exit with appropriate code
        if fail_on_violations and filtered_violations:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Error during policy check: {e}", err=True)
        sys.exit(1)


@click.command()
def list_policy_templates():
    """📜 List all available built-in policy templates"""
    template_manager = get_template_manager()
    template_manager.list_templates()


# =============================================================================
# Init Command Helper Functions
# =============================================================================

def _load_config_schema() -> Dict[str, Any]:
    """Load the JSON schema for config validation."""
    schema_path = Path(__file__).parent / "config" / "config_schema.json"
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback minimal schema if file not found
        return {
            "type": "object",
            "required": ["policy_template", "severity_threshold", "fail_on_violations", "logs_source"]
        }


def _validate_config(config_data: Dict[str, Any]) -> List[str]:
    """Validate configuration against JSON schema.
    
    Args:
        config_data: Configuration dictionary to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    try:
        schema = _load_config_schema()
        
        if HAS_JSONSCHEMA:
            # Full validation with jsonschema
            jsonschema.validate(config_data, schema)
        else:
            # Basic validation without jsonschema
            required_keys = ['policy_template', 'severity_threshold', 'fail_on_violations', 'logs_source']
            for key in required_keys:
                if key not in config_data:
                    errors.append(f"Missing required field: {key}")
            
            # Validate enum values
            if 'severity_threshold' in config_data:
                valid_severities = ['low', 'medium', 'high', 'critical']
                if config_data['severity_threshold'] not in valid_severities:
                    errors.append(f"Invalid severity_threshold: {config_data['severity_threshold']}")
                    
            if 'logs_source' in config_data:
                valid_sources = ['local', 'langfuse', 'helicone', 'other']
                if config_data['logs_source'] not in valid_sources:
                    errors.append(f"Invalid logs_source: {config_data['logs_source']}")
    
    except Exception as e:
        if HAS_JSONSCHEMA and "ValidationError" in str(type(e)):
            errors.append(f"Schema validation error: {str(e)}")
        else:
            errors.append(f"Validation error: {str(e)}")
    
    return errors


def _check_config_version_compatibility(config_data: Dict[str, Any]) -> Optional[str]:
    """Check if config version is compatible with current CLI version.
    
    Args:
        config_data: Configuration dictionary
        
    Returns:
        Warning message if incompatible, None if compatible
    """
    cli_version = _get_current_cli_version()
    config_version = config_data.get('version', '1.0.0')
    
    # Simple version comparison (major.minor)
    try:
        cli_parts = cli_version.split('.')[:2]
        config_parts = config_version.split('.')[:2]
        
        cli_major, cli_minor = int(cli_parts[0]), int(cli_parts[1])
        config_major, config_minor = int(config_parts[0]), int(config_parts[1])
        
        # Warn if CLI version is older than config
        if (cli_major < config_major) or (cli_major == config_major and cli_minor < config_minor):
            return f"⚠️  Config was created with newer version ({config_version}). Current CLI: {cli_version}. Config may be incompatible."
    
    except (ValueError, IndexError):
        # If version parsing fails, skip check
        pass
    
    return None


def _get_env_or_default(env_var: str, default: Any, convert_type: type = str) -> Any:
    """Get environment variable with type conversion and default fallback.
    
    Args:
        env_var: Environment variable name
        default: Default value if env var not set
        convert_type: Type to convert to (str, bool, int, etc.)
        
    Returns:
        Environment variable value or default
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    if convert_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    
    try:
        return convert_type(value)
    except (ValueError, TypeError):
        return default


def _validate_template_selection(template_input: str, available_templates: List[str]) -> List[str]:
    """Validate and parse template selection.
    
    Args:
        template_input: Comma-separated template names or 'all'
        available_templates: List of available template names
        
    Returns:
        List of validation errors (empty if valid)
    """
    if template_input.strip().lower() == "all":
        return []
    
    templates = [t.strip() for t in template_input.split(",")]
    available_set = set(available_templates[:-1])  # Exclude 'all' from validation
    invalid_templates = [t for t in templates if t not in available_set]
    
    if invalid_templates:
        return [f"Invalid templates: {', '.join(invalid_templates)}"]
    
    return []


def _print_workflow_yaml(policy_templates: str, severity: str, fail_on_violations: bool, 
                        python_version: str = "3.11") -> None:
    """Print the generated GitHub Actions workflow YAML to stdout.
    
    Args:
        policy_templates: Policy templates to use
        severity: Severity threshold
        fail_on_violations: Whether to fail on violations
        python_version: Python version for workflow
    """
    # Build command flags
    cmd_parts = ["crashlens policy-check logs.jsonl"]
    cmd_parts.append(f"--policy-template {policy_templates}")
    cmd_parts.append(f"--severity-threshold {severity}")
    
    if fail_on_violations:
        cmd_parts.append("--fail-on-violations")
    
    command = " ".join(cmd_parts)
    
    # Workflow content
    workflow_content = f"""name: Crashlens Policy Check

# Run on push and pull requests to main branch
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  
  # Allow manual workflow dispatch for testing
  workflow_dispatch:
    inputs:
      policy_template:
        description: 'Policy templates (comma-separated or "all")'
        required: false
        default: '{policy_templates}'
      severity_threshold:
        description: 'Severity threshold'
        required: false
        default: '{severity}'
        type: choice
        options: ['low', 'medium', 'high', 'critical']
      fail_on_violations:
        description: 'Fail on violations'
        required: false
        default: '{str(fail_on_violations).lower()}'
        type: boolean

# Minimal permissions for security
permissions:
  contents: read
  pull-requests: write

jobs:
  crashlens-policy-check:
    name: Run Crashlens Policy Analysis
    runs-on: ubuntu-latest
    
    steps:
    # Checkout repository code
    - name: Checkout code
      uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608  # v4.1.0
      
    # Set up Python environment  
    - name: Set up Python {python_version}
      uses: actions/setup-python@65d7f2d534ac1bc67fcd62888c5f4f3d2cb2b236  # v4.7.1
      with:
        python-version: '{python_version}'
        
    # Cache pip dependencies
    - name: Cache pip dependencies
      uses: actions/cache@88522ab9f39a2ea568f7027eddc7d8d8bc9d59c8  # v3.3.1
      with:
        path: ~/.cache/pip
        key: ${{{{ runner.os }}}}-pip-${{{{ hashFiles('**/requirements.txt', '**/pyproject.toml') }}}}
        restore-keys: |
          ${{{{ runner.os }}}}-pip-
        
    # Install Crashlens from PyPI
    - name: Install Crashlens
      run: |
        python -m pip install --upgrade pip
        pip install crashlens==1.0.0  # Pinned version for security
        
    # Verify installation
    - name: Verify Crashlens installation
      run: |
        crashlens --version
        crashlens list-policy-templates
        
    # Run policy check on log files
    - name: Run Crashlens policy check
      run: |
        # Check for config file first
        if [[ -f ".crashlens/config.yaml" ]]; then
          echo "📁 Using .crashlens/config.yaml configuration"
          crashlens scan . --config .crashlens/config.yaml
        elif find . -name "*.jsonl" -type f | grep -q .; then
          echo "📄 Found .jsonl files, running policy check..."
          # Use workflow inputs if available, fallback to defaults
          POLICY_TEMPLATE="${{{{ github.event.inputs.policy_template || '{policy_templates}' }}}}"
          SEVERITY="${{{{ github.event.inputs.severity_threshold || '{severity}' }}}}"
          FAIL_ON="${{{{ github.event.inputs.fail_on_violations || '{str(fail_on_violations).lower()}' }}}}"
          
          FLAGS=""
          if [[ "$FAIL_ON" == "true" ]]; then
            FLAGS="--fail-on-violations"
          fi
          
          find . -name "*.jsonl" -type f -exec crashlens policy-check {{}} --policy-template "$POLICY_TEMPLATE" --severity-threshold "$SEVERITY" $FLAGS \\;
        else
          echo "❌ No .jsonl log files or .crashlens/config.yaml found."
          echo "💡 Add your log files (.jsonl) or run 'crashlens init' to create configuration."
          exit 1
        fi
        
    # Upload results as artifacts (excluding sensitive logs)
    - name: Upload policy results
      if: always()
      uses: actions/upload-artifact@a8a3f3ad30e3422c9c7b888a15615d19a852ae32  # v3.1.3
      with:
        name: crashlens-policy-results-${{{{ github.run_number }}}}
        path: |
          crashlens-*.json
          crashlens-*.md
        retention-days: 30
        
    # Add policy check summary to PR
    - name: Add policy summary to PR
      if: github.event_name == 'pull_request'
      run: |
        echo "## 🔍 Crashlens Policy Check Results" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "- **Repository**: ${{{{ github.repository }}}}" >> $GITHUB_STEP_SUMMARY
        echo "- **Branch**: ${{{{ github.head_ref }}}}" >> $GITHUB_STEP_SUMMARY
        echo "- **Commit**: ${{{{ github.sha }}}}" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "**Policy Templates**: ${{{{ github.event.inputs.policy_template || '{policy_templates}' }}}}" >> $GITHUB_STEP_SUMMARY
        echo "**Severity Threshold**: ${{{{ github.event.inputs.severity_threshold || '{severity}' }}}}" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "Check the logs above for detailed violation information." >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "🔗 [Crashlens Documentation](https://github.com/Crashlens/crashlens)" >> $GITHUB_STEP_SUMMARY
"""
    
    click.echo(workflow_content)


@click.command()
@click.option('--non-interactive', is_flag=True, 
              help='Run in non-interactive mode using environment variables')
@click.option('--dry-run-workflow', is_flag=True,
              help='Print workflow YAML to stdout instead of writing to disk')
def init(non_interactive: bool, dry_run_workflow: bool):
    """🚀 Setup wizard to initialize Crashlens configuration"""
    
    # Define available options
    AVAILABLE_TEMPLATES = [
        "retry-loop-prevention",
        "model-overkill-detection", 
        "chain-recursion-prevention",
        "fallback-storm-detection",
        "budget-protection",
        "rate-limit-management",
        "prompt-optimization",
        "error-handling-efficiency",
        "context-window-optimization",
        "batch-processing-efficiency",
        "all"
    ]
    
    SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
    LOGS_SOURCES = ["local", "langfuse", "helicone", "other"]
    
    try:
        # Handle non-interactive mode
        if non_interactive:
            click.echo("🤖 Running in non-interactive mode...")
            click.echo()
            
            # Get all values from environment variables
            policy_templates = _get_env_or_default('CRASHLENS_TEMPLATES', 'all')
            severity = _get_env_or_default('CRASHLENS_SEVERITY', 'high')
            fail_on_violations = _get_env_or_default('CRASHLENS_FAIL_ON_VIOLATIONS', True, bool)
            logs_source = _get_env_or_default('CRASHLENS_LOGS_SOURCE', 'local')
            create_workflow = _get_env_or_default('CRASHLENS_CREATE_WORKFLOW', False, bool)
            
            # Validate inputs
            validation_errors = _validate_template_selection(policy_templates, AVAILABLE_TEMPLATES)
            if severity not in SEVERITY_LEVELS:
                validation_errors.append(f"Invalid CRASHLENS_SEVERITY: {severity}")
            if logs_source not in LOGS_SOURCES:
                validation_errors.append(f"Invalid CRASHLENS_LOGS_SOURCE: {logs_source}")
            
            if validation_errors:
                for error in validation_errors:
                    click.echo(f"❌ {error}")
                click.echo(f"❌ Non-interactive mode failed due to invalid environment variables.")
                sys.exit(1)
                
            click.echo(f"📋 Policy templates: {policy_templates}")
            click.echo(f"📊 Severity threshold: {severity}")  
            click.echo(f"🚨 Fail on violations: {fail_on_violations}")
            click.echo(f"📁 Logs source: {logs_source}")
            click.echo(f"⚙️  Create workflow: {create_workflow}")
            click.echo()
            
        else:
            # Interactive mode
            click.echo("🚀 Welcome to Crashlens Setup Wizard")
            click.echo()
            
            # 1. Policy templates selection
            while True:
                policy_input = click.prompt(
                    "Enter default policy templates (comma separated)", 
                    default="all",
                    show_default=True
                )
                
                validation_errors = _validate_template_selection(policy_input, AVAILABLE_TEMPLATES)
                if not validation_errors:
                    policy_templates = policy_input
                    break
                
                for error in validation_errors:
                    click.echo(f"❌ {error}")
                click.echo(f"Available templates: {', '.join(AVAILABLE_TEMPLATES)}")
                continue
            
            # 2. Severity threshold
            while True:
                severity = click.prompt(
                    f"Severity threshold ({'/'.join(SEVERITY_LEVELS)})",
                    default="high",
                    show_default=True
                ).lower()
                
                if severity in SEVERITY_LEVELS:
                    break
                
                click.echo(f"❌ Invalid severity level. Choose from: {', '.join(SEVERITY_LEVELS)}")
            
            # 3. Fail on violations
            fail_on_violations = click.confirm(
                "Fail CI/CD on violations?",
                default=True
            )
            
            # 4. Logs source
            while True:
                logs_source = click.prompt(
                    f"Logs source ({'/'.join(LOGS_SOURCES)})",
                    default="local",
                    show_default=True
                ).lower()
                
                if logs_source in LOGS_SOURCES:
                    break
                    
                click.echo(f"❌ Invalid logs source. Choose from: {', '.join(LOGS_SOURCES)}")
            
            # 5. Create GitHub Actions workflow
            create_workflow = click.confirm(
                "Create GitHub Actions workflow?",
                default=False
            )
        
        # Handle dry run mode for workflow
        if dry_run_workflow:
            click.echo("🔍 Dry run mode - printing workflow YAML:")
            click.echo("=" * 60)
            _print_workflow_yaml(policy_templates, severity, fail_on_violations)
            click.echo("=" * 60)
            click.echo("✅ Dry run complete - no files written")
            return
        
        # 6. Save configuration
        config_dir = Path(".crashlens")
        config_file = config_dir / "config.yaml"
        
        # Check if config exists
        if config_file.exists() and not non_interactive:
            if not click.confirm(f"Configuration file {config_file} already exists. Overwrite?"):
                click.echo("❌ Setup cancelled.")
                return
        
        # Create config directory
        config_dir.mkdir(exist_ok=True)
        
        # Prepare configuration with validation
        cli_version = _get_current_cli_version()
        config_data = {
            'policy_template': policy_templates,
            'severity_threshold': severity,
            'fail_on_violations': fail_on_violations,
            'logs_source': logs_source,
            'created_at': datetime.now().isoformat(),
            'version': cli_version,
            'output_directory': '.'
        }
        
        # Validate configuration before saving
        validation_errors = _validate_config(config_data)
        if validation_errors:
            click.echo("❌ Configuration validation failed:")
            for error in validation_errors:
                click.echo(f"   • {error}")
            sys.exit(1)
        
        # Check for version compatibility if updating existing config
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f)
                
                version_warning = _check_config_version_compatibility(existing_config)
                if version_warning:
                    click.echo(version_warning)
            except Exception:
                pass  # Ignore errors reading existing config
        
        # Atomic write of configuration
        temp_config_file = config_file.with_suffix('.tmp')
        try:
            with open(temp_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            # Atomic move
            temp_config_file.replace(config_file)
            click.echo(f"✅ Configuration saved at {config_file}")
        except Exception as e:
            if temp_config_file.exists():
                temp_config_file.unlink()  # Cleanup temp file
            raise e
        
        # 7. GitHub Actions workflow creation
        if create_workflow:
            _create_github_workflow(policy_templates, severity, fail_on_violations)
        
        # Success message and next steps
        click.echo()
        click.echo("🎉 Crashlens setup complete!")
        click.echo("👉 Next steps:")
        click.echo("   1. Add your log files (.jsonl format)")
        click.echo("   2. Run: crashlens scan logs.jsonl")
        click.echo("   3. Or use policy-check: crashlens policy-check logs.jsonl")
        
        if config_file.exists():
            click.echo(f"   4. View config: cat {config_file}")
        
    except KeyboardInterrupt:
        click.echo("\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error during setup: {e}", err=True)
        sys.exit(1)


def _create_github_workflow(policy_templates: str, severity: str, fail_on_violations: bool):
    """Create GitHub Actions workflow file"""
    
    workflow_dir = Path(".github/workflows")
    workflow_file = workflow_dir / "crashlens.yml"
    
    # Check if workflow exists
    if workflow_file.exists():
        if not click.confirm(f"Workflow file {workflow_file} already exists. Overwrite?"):
            click.echo("⏭️  Skipped GitHub Actions workflow creation.")
            return
    
    # Create workflow directory
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command flags
    cmd_parts = ["crashlens policy-check logs.jsonl"]
    cmd_parts.append(f"--policy-template {policy_templates}")
    cmd_parts.append(f"--severity-threshold {severity}")
    
    if fail_on_violations:
        cmd_parts.append("--fail-on-violations")
    
    command = " ".join(cmd_parts)
    
    # Workflow content
    workflow_content = f"""name: Crashlens Policy Check

# Run on push and pull requests to main branch
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  
  # Allow manual workflow dispatch for testing
  workflow_dispatch:

jobs:
  crashlens-policy-check:
    name: Run Crashlens Policy Analysis
    runs-on: ubuntu-latest
    
    steps:
    # Checkout repository code
    - name: Checkout code
      uses: actions/checkout@v4
      
    # Set up Python environment
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    # Install Crashlens from PyPI
    - name: Install Crashlens
      run: |
        python -m pip install --upgrade pip
        pip install crashlens
        
    # Run policy check on log files
    - name: Run Crashlens policy check
      run: |
        # Find and check .jsonl files
        if find . -name "*.jsonl" -type f | grep -q .; then
          echo "Found .jsonl files, running policy check..."
          find . -name "*.jsonl" -type f -exec {command.replace('logs.jsonl', '{{}}')} \\;
        else
          echo "No .jsonl log files found. Add your log files and re-run."
          echo "Expected: .jsonl files containing your API logs"
        fi
        
    # Upload results as artifacts
    - name: Upload policy results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: crashlens-policy-results
        path: |
          *.jsonl
          crashlens-*.json
          crashlens-*.md
        retention-days: 30
"""
    
    # Save workflow file
    with open(workflow_file, 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    
    click.echo(f"✅ GitHub Actions workflow created at {workflow_file}")


# ============================================================================
# SIMULATE COMMAND - Generate Langfuse-style .jsonl traces for policy testing
# ============================================================================

@click.command()
@click.option('--output', required=True, type=click.Path(path_type=Path),
              help='Path to write .jsonl file')
@click.option('--count', default=100, type=int,
              help='Number of traces to generate (default: 100)')
@click.option('--scenario', 
              type=click.Choice(['normal', 'retry-loop', 'model-overkill', 'slow', 'mixed-errors'], 
                               case_sensitive=False),
              default='normal',
              help='Scenario type to generate (default: normal)')
@click.option('--models', default='gpt-4o,gpt-3.5-turbo,gpt-4-turbo,gpt-4',
              help='Comma-separated list of allowed model names (default: common OpenAI models)')
@click.option('--error-rate', default=0.2, type=float,
              help='Probability (0-1) of generating error traces (default: 0.2)')
@click.option('--seed', type=int,
              help='Random seed for deterministic output')
@click.option('--force', is_flag=True,
              help='Overwrite existing output file without prompting')
@click.option('--open', 'run_policy_check', is_flag=True,
              help='After generation, run crashlens policy-check on the generated file')
def simulate(output: Path, count: int, scenario: str, models: str, 
           error_rate: float, seed: Optional[int], force: bool, run_policy_check: bool):
    """
    Generate realistic Langfuse-style .jsonl traces for testing Crashlens policies.
    
    Creates synthetic trace data with configurable scenarios to test policy detection
    without requiring production logs.
    
    Examples:
        crashlens simulate --output test.jsonl --count 500 --scenario retry-loop
        
        crashlens simulate --output traces.jsonl --scenario mixed-errors --error-rate 0.3 --open
        
        crashlens simulate --output deterministic.jsonl --seed 42 --force
    """
    # Validate faker dependency
    if not HAS_FAKER:
        click.echo("❌ Error: faker package not installed. Run: pip install faker", err=True)
        sys.exit(1)
    
    # Validate parameters
    if count <= 0:
        click.echo("❌ Error: count must be greater than 0", err=True)
        sys.exit(1)
    
    if not (0.0 <= error_rate <= 1.0):
        click.echo("❌ Error: error-rate must be between 0.0 and 1.0", err=True)
        sys.exit(1)
    
    # Parse and validate models
    model_list = _parse_models(models)
    if not model_list:
        click.echo("❌ Error: no valid models specified", err=True)
        sys.exit(1)
    
    # Check if output file exists
    if output.exists() and not force:
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            click.echo("Operation cancelled.")
            sys.exit(1)
    
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)
        if HAS_FAKER:
            fake = Faker()
            Faker.seed(seed)
        click.echo(f"🎲 Using random seed: {seed}")
    else:
        fake = Faker() if HAS_FAKER else None
    
    click.echo(f"🏗️  Generating {count} traces with scenario: {scenario}")
    click.echo(f"📝 Models: {', '.join(model_list)}")
    click.echo(f"💥 Error rate: {error_rate:.1%}")
    
    try:
        # Generate traces
        traces = _generate_traces(count, scenario, model_list, error_rate, fake)
        
        # Write to JSONL file
        _write_jsonl_traces(output, traces)
        
        click.echo(f"✅ Generated {len(traces)} traces to {output}")
        
        # Run policy check if requested
        if run_policy_check:
            click.echo("🔍 Running policy check on generated traces...")
            _run_policy_check_on_file(output)
            
    except Exception as e:
        click.echo(f"❌ Error generating traces: {str(e)}", err=True)
        sys.exit(1)


def _parse_models(models_str: str) -> List[str]:
    """Parse comma-separated model list and return valid models."""
    if not models_str.strip():
        # Default common OpenAI models
        return ['gpt-4o', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4']
    
    models = [model.strip() for model in models_str.split(',') if model.strip()]
    if not models:
        return ['gpt-4o', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4']
    
    return models


def _generate_traces(count: int, scenario: str, models: List[str], 
                    error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate traces based on scenario and parameters."""
    traces = []
    
    if scenario == 'retry-loop':
        traces = _generate_retry_loop_traces(count, models, error_rate, fake)
    elif scenario == 'model-overkill':
        traces = _generate_model_overkill_traces(count, models, error_rate, fake)
    elif scenario == 'slow':
        traces = _generate_slow_traces(count, models, error_rate, fake)
    elif scenario == 'mixed-errors':
        traces = _generate_mixed_error_traces(count, models, error_rate, fake)
    else:  # normal
        traces = _generate_normal_traces(count, models, error_rate, fake)
    
    return traces


def _generate_normal_traces(count: int, models: List[str], 
                          error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate normal, realistic traces."""
    traces = []
    base_time = datetime.now()
    
    for i in range(count):
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        model = random.choice(models)
        
        # Generate realistic prompt/response
        prompt = fake.sentence(nb_words=random.randint(5, 30)) if fake else f"User prompt {i+1}"
        
        # Determine if this should be an error trace
        is_error = random.random() < error_rate
        
        if is_error:
            # Error trace
            output = ""
            status = "error" if random.random() < 0.5 else "timeout"
            completion_tokens = 0
            duration_ms = random.randint(100, 2000)
        else:
            # Successful trace
            output = fake.text(max_nb_chars=random.randint(50, 500)) if fake else f"Response for trace {i+1}"
            status = "success"
            completion_tokens = random.randint(10, 300)
            duration_ms = random.randint(200, 3000)
        
        prompt_tokens = random.randint(10, 200)
        
        # Calculate timing
        start_time = base_time + timedelta(seconds=i * random.randint(1, 10))
        end_time = start_time + timedelta(milliseconds=duration_ms)
        
        trace = {
            "traceId": trace_id,
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "input": {
                "model": model,
                "prompt": prompt
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "cost": _calculate_cost(model, prompt_tokens, completion_tokens),
            "output": output,
            "status": status
        }
        
        traces.append(trace)
        base_time = end_time
    
    return traces


def _generate_retry_loop_traces(count: int, models: List[str], 
                               error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate traces with retry loop patterns."""
    traces = []
    base_time = datetime.now()
    
    # Generate groups of retry traces
    while len(traces) < count:
        trace_id = f"retry_{uuid.uuid4().hex[:8]}"
        model = random.choice(models)
        
        # Same prompt for all retries
        prompt = fake.sentence(nb_words=random.randint(8, 25)) if fake else f"Retry prompt for {trace_id}"
        
        # Generate 3-6 retry attempts
        retry_count = random.randint(3, 6)
        
        for retry_num in range(min(retry_count, count - len(traces))):
            is_last = retry_num == retry_count - 1
            is_error = not is_last or random.random() < error_rate
            
            if is_error and not is_last:
                # Failed retry
                output = ""
                status = "error"
                completion_tokens = 0
                duration_ms = random.randint(100, 1000)
            else:
                # Success or final attempt
                output = fake.text(max_nb_chars=random.randint(100, 400)) if fake else f"Success response"
                status = "success" if not is_error else "error"
                completion_tokens = random.randint(20, 200) if status == "success" else 0
                duration_ms = random.randint(500, 2000)
            
            prompt_tokens = random.randint(10, 150)
            
            start_time = base_time + timedelta(seconds=retry_num * random.randint(1, 3))
            end_time = start_time + timedelta(milliseconds=duration_ms)
            
            trace = {
                "traceId": trace_id,  # Same trace ID for all retries
                "startTime": start_time.isoformat() + "Z",
                "endTime": end_time.isoformat() + "Z",
                "input": {
                    "model": model,
                    "prompt": prompt  # Same prompt
                },
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                },
                "cost": _calculate_cost(model, prompt_tokens, completion_tokens),
                "output": output,
                "status": status,
                "metadata": {
                    "retry_attempt": retry_num + 1
                }
            }
            
            traces.append(trace)
            base_time = end_time + timedelta(seconds=1)
    
    return traces[:count]


def _generate_model_overkill_traces(count: int, models: List[str], 
                                  error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate traces showing expensive models for simple tasks."""
    traces = []
    base_time = datetime.now()
    
    # Expensive models for overkill detection
    expensive_models = [m for m in models if 'gpt-4' in m]
    if not expensive_models:
        expensive_models = models[:1]  # Use first model as expensive
    
    simple_prompts = [
        "What is 2+2?",
        "What is the capital of France?", 
        "How do you spell 'hello'?",
        "What color is the sky?",
        "Is Python a programming language?",
    ] if not fake else None
    
    for i in range(count):
        trace_id = f"overkill_{uuid.uuid4().hex[:8]}"
        
        # 70% chance to use expensive model for simple task
        if random.random() < 0.7:
            model = random.choice(expensive_models)
            # Simple prompt
            if simple_prompts:
                prompt = random.choice(simple_prompts)
            else:
                prompt = fake.sentence(nb_words=random.randint(3, 8)) if fake else f"Simple question {i+1}"
            prompt_tokens = random.randint(5, 15)  # Very few tokens
        else:
            model = random.choice(models)
            prompt = fake.sentence(nb_words=random.randint(10, 25)) if fake else f"Complex prompt {i+1}"
            prompt_tokens = random.randint(20, 200)
        
        is_error = random.random() < error_rate
        
        if is_error:
            output = ""
            status = "error"
            completion_tokens = 0
            duration_ms = random.randint(100, 1500)
        else:
            output = fake.sentence(nb_words=random.randint(3, 20)) if fake else f"Simple answer {i+1}"
            status = "success"
            completion_tokens = random.randint(5, 50)  # Short responses for simple questions
            duration_ms = random.randint(200, 1200)
        
        start_time = base_time + timedelta(seconds=i * random.randint(1, 5))
        end_time = start_time + timedelta(milliseconds=duration_ms)
        
        trace = {
            "traceId": trace_id,
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "input": {
                "model": model,
                "prompt": prompt
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "cost": _calculate_cost(model, prompt_tokens, completion_tokens),
            "output": output,
            "status": status
        }
        
        traces.append(trace)
        base_time = end_time
    
    return traces


def _generate_slow_traces(count: int, models: List[str], 
                         error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate traces with slow response times."""
    traces = []
    base_time = datetime.now()
    
    for i in range(count):
        trace_id = f"slow_{uuid.uuid4().hex[:8]}"
        model = random.choice(models)
        
        prompt = fake.sentence(nb_words=random.randint(15, 50)) if fake else f"Complex prompt requiring slow processing {i+1}"
        
        is_error = random.random() < error_rate
        
        # Generate slow durations (above 5000ms threshold)
        if random.random() < 0.8:  # 80% chance for genuinely slow
            duration_ms = random.randint(5000, 30000)  # 5-30 seconds
        else:
            duration_ms = random.randint(2000, 4999)   # Just under threshold
        
        if is_error:
            output = ""
            status = "timeout" if random.random() < 0.7 else "error"
            completion_tokens = 0
        else:
            output = fake.text(max_nb_chars=random.randint(200, 800)) if fake else f"Detailed response {i+1}"
            status = "success"
            completion_tokens = random.randint(100, 500)
        
        prompt_tokens = random.randint(50, 300)
        
        start_time = base_time + timedelta(seconds=i * random.randint(2, 8))
        end_time = start_time + timedelta(milliseconds=duration_ms)
        
        trace = {
            "traceId": trace_id,
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "input": {
                "model": model,
                "prompt": prompt
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "cost": _calculate_cost(model, prompt_tokens, completion_tokens),
            "output": output,
            "status": status,
            "duration_ms": duration_ms
        }
        
        traces.append(trace)
        base_time = end_time
    
    return traces


def _generate_mixed_error_traces(count: int, models: List[str], 
                                error_rate: float, fake) -> List[Dict[str, Any]]:
    """Generate traces with mixed error patterns."""
    traces = []
    base_time = datetime.now()
    
    error_types = ['429_rate_limit', 'timeout', 'network_error', 'invalid_request', 'model_overloaded']
    
    for i in range(count):
        trace_id = f"mixed_{uuid.uuid4().hex[:8]}"
        model = random.choice(models)
        
        prompt = fake.sentence(nb_words=random.randint(8, 30)) if fake else f"Mixed scenario prompt {i+1}"
        prompt_tokens = random.randint(10, 250)
        
        is_error = random.random() < error_rate
        
        if is_error:
            error_type = random.choice(error_types)
            
            if error_type == '429_rate_limit':
                output = ""
                status = "error"
                completion_tokens = 0
                duration_ms = random.randint(50, 200)  # Quick failure
                metadata = {"error_code": 429, "error_type": "rate_limit"}
                
            elif error_type == 'timeout':
                output = ""
                status = "timeout"
                completion_tokens = 0
                duration_ms = random.randint(10000, 30000)  # Long timeout
                metadata = {"error_type": "timeout"}
                
            elif error_type == 'network_error':
                output = ""
                status = "error"
                completion_tokens = 0
                duration_ms = random.randint(100, 2000)
                metadata = {"error_type": "network"}
                
            elif error_type == 'invalid_request':
                output = ""
                status = "error"
                completion_tokens = 0
                duration_ms = random.randint(50, 300)
                metadata = {"error_code": 400, "error_type": "invalid_request"}
                
            else:  # model_overloaded
                output = ""
                status = "error"
                completion_tokens = 0
                duration_ms = random.randint(1000, 5000)
                metadata = {"error_code": 503, "error_type": "model_overloaded"}
        
        else:
            # Success case with some variations
            if random.random() < 0.1:  # 10% partial responses
                output = fake.sentence(nb_words=random.randint(5, 15)) + "..." if fake else "Partial response..."
                status = "partial"
                completion_tokens = random.randint(5, 50)
                duration_ms = random.randint(1000, 4000)
                metadata = {"completion_reason": "length"}
            else:
                output = fake.text(max_nb_chars=random.randint(100, 600)) if fake else f"Complete response {i+1}"
                status = "success"
                completion_tokens = random.randint(20, 400)
                duration_ms = random.randint(300, 3000)
                metadata = {}
        
        start_time = base_time + timedelta(seconds=i * random.randint(1, 6))
        end_time = start_time + timedelta(milliseconds=duration_ms)
        
        trace = {
            "traceId": trace_id,
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "input": {
                "model": model,
                "prompt": prompt
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "cost": _calculate_cost(model, prompt_tokens, completion_tokens),
            "output": output,
            "status": status
        }
        
        if metadata:
            trace["metadata"] = metadata
        
        traces.append(trace)
        base_time = end_time
    
    return traces


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost for a trace based on model and token usage."""
    # Simplified pricing (per 1k tokens)
    pricing = {
        'gpt-4o': {'prompt': 0.005, 'completion': 0.015},
        'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
        'gpt-4': {'prompt': 0.03, 'completion': 0.06},
        'gpt-3.5-turbo': {'prompt': 0.0005, 'completion': 0.0015},
    }
    
    # Default pricing for unknown models
    default_pricing = {'prompt': 0.002, 'completion': 0.006}
    
    model_pricing = pricing.get(model, default_pricing)
    
    prompt_cost = (prompt_tokens / 1000) * model_pricing['prompt']
    completion_cost = (completion_tokens / 1000) * model_pricing['completion']
    
    return round(prompt_cost + completion_cost, 6)


def _write_jsonl_traces(output_path: Path, traces: List[Dict[str, Any]]):
    """Write traces to JSONL file."""
    try:
        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for trace in traces:
                json.dump(trace, f, ensure_ascii=False)
                f.write('\n')
                
    except PermissionError:
        raise Exception(f"Permission denied writing to {output_path}")
    except Exception as e:
        raise Exception(f"Failed to write traces to {output_path}: {str(e)}")


def _run_policy_check_on_file(output_path: Path):
    """Run policy check on the generated file."""
    import subprocess
    import os
    
    try:
        # Set environment variables for proper UTF-8 handling on Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Run crashlens policy-check command
        cmd = [
            sys.executable, '-m', 'crashlens.cli', 'policy-check',
            str(output_path),
            '--policy-template', 'all',
            '--fail-on-violations',
            '--severity-threshold', 'high'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              timeout=60, env=env, encoding='utf-8', 
                              errors='replace')
        
        if result.stdout:
            click.echo(result.stdout)
        
        if result.stderr:
            click.echo(result.stderr, err=True)
            
        if result.returncode != 0:
            click.echo(f"⚠️  Policy check completed with return code: {result.returncode}")
        else:
            click.echo("✅ Policy check completed successfully")
            
    except subprocess.TimeoutExpired:
        click.echo("❌ Policy check timed out after 60 seconds", err=True)
    except Exception as e:
        click.echo(f"❌ Error running policy check: {str(e)}", err=True)


@click.group()
def slack():
    """Slack integration commands"""
    pass


@slack.command()
@click.option('--webhook-url', type=str, help='Slack webhook URL (or set CRASHLENS_SLACK_WEBHOOK env var)')
@click.option('--report-file', type=click.Path(exists=True, path_type=Path), 
              default='report.md', help='Path to the report file (default: report.md)')
def notify(webhook_url: Optional[str], report_file: Path):
    """Send CrashLens report to Slack via webhook"""
    
    # Get webhook URL from option or environment variable
    if not webhook_url:
        webhook_url = os.getenv('CRASHLENS_SLACK_WEBHOOK')
    
    if not webhook_url:
        click.echo("❌ Webhook URL required. Use --webhook-url or set CRASHLENS_SLACK_WEBHOOK env var", err=True)
        sys.exit(1)
    
    # Check if report file exists
    if not report_file.exists():
        click.echo(f"❌ Report file not found: {report_file}", err=True)
        sys.exit(1)
    
    try:
        # Load the report file
        report_content = report_file.read_text(encoding='utf-8')
        
        # Extract key metrics from report
        total_spend = "Unknown"
        potential_savings = "Unknown"
        
        lines = report_content.split('\n')
        for line in lines:
            line = line.strip()
            if 'Total Spend' in line or 'total spend' in line.lower():
                # Extract cost value (look for currency symbols and numbers)
                import re
                cost_match = re.search(r'[\$₹€£¥]?[\d,]+\.?\d*', line)
                if cost_match:
                    total_spend = cost_match.group()
            elif 'Potential Savings' in line or 'potential savings' in line.lower():
                # Extract savings value
                import re
                savings_match = re.search(r'[\$₹€£¥]?[\d,]+\.?\d*', line)
                if savings_match:
                    potential_savings = savings_match.group()
            elif 'Cost:' in line and '$' in line:
                # Extract from summary line like "Cost: $859.52"
                import re
                cost_match = re.search(r'[\$₹€£¥]?[\d,]+\.?\d*', line)
                if cost_match and total_spend == "Unknown":
                    total_spend = cost_match.group()
        
        # Parse Slack-formatted content for better display
        def convert_slack_to_native(content):
            """Convert Slack-formatted markdown to native Slack formatting"""
            lines = content.split('\n')
            formatted_lines = []
            
            for line in lines:
                # Convert headers
                if line.startswith('🤖 **Model Breakdown**'):
                    formatted_lines.append('🤖 *Model Breakdown*')
                elif line.startswith('🏆 **Top Expensive Traces**'):
                    formatted_lines.append('🏆 *Top Expensive Traces*')
                elif line.startswith('🚨 **Waste Analysis**'):
                    formatted_lines.append('🚨 *Waste Analysis*')
                # Convert table headers and content
                elif line.startswith('| Model | Cost | Percentage |'):
                    formatted_lines.append('`Model          Cost       %`')
                elif line.startswith('| Rank | Model | Cost |'):
                    formatted_lines.append('`Rank  Model    Cost`')
                elif line.startswith('| Issue Type | Count | Cost | Tokens |'):
                    formatted_lines.append('`Issue Type    Count   Cost      Tokens`')
                elif line.startswith('|---'):
                    continue  # Skip separator lines
                elif line.startswith('| ') and line.endswith(' |'):
                    # Convert table rows to monospace format
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    if len(cells) >= 2:
                        formatted_line = '`' + '  '.join(f"{cell:<12}" for cell in cells) + '`'
                        formatted_lines.append(formatted_line)
                else:
                    # Keep other lines as-is, but remove excessive emojis in summary
                    if not line.startswith('📊 CrashLens Summary'):
                        formatted_lines.append(line)
                    else:
                        # Simplify summary line
                        if 'Cost:' in line:
                            import re
                            cost_match = re.search(r'Cost: ([\$₹€£¥]?[\d,]+\.?\d*)', line)
                            traces_match = re.search(r'Traces: (\d+)', line)
                            if cost_match and traces_match:
                                formatted_lines.append(f"📊 *Analysis Summary*\n• Traces: {traces_match.group(1)}\n• Total Cost: {cost_match.group(1)}")
            
            return '\n'.join(formatted_lines)
        
        # Convert the report content
        formatted_content = convert_slack_to_native(report_content)
        
        # Split into sections for better display
        sections = formatted_content.split('\n\n')
        
        # Construct Slack payload using blocks with native formatting
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔍 *CrashLens Analysis Complete*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💰 *Total Spend:* {total_spend}\n🎯 *Potential Savings:* {potential_savings}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add formatted sections
        for section in sections[:3]:  # Limit to first 3 sections to avoid message size limits
            if section.strip():
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": section.strip()[:3000]  # Slack has text limits
                    }
                })
        
        payload = {"blocks": blocks}
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            click.echo("✅ Slack notification sent successfully")
        else:
            click.echo(f"❌ Failed to send Slack notification. Status: {response.status_code}, Response: {response.text}", err=True)
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Network error sending to Slack: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error processing report or sending to Slack: {str(e)}", err=True)
        sys.exit(1)


# Add commands to CLI
cli.add_command(policy_check)
cli.add_command(list_policy_templates)
cli.add_command(init)
cli.add_command(simulate)
cli.add_command(slack)


if __name__ == "__main__":
    cli()