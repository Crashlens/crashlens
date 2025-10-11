"""
Error formatting utilities for JSON output
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any


def format_error_response(
    error: Exception, 
    request_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format errors as JSON response.
    
    Args:
        error: The exception that occurred
        request_id: Optional request ID for tracking
        additional_context: Optional additional context to include
        
    Returns:
        JSON string with error details
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    error_response = {
        "status": "error",
        "version": "1.0.0",
        "requestId": request_id,
        "timestamp": timestamp,
        "errors": [
            {
                "code": type(error).__name__,
                "message": str(error),
                "timestamp": timestamp
            }
        ],
        "data": None
    }
    
    # Add additional context if provided
    if additional_context:
        error_response["errors"][0]["context"] = additional_context
    
    return json.dumps(error_response, indent=2)


def format_validation_error(
    field: str,
    message: str,
    value: Any = None,
    request_id: Optional[str] = None
) -> str:
    """
    Format validation errors as JSON response.
    
    Args:
        field: The field that failed validation
        message: Validation error message
        value: The invalid value (optional)
        request_id: Optional request ID for tracking
        
    Returns:
        JSON string with validation error details
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    error_response = {
        "status": "error",
        "version": "1.0.0",
        "requestId": request_id,
        "timestamp": timestamp,
        "errors": [
            {
                "code": "ValidationError",
                "message": message,
                "field": field,
                "timestamp": timestamp
            }
        ],
        "data": None
    }
    
    if value is not None:
        error_response["errors"][0]["value"] = str(value)
    
    return json.dumps(error_response, indent=2)


def format_file_error(
    file_path: str,
    error: Exception,
    request_id: Optional[str] = None
) -> str:
    """
    Format file-related errors as JSON response.
    
    Args:
        file_path: Path to the file that caused the error
        error: The exception that occurred
        request_id: Optional request ID for tracking
        
    Returns:
        JSON string with file error details
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    error_response = {
        "status": "error",
        "version": "1.0.0",
        "requestId": request_id,
        "timestamp": timestamp,
        "errors": [
            {
                "code": type(error).__name__,
                "message": str(error),
                "file": file_path,
                "timestamp": timestamp
            }
        ],
        "data": None
    }
    
    return json.dumps(error_response, indent=2)
