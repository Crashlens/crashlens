"""
CLI Runner Functions for CrashLens
Handles specialized CLI operations like contract checking
"""

import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
import click

from .schema_checker import SchemaChecker


def run_contract_check(logs: List[Dict[str, Any]], log_format: str = "langfuse-v1", 
                      verbose: bool = False, output_format: str = "text") -> int:
    """
    Run schema contract validation on logs and exit with appropriate status code.
    
    Args:
        logs: List of log entries to validate
        log_format: Log format version to validate against
        verbose: Enable verbose output
        output_format: Output format - "text" or "json"
        
    Returns:
        Exit code: 0 for success, 1 for failure
    """
    # Initialize schema checker
    checker = SchemaChecker(log_format=log_format, verbose=verbose)
    
    # Validate that the schema contract is properly defined and get info
    contract_info = checker.get_contract_info()
    if "error" in contract_info:
        if output_format == "json":
            import json
            error_result = {
                "format": log_format,
                "success": False,
                "error": contract_info['error'],
                "contract_info": None
            }
            print(json.dumps(error_result, indent=2))
        else:
            click.echo(f"Invalid schema contract for format: {log_format}", err=True)
        return 1
    
    # Show contract info if verbose (but not for JSON output)
    if verbose and output_format != "json":
        click.echo(f"Validating against {contract_info['format']} schema:")
        click.echo(f"   Required fields: {', '.join(contract_info['required_fields'])}")
        click.echo(f"   Optional fields: {', '.join(contract_info['optional_fields'])}")
        click.echo(f"   Total entries to check: {len(logs)}")
        click.echo("")
    
    # Run contract validation
    errors = checker.check_logs(logs)
    
    # Prepare result data  
    # Make contract_info JSON-serializable by converting types to strings
    json_safe_contract_info = {
        key: value if key != 'field_types' else {k: str(v) for k, v in value.items()}
        for key, value in contract_info.items()
    }
    
    result_data = {
        "format": log_format,
        "total_entries": len(logs),
        "errors": errors,
        "error_count": len(errors),
        "success": len(errors) == 0,
        "contract_info": json_safe_contract_info
    }
    
    # JSON output format
    if output_format == "json":
        import json
        print(json.dumps(result_data, indent=2))
        return 0 if len(errors) == 0 else 1
    
    # Text output format (default)
    if verbose and output_format != "json":
        click.echo(f"Validating against {contract_info['format']} schema:")
        click.echo(f"   Required fields: {', '.join(contract_info['required_fields'])}")
        click.echo(f"   Optional fields: {', '.join(contract_info['optional_fields'])}")
        click.echo(f"   Total entries to check: {len(logs)}")
        click.echo("")
    
    # Report results
    if not errors:
        click.echo("Contract check passed. All required fields present.")
        if verbose:
            click.echo(f"   Validated {len(logs)} log entries successfully")
        return 0
    else:
        click.echo("Contract check failed:")
        for error in errors:
            click.echo(f"  - {error}")
        
        # Summary
        click.echo("")
        click.echo(f"Found {len(errors)} violation(s) across {len(logs)} log entries.")
        
        if verbose:
            # Group errors by type for better insight
            error_types = {}
            for error in errors:
                if "Missing required field:" in error:
                    field = error.split("Missing required field: ")[1].split()[0]
                    error_types.setdefault("missing_fields", set()).add(field)
                elif "incorrect type" in error:
                    error_types.setdefault("type_errors", []).append(error)
            
            if error_types:
                click.echo("Error summary:")
                if "missing_fields" in error_types:
                    click.echo(f"   Missing fields: {', '.join(sorted(error_types['missing_fields']))}")
                if "type_errors" in error_types:
                    click.echo(f"   Type errors: {len(error_types['type_errors'])} occurrences")
        
        return 1


