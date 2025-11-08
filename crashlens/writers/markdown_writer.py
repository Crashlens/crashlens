"""
Markdown Writer for CrashLens Guard Reports

Formats guard policy violation reports as Markdown with PII scrubbing support.
"""

from typing import Any, Dict

from crashlens.utils.pii_scrubber import PIIScrubber


class MarkdownWriter:
    """Writes guard reports in Markdown format with PII handling"""
    
    def __init__(self, strip_pii: bool = False, no_content: bool = False):
        """
        Initialize Markdown writer with privacy options
        
        Args:
            strip_pii: If True, redact PII (emails, phones, SSN, credit cards)
            no_content: If True, omit content examples from report
        """
        self.strip_pii = strip_pii
        self.no_content = no_content
        self.pii_scrubber = PIIScrubber() if strip_pii else None
    
    def format(self, report: Dict[str, Any], logfile: str) -> str:
        """
        Format report as Markdown
        
        Args:
            report: Report data structure with rules, violations, examples
            logfile: Path to log file that was scanned
            
        Returns:
            Markdown-formatted report string
        """
        lines = ["# CrashLens Guard Report", ""]
        lines.append(f"- **Scanned**: `{logfile}`")
        lines.append(f"- **Rules Checked**: {len(report['rules'])}")
        lines.append(f"- **Violations Found**: {report['summary']['violations']}")
        lines.append("")
        
        if report['summary']['violations'] == 0:
            lines.append("✅ **No violations detected**")
            lines.append("")
            return "\n".join(lines)
        
        lines.append("## Violations by Rule")
        lines.append("")
        
        for rid, meta in report["rules"].items():
            if meta["count"] == 0:
                continue
                
            lines.append(f"### {rid} — `{meta['severity']}` severity")
            lines.append("")
            lines.append(f"**Description**: {meta['description']}")
            lines.append("")
            lines.append(f"**Violation Count**: {meta['count']}")
            lines.append("")
            
            # Skip examples if no_content flag is set
            if not self.no_content and meta['examples']:
                lines.append("**Example Violations**:")
                lines.append("")
                for i, ex in enumerate(meta['examples'][:3], 1):
                    lines.append(f"{i}. **Timestamp**: {ex.get('timestamp', 'N/A')}")
                    lines.append(f"   - **Model**: `{ex.get('model', 'N/A')}`")
                    lines.append(f"   - **Tokens**: {ex.get('tokens', 'N/A')}")
                    lines.append(f"   - **Retry Count**: {ex.get('retry_count', 'N/A')}")
                    lines.append(f"   - **Fallback**: {ex.get('fallback_triggered', 'N/A')}")
                    lines.append(f"   - **Endpoint**: `{self._maybe_scrub(ex.get('endpoint', 'N/A'))}`")
                    
                    if ex.get('prompt'):
                        prompt_text = self._maybe_scrub(ex['prompt'])
                        prompt_preview = prompt_text[:80]
                        if len(prompt_text) > 80:
                            prompt_preview += "..."
                        lines.append(f"   - **Prompt**: {prompt_preview}")
                    
                    lines.append("")
            
            lines.append("---")
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
