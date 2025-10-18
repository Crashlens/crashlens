"""
PII Remover - Core logic for removing PII from text
"""

from typing import Dict, List, Set, Optional
from .patterns import PII_PATTERNS, PII_REPLACEMENTS

class PIIRemover:
    """Remove personally identifiable information from text."""
    
    def __init__(self, pii_types: Optional[List[str]] = None):
        """
        Initialize PII remover.
        
        Args:
            pii_types: List of PII types to remove. If None, removes all types.
        """
        self.pii_types = pii_types or list(PII_PATTERNS.keys())
        self.stats = {pii_type: 0 for pii_type in self.pii_types}
        
    def remove_pii_from_text(self, text: str, dry_run: bool = False) -> str:
        """
        Remove PII from text string.
        
        Args:
            text: Input text containing potential PII
            dry_run: If True, only count PII without removing
            
        Returns:
            Sanitized text with PII removed (or original if dry_run)
        """
        if not text:
            return text
            
        sanitized = text
        
        for pii_type in self.pii_types:
            if pii_type not in PII_PATTERNS:
                continue
                
            pattern = PII_PATTERNS[pii_type]
            replacement = PII_REPLACEMENTS[pii_type]
            
            # Find all matches
            matches = pattern.findall(sanitized)
            match_count = len(matches)
            
            if match_count > 0:
                self.stats[pii_type] += match_count
                
                if not dry_run:
                    # Replace all matches with redaction token
                    sanitized = pattern.sub(replacement, sanitized)
        
        return sanitized
    
    def remove_pii_from_dict(self, data: dict, dry_run: bool = False) -> dict:
        """
        Remove PII from dictionary (log record).
        
        Args:
            data: Dictionary containing log data
            dry_run: If True, only count PII without removing
            
        Returns:
            Sanitized dictionary with PII removed
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Apply PII removal to string values
                sanitized[key] = self.remove_pii_from_text(value, dry_run)
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                sanitized[key] = self.remove_pii_from_dict(value, dry_run)
            elif isinstance(value, list):
                # Handle lists
                sanitized[key] = [
                    self.remove_pii_from_text(item, dry_run) if isinstance(item, str) 
                    else item 
                    for item in value
                ]
            else:
                # Keep other types as-is (numbers, booleans, null)
                sanitized[key] = value
        
        return sanitized
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics on PII items removed."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counter."""
        self.stats = {pii_type: 0 for pii_type in self.pii_types}