def load_logs_from_source(source: Optional[str], stdin_mode: bool = False, paste_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Load logs from various sources (file, stdin, clipboard).
    
    Args:
        source: File path or content source
        stdin_mode: Read from stdin
        paste_mode: Read from clipboard
        
    Returns:
        List of parsed log entries
        
    Raises:
        SystemExit: If logs cannot be loaded or parsed
    """
    logs = []
    
    try:
        if stdin_mode:
            # Read from stdin
            content = sys.stdin.read().strip()
            if not content:
                click.echo("Error: No input provided via stdin", err=True)
                sys.exit(1)
        elif paste_mode:
            # Read from clipboard
            try:
                import pyperclip
                content = pyperclip.paste().strip()
                if not content:
                    click.echo("Error: No content in clipboard", err=True)
                    sys.exit(1)
            except ImportError:
                click.echo("Error: pyperclip not available for --paste mode", err=True)
                sys.exit(1)
        else:
            # Read from file
            if not source or not Path(source).exists():
                click.echo(f"Error: Log file not found: {source}", err=True)
                sys.exit(1)
            
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        
        # Parse JSONL content
        if not content:
            click.echo("Error: Empty log content", err=True)
            sys.exit(1)
        
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                log_entry = json.loads(line)
                logs.append(log_entry)
            except json.JSONDecodeError as e:
                click.echo(f"Error: Invalid JSON on line {line_num}: {e}", err=True)
                sys.exit(1)
        
        if not logs:
            click.echo("Error: No valid log entries found", err=True)
            sys.exit(1)
        
        return logs
        
    except Exception as e:
        click.echo(f"Error loading logs: {e}", err=True)
        sys.exit(1)


def validate_log_format(log_format: str) -> str:
    """
    Validate and normalize log format string.
    
    Args:
        log_format: Log format string to validate
        
    Returns:
        Normalized log format string
        
    Raises:
        SystemExit: If log format is not supported
    """
    # Check if format is supported
    checker = SchemaChecker()
    supported_formats = checker.get_supported_formats()
    
    if log_format not in supported_formats:
        click.echo(f"Error: Unsupported log format: {log_format}", err=True)
        click.echo(f"💡 Supported formats: {', '.join(supported_formats)}", err=True)
        sys.exit(1)
    
    return log_format


def print_contract_info(log_format: str) -> None:
    """
    Print detailed information about a schema contract.
    
    Args:
        log_format: Log format to show info for
    """
    checker = SchemaChecker(log_format=log_format)
    contract_info = checker.get_contract_info()
    
    if "error" in contract_info:
        click.echo(f"{contract_info['error']}", err=True)
        return
    
    click.echo(f"Schema Contract Information for {contract_info['format']}")
    click.echo("=" * 50)
    click.echo(f"Required fields ({len(contract_info['required_fields'])}):")
    for field in contract_info['required_fields']:
        click.echo(f"  • {field}")
    
    if contract_info['optional_fields']:
        click.echo(f"\nOptional fields ({len(contract_info['optional_fields'])}):")
        for field in contract_info['optional_fields']:
            click.echo(f"  • {field}")
    
    if contract_info['field_types']:
        click.echo(f"\nField type requirements:")
        for field, field_type in contract_info['field_types'].items():
            if isinstance(field_type, tuple):
                type_name = " or ".join(t.__name__ for t in field_type)
            else:
                type_name = field_type.__name__
            click.echo(f"  • {field}: {type_name}")
    
    click.echo(f"\nTotal fields: {contract_info['total_fields']}")


def run_contract_check_cli(logfile: Optional[str], log_format: str, stdin_mode: bool = False, 
                          paste_mode: bool = False, verbose: bool = False, 
                          show_info: bool = False, output_format: str = "text") -> int:
    """
    Complete CLI workflow for contract checking.
    
    Args:
        logfile: Path to log file (if not using stdin/paste)
        log_format: Log format version to validate against
        stdin_mode: Read from stdin
        paste_mode: Read from clipboard
        verbose: Enable verbose output
        output_format: Output format - "text" or "json"
        
    Returns:
        Exit code: 0 for success, 1 for failure
    """
    # Validate log format first
    log_format = validate_log_format(log_format)
    
    # Show contract info if requested
    if show_info:
        print_contract_info(log_format)
        return 0
    
    # Load logs from appropriate source
    logs = load_logs_from_source(logfile, stdin_mode, paste_mode)
    
    # Run contract validation
    return run_contract_check(logs, log_format, verbose, output_format)
