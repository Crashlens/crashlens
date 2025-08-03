"""
Schema Contract Checker for CrashLens
Validates log entries against required schema contracts
"""

from typing import Dict, List, Any, Set, Optional
import logging


class SchemaChecker:
    """
    Validates log entries against predefined schema contracts.
    
    Supports validation of required fields, field types, and nested structures.
    Designed to work with various log formats including Langfuse logs.
    """
    
    def __init__(self, log_format: str = "langfuse-v1", verbose: bool = False):
        """
        Initialize schema checker with specific log format requirements.
        
        Args:
            log_format: Log format version (e.g., "langfuse-v1", "langfuse-v2")
            verbose: Enable verbose logging for debugging
        """
        self.log_format = log_format
        self.verbose = verbose
        
        # Define schema contracts for different log formats
        self.schema_contracts = {
            "langfuse-v1": {
                "required_fields": [
                    "traceId",  # Using Langfuse's actual field name
                    "startTime",  # timestamp equivalent in Langfuse
                    "input.model"  # model field is nested in input
                ],
                "optional_fields": [
                    "endTime",
                    "cost",
                    "usage.prompt_tokens",
                    "usage.completion_tokens",
                    "output"
                ],
                "field_types": {
                    "traceId": str,
                    "startTime": str,
                    "endTime": str,
                    "cost": (int, float),
                    "usage.prompt_tokens": int,
                    "usage.completion_tokens": int
                }
            },
            "langfuse-v2": {
                "required_fields": [
                    "traceId",
                    "startTime", 
                    "input.model",
                    "userId"  # Additional requirement for v2
                ],
                "optional_fields": [
                    "endTime",
                    "cost",
                    "usage.prompt_tokens", 
                    "usage.completion_tokens",
                    "output",
                    "metadata"
                ],
                "field_types": {
                    "traceId": str,
                    "userId": str,
                    "startTime": str,
                    "endTime": str,
                    "cost": (int, float),
                    "usage.prompt_tokens": int,
                    "usage.completion_tokens": int
                }
            }
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.
        
        Args:
            data: Dictionary to search in
            field_path: Dot-separated path (e.g., "input.model", "usage.prompt_tokens")
            
        Returns:
            Value at the specified path, or None if not found
        """
        try:
            value = data
            for key in field_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except (TypeError, KeyError, AttributeError):
            return None
    
    def check_log(self, log: Dict[str, Any]) -> List[str]:
        """
        Check a single log entry against the schema contract.
        
        Args:
            log: Log entry dictionary to validate
            
        Returns:
            List of error messages for any violations found
        """
        errors = []
        
        # Get schema contract for the log format
        if self.log_format not in self.schema_contracts:
            return [f"Unknown log format: {self.log_format}"]
        
        contract = self.schema_contracts[self.log_format]
        required_fields = contract.get("required_fields", [])
        field_types = contract.get("field_types", {})
        
        # Check required fields
        for field in required_fields:
            value = self._get_nested_value(log, field)
            if value is None:
                errors.append(f"Missing required field: {field}")
            elif field in field_types:
                # Check field type if specified
                expected_type = field_types[field]
                if not isinstance(value, expected_type):
                    if isinstance(expected_type, tuple):
                        type_names = " or ".join(t.__name__ for t in expected_type)
                    else:
                        type_names = expected_type.__name__
                    errors.append(f"Field '{field}' has incorrect type. Expected {type_names}, got {type(value).__name__}")
        
        # Additional type checking for optional fields that are present
        for field, expected_type in field_types.items():
            if field not in required_fields:  # Skip required fields (already checked above)
                value = self._get_nested_value(log, field)
                if value is not None and not isinstance(value, expected_type):
                    if isinstance(expected_type, tuple):
                        type_names = " or ".join(t.__name__ for t in expected_type)
                    else:
                        type_names = expected_type.__name__
                    errors.append(f"Optional field '{field}' has incorrect type. Expected {type_names}, got {type(value).__name__}")
        
        if self.verbose and not errors:
            self.logger.debug(f"Log entry passed schema validation for {self.log_format}")
        
        return errors
    
    def check_logs(self, logs: List[Dict[str, Any]]) -> List[str]:
        """
        Check multiple log entries and aggregate all errors.
        
        Args:
            logs: List of log entry dictionaries to validate
            
        Returns:
            List of formatted error messages with line numbers
        """
        all_errors = []
        
        for line_num, log in enumerate(logs, 1):
            log_errors = self.check_log(log)
            for error in log_errors:
                all_errors.append(f"Line {line_num}: {error}")
        
        if self.verbose:
            self.logger.debug(f"Checked {len(logs)} log entries, found {len(all_errors)} errors")
        
        return all_errors
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported log formats.
        
        Returns:
            List of supported log format names
        """
        return list(self.schema_contracts.keys())
    
    def get_contract_info(self, log_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a schema contract.
        
        Args:
            log_format: Log format to get info for (defaults to current format)
            
        Returns:
            Dictionary containing contract information
        """
        format_to_check = log_format or self.log_format
        
        if format_to_check not in self.schema_contracts:
            return {"error": f"Unknown log format: {format_to_check}"}
        
        contract = self.schema_contracts[format_to_check]
        
        return {
            "format": format_to_check,
            "required_fields": contract.get("required_fields", []),
            "optional_fields": contract.get("optional_fields", []),
            "field_types": contract.get("field_types", {}),
            "total_fields": len(contract.get("required_fields", [])) + len(contract.get("optional_fields", []))
        }
    
    def validate_contract_completeness(self) -> bool:
        """
        Validate that the current schema contract is properly defined.
        
        Returns:
            True if contract is valid, False otherwise
        """
        if self.log_format not in self.schema_contracts:
            self.logger.error(f"Schema contract not found for format: {self.log_format}")
            return False
        
        contract = self.schema_contracts[self.log_format]
        
        # Check that contract has required structure
        if "required_fields" not in contract:
            self.logger.error(f"Schema contract for {self.log_format} missing 'required_fields'")
            return False
        
        if not contract["required_fields"]:
            self.logger.warning(f"Schema contract for {self.log_format} has no required fields")
        
        return True
