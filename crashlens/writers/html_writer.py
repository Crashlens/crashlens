"""
HTML Writer for CrashLens Guard Reports

Formats guard policy violation reports as HTML with Bootstrap styling and PII scrubbing.
"""

import html
from typing import Any, Dict

from crashlens.utils.pii_scrubber import PIIScrubber


class HTMLWriter:
    """Writes guard reports in HTML format with Bootstrap styling"""
    
    # Color mapping for severity levels
    SEVERITY_COLORS = {
        'critical': '#dc3545',  # Red
        'high': '#fd7e14',      # Orange
        'medium': '#ffc107',    # Yellow
        'low': '#6c757d'        # Gray
    }
    
    def __init__(self, strip_pii: bool = False, no_content: bool = False):
        """
        Initialize HTML writer with privacy options
        
        Args:
            strip_pii: If True, redact PII (emails, phones, SSN, credit cards)
            no_content: If True, omit content examples from report
        """
        self.strip_pii = strip_pii
        self.no_content = no_content
        self.pii_scrubber = PIIScrubber() if strip_pii else None
    
    def format(self, report: Dict[str, Any], logfile: str, summary_only: bool = False) -> str:
        """
        Format report as HTML with Bootstrap styling
        
        Args:
            report: Report data structure with rules, violations, examples
            logfile: Path to log file that was scanned
            summary_only: If True, omit content examples (overrides no_content)
            
        Returns:
            HTML report string with inline styles for email compatibility
        """
        # Determine if we should show content
        show_content = not (self.no_content or summary_only)
        
        # Start HTML with inline styles
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '    <title>CrashLens Guard Report</title>',
            '    <style>',
            '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background-color: #f8f9fa; }',
            '        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
            '        h1 { color: #212529; border-bottom: 3px solid #0d6efd; padding-bottom: 10px; }',
            '        .summary { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }',
            '        .summary-item { display: inline-block; margin-right: 30px; }',
            '        .summary-label { font-weight: 600; color: #495057; }',
            '        .violation-card { border-left: 4px solid #dee2e6; padding: 15px; margin: 15px 0; background: #f8f9fa; border-radius: 4px; }',
            '        .violation-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }',
            '        .rule-id { font-weight: 700; font-size: 1.1em; color: #212529; }',
            '        .severity-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; color: white; }',
            '        .description { color: #6c757d; margin: 10px 0; }',
            '        .count { font-size: 1.2em; font-weight: 600; color: #dc3545; }',
            '        .examples { margin-top: 15px; }',
            '        .example-item { background: white; padding: 12px; margin: 8px 0; border-radius: 4px; border: 1px solid #dee2e6; }',
            '        .example-row { margin: 5px 0; }',
            '        .example-label { font-weight: 600; color: #495057; min-width: 120px; display: inline-block; }',
            '        .example-value { color: #212529; }',
            '        code { background: #f1f3f5; padding: 2px 6px; border-radius: 3px; font-family: "Courier New", monospace; }',
            '        .no-violations { text-align: center; padding: 40px; color: #28a745; font-size: 1.3em; }',
            '        .success-icon { font-size: 3em; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <div class="container">',
            '        <h1>🛡️ CrashLens Guard Report</h1>',
            '        <div class="summary">',
            f'            <div class="summary-item"><span class="summary-label">Scanned:</span> <code>{html.escape(logfile)}</code></div>',
            f'            <div class="summary-item"><span class="summary-label">Rules Checked:</span> {len(report["rules"])}</div>',
            f'            <div class="summary-item"><span class="summary-label">Violations Found:</span> <span class="count">{report["summary"]["violations"]}</span></div>',
            '        </div>',
        ]
        
        # No violations case
        if report['summary']['violations'] == 0:
            html_parts.extend([
                '        <div class="no-violations">',
                '            <div class="success-icon">✅</div>',
                '            <div>No violations detected - All policies passed!</div>',
                '        </div>',
            ])
        else:
            # Add violation cards
            for rid, meta in report["rules"].items():
                if meta["count"] == 0:
                    continue
                
                severity = meta['severity'].lower()
                color = self.SEVERITY_COLORS.get(severity, '#6c757d')
                
                html_parts.extend([
                    f'        <div class="violation-card" style="border-left-color: {color};">',
                    '            <div class="violation-header">',
                    f'                <span class="rule-id">{html.escape(rid)}</span>',
                    f'                <span class="severity-badge" style="background-color: {color};">{html.escape(severity.upper())}</span>',
                    '            </div>',
                    f'            <div class="description">{html.escape(meta["description"])}</div>',
                    f'            <div><span class="summary-label">Violation Count:</span> <span class="count">{meta["count"]}</span></div>',
                ])
                
                # Add examples if available and content should be shown
                if meta['examples'] and show_content:
                    html_parts.append('            <div class="examples">')
                    html_parts.append('                <div class="summary-label">Example Violations:</div>')
                    
                    for i, ex in enumerate(meta['examples'][:3], 1):
                        html_parts.append('                <div class="example-item">')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Example #{i}</span></div>')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Timestamp:</span> <span class="example-value">{html.escape(str(ex.get("timestamp", "N/A")))}</span></div>')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Model:</span> <code>{html.escape(str(ex.get("model", "N/A")))}</code></div>')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Tokens:</span> <span class="example-value">{html.escape(str(ex.get("tokens", "N/A")))}</span></div>')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Retry Count:</span> <span class="example-value">{html.escape(str(ex.get("retry_count", "N/A")))}</span></div>')
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Fallback:</span> <span class="example-value">{html.escape(str(ex.get("fallback_triggered", "N/A")))}</span></div>')
                        
                        endpoint = self._maybe_scrub(str(ex.get("endpoint", "N/A")))
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Endpoint:</span> <code>{html.escape(endpoint)}</code></div>')
                        
                        if ex.get('prompt'):
                            prompt_text = self._maybe_scrub(ex['prompt'])
                            prompt_preview = prompt_text[:80]
                            if len(prompt_text) > 80:
                                prompt_preview += "..."
                            html_parts.append(f'                    <div class="example-row"><span class="example-label">Prompt:</span> <span class="example-value">{html.escape(prompt_preview)}</span></div>')
                        
                        html_parts.append('                </div>')
                    
                    html_parts.append('            </div>')
                
                html_parts.append('        </div>')
        
        # Close HTML
        html_parts.extend([
            '    </div>',
            '</body>',
            '</html>'
        ])
        
        return "\n".join(html_parts)
    
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
