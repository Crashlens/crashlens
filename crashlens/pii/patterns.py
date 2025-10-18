"""
PII Pattern Definitions for CrashLens
Regex patterns to detect and remove personally identifiable information.
"""

import re
from typing import Dict, Pattern

# Compiled regex patterns for performance
PII_PATTERNS: Dict[str, Pattern] = {
    # Email addresses: user@example.com
    'email': re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    ),
    
    # US Phone numbers: (123) 456-7890, 123-456-7890, 1234567890
    'phone_us': re.compile(
        r'\b(\+?1[-.\s]?)?'                    # Optional country code
        r'(\(?\d{3}\)?[-.\s]?)'                # Area code
        r'\d{3}[-.\s]?'                        # Exchange
        r'\d{4}\b'                             # Subscriber number
    ),
    
    # US Social Security Numbers: 123-45-6789
    'ssn': re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b'
    ),
    
    # Credit card numbers: 1234-5678-9012-3456 or 1234567890123456
    'credit_card': re.compile(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    ),
    
    # IP addresses: 192.168.1.1
    'ip_address': re.compile(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ),
    
    # Generic API keys/tokens (32+ alphanumeric characters)
    'api_key': re.compile(
        r'\b[A-Za-z0-9_-]{32,}\b'
    ),
    
    # Street addresses (simplified pattern)
    'street_address': re.compile(
        r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b',
        re.IGNORECASE
    ),
    
    # Dates in various formats: MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD
    'date': re.compile(
        r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
    ),
}

# Replacement tokens for each PII type
PII_REPLACEMENTS: Dict[str, str] = {
    'email': '[EMAIL_REDACTED]',
    'phone_us': '[PHONE_REDACTED]',
    'ssn': '[SSN_REDACTED]',
    'credit_card': '[CREDIT_CARD_REDACTED]',
    'ip_address': '[IP_REDACTED]',
    'api_key': '[API_KEY_REDACTED]',
    'street_address': '[ADDRESS_REDACTED]',
    'date': '[DATE_REDACTED]',
}

def validate_email(text: str) -> bool:
    """Validate if text contains email addresses."""
    return bool(PII_PATTERNS['email'].search(text))

def validate_phone(text: str) -> bool:
    """Validate if text contains phone numbers."""
    return bool(PII_PATTERNS['phone_us'].search(text))

def validate_ssn(text: str) -> bool:
    """Validate if text contains SSN."""
    return bool(PII_PATTERNS['ssn'].search(text))

def get_pattern(pii_type: str) -> Pattern:
    """Get compiled regex pattern for PII type."""
    if pii_type not in PII_PATTERNS:
        raise ValueError(f"Unknown PII type: {pii_type}")
    return PII_PATTERNS[pii_type]

def get_replacement(pii_type: str) -> str:
    """Get replacement token for PII type."""
    if pii_type not in PII_REPLACEMENTS:
        raise ValueError(f"Unknown PII type: {pii_type}")
    return PII_REPLACEMENTS[pii_type]
