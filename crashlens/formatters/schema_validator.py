"""
JSON schema validation utilities for CrashLens output
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def load_schema() -> Dict[str, Any]:
    """
    Load the JSON schema for CrashLens output.
    
    Returns:
        Dictionary containing the JSON schema
    """
    schema_path = Path(__file__).parent / "schema.json"
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_output(output_json: str) -> Tuple[bool, List[str]]:
    """
    Validate JSON output against the CrashLens schema.
    
    Args:
        output_json: JSON string to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if not HAS_JSONSCHEMA:
        return True, ["jsonschema not installed - skipping validation"]
    
    try:
        # Parse JSON
        data = json.loads(output_json)
        
        # Load schema
        schema = load_schema()
        
        # Validate
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))
        
        if not errors:
            return True, []
        
        # Format errors
        error_messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path)
            error_messages.append(f"{path}: {error.message}")
        
        return False, error_messages
        
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {str(e)}"]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def validate_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a JSON file against the CrashLens schema.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return validate_output(content)
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]
    except Exception as e:
        return False, [f"Error reading file: {str(e)}"]


if __name__ == '__main__':
    # CLI for validating files
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python schema_validator.py <json_file>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    is_valid, errors = validate_file(file_path)
    
    if is_valid:
        print(f"✓ {file_path} is valid")
        sys.exit(0)
    else:
        print(f"✗ {file_path} has validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
