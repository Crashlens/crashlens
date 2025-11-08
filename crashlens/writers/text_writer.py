"""
Text Writer for CrashLens Guard Reports

Formats guard policy violation reports as plain text with PII scrubbing support.
"""

from typing import Any, Dict

from crashlens.utils.pii_scrubber import PIIScrubber


class TextWriter:
    """Writes guard reports in plain text format with PII handling"""
    
    def __init__(self, strip_pii: bool = False, no_content: bool = False):
        """
        Initialize text writer with privacy options
        
        Args:
            strip_pii: If True, redact PII (emails, phones, SSN, credit cards)
            no_content: If True, omit content examples from report
        """
        self.strip_pii = strip_pii
        self.no_content = no_content
        self.pii_scrubber = PIIScrubber() if strip_pii else None
    
    def format(self, report: Dict[str, Any], logfile: str) -> str:
        """
        Format report as plain text
        
        Args:
            report: Report data structure with rules, violations, examples
            logfile: Path to log file that was scanned
            
        Returns:
            Plain text report string
        """
        lines = ["=" * 60]
        lines.append("CrashLens Guard Report")
        lines.append("=" * 60)
        lines.append(f"Scanned: {logfile}")
        lines.append(f"Rules Checked: {len(report['rules'])}")
        lines.append(f"Violations Found: {report['summary']['violations']}")
        lines.append("=" * 60)
        lines.append("")
        
        if report['summary']['violations'] == 0:
            lines.append("✅ No violations detected")
            lines.append("")
            return "\n".join(lines)
        
        for rid, meta in report["rules"].items():
            if meta["count"] == 0:
                continue
            
            lines.append(f"Rule: {rid} [{meta['severity'].upper()}]")
            lines.append(f"Description: {meta['description']}")
            lines.append(f"Violation Count: {meta['count']}")
            
            # Skip examples if no_content flag is set
            if not self.no_content and meta['examples']:
                lines.append("Examples:")
                for ex in meta['examples'][:2]:
                    timestamp = ex.get('timestamp', 'N/A')
                    model = ex.get('model', 'N/A')
                    tokens = ex.get('tokens', 'N/A')
                    prompt = ex.get('prompt', '')
                    
                    # Apply PII scrubbing if enabled
                    if prompt:
                        prompt = self._maybe_scrub(prompt)
                    
                    prompt_preview = prompt[:60] if prompt else ''
                    lines.append(f"  - {timestamp} | {model} | tokens={tokens} | prompt={prompt_preview}")
            
            lines.append("-" * 60)
            lines.append("")
        
        return "\n".join(lines)
    
    def _maybe_scrub(self, text: str) -> str:
        """
        Scrub PII from text if strip_pii is enabled
        
        Args:
            text: Input text
            
        Returns:
            Original text or scrubbed text
        """
        if not text or not isinstance(text, str):
            return str(text)
        
        if self.strip_pii and self.pii_scrubber:
            return self.pii_scrubber.scrub_text(text)
        
        return text
