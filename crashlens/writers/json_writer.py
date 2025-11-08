"""
JSON Writer for CrashLens Guard Reports

Formats guard policy violation reports as JSON with PII scrubbing support.
"""

import json
from typing import Any, Dict, Optional

from crashlens.utils.pii_scrubber import PIIScrubber


class JSONWriter:
    """Writes guard reports in JSON format with PII handling"""
    
    def __init__(self, strip_pii: bool = False, no_content: bool = False):
        """
        Initialize JSON writer with privacy options
        
        Args:
            strip_pii: If True, redact PII (emails, phones, SSN, credit cards)
            no_content: If True, omit content examples from report
        """
        self.strip_pii = strip_pii
        self.no_content = no_content
        self.pii_scrubber = PIIScrubber() if strip_pii else None
    
    def format(self, report: Dict[str, Any]) -> str:
        """
        Format report as pretty-printed JSON
        
        Args:
            report: Report data structure with rules, violations, examples
            
        Returns:
            Pretty-printed JSON string
        """
        # Apply PII scrubbing if enabled
        if self.strip_pii and self.pii_scrubber:
            report = self._scrub_pii_from_report(report)
        
        # Remove content examples if no_content flag is set
        if self.no_content:
            report = self._remove_content_examples(report)
        
        return json.dumps(report, indent=2)
    
    def _scrub_pii_from_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively scrub PII from report data
        
        Args:
            report: Original report dictionary
            
        Returns:
            Deep copy of report with PII redacted
        """
        if not self.pii_scrubber:
            return report
        
        import copy
        scrubbed = copy.deepcopy(report)
        
        # Scrub examples in rules
        if 'rules' in scrubbed:
            for rule_id, rule_data in scrubbed['rules'].items():
                if 'examples' in rule_data and isinstance(rule_data['examples'], list):
                    for example in rule_data['examples']:
                        # Scrub prompt field
                        if 'prompt' in example and isinstance(example['prompt'], str):
                            example['prompt'] = self.pii_scrubber.scrub_text(example['prompt'])
                        
                        # Scrub completion field if present
                        if 'completion' in example and isinstance(example['completion'], str):
                            example['completion'] = self.pii_scrubber.scrub_text(example['completion'])
                        
                        # Scrub endpoint (may contain API keys in query params)
                        if 'endpoint' in example and isinstance(example['endpoint'], str):
                            example['endpoint'] = self.pii_scrubber.scrub_text(example['endpoint'])
        
        return scrubbed
    
    def _remove_content_examples(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove content examples from report
        
        Args:
            report: Original report dictionary
            
        Returns:
            Deep copy of report without content examples
        """
        import copy
        no_content_report = copy.deepcopy(report)
        
        # Remove examples from rules
        if 'rules' in no_content_report:
            for rule_id, rule_data in no_content_report['rules'].items():
                if 'examples' in rule_data:
                    # Keep count but remove example details
                    rule_data['examples'] = []
        
        return no_content_report
