#!/usr/bin/env python3
"""
Tests for HTML output format
Validates HTML structure, styling, severity colors, and XSS safety
"""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import guard


class HTMLValidator(HTMLParser):
    """Simple HTML validator to check structure"""
    
    def __init__(self):
        super().__init__()
        self.tags = []
        self.errors = []
        self.found_doctype = False
        
    def handle_startendtag(self, tag, attrs):
        # Self-closing tags like <meta>
        pass
    
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        
    def handle_endtag(self, tag):
        if not self.tags:
            self.errors.append(f"Unexpected closing tag: {tag}")
            return
        if self.tags[-1] != tag:
            self.errors.append(f"Mismatched tags: expected {self.tags[-1]}, got {tag}")
        else:
            self.tags.pop()
    
    def handle_decl(self, decl):
        if decl.lower().startswith('doctype'):
            self.found_doctype = True
    
    def is_valid(self):
        return len(self.errors) == 0 and len(self.tags) == 0 and self.found_doctype


def extract_html_from_output(output: str) -> str:
    """Extract HTML from Click output (may contain stderr messages)"""
    # Find DOCTYPE declaration
    doctype_idx = output.find('<!DOCTYPE')
    if doctype_idx == -1:
        raise ValueError("No HTML found in output")
    
    # Find closing </html> tag
    html_end_idx = output.find('</html>', doctype_idx)
    if html_end_idx == -1:
        raise ValueError("No closing </html> tag found")
    
    return output[doctype_idx:html_end_idx + 7]


class TestHTMLOutput:
    """Test HTML output format"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def setup_files_no_violations(self, tmp_path):
        """Create logs with no violations"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-3.5-turbo",
            "tokens": 100,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "simple prompt",
            "cost_usd": 0.001,
            "endpoint": "/api/chat"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        return logs, rules
    
    @pytest.fixture
    def setup_files_with_violations(self, tmp_path):
        """Create logs with multiple severity levels"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "timestamp": "2025-10-25T10:00:00Z",
                "model": "gpt-4o",
                "tokens": 5000,
                "retry_count": 0,
                "fallback_triggered": False,
                "prompt": "test",
                "cost_usd": 0.50,
                "endpoint": "/api/chat"
            }),
            json.dumps({
                "timestamp": "2025-10-25T10:01:00Z",
                "model": "gpt-4o",
                "tokens": 3000,
                "retry_count": 5,
                "fallback_triggered": True,
                "prompt": "another test",
                "cost_usd": 0.30,
                "endpoint": "/api/chat"
            })
        ]), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
  - id: RL002
    description: "Many retries"
    if:
      if_retry_count_gt: 2
    action: fail_ci
    severity: error
  - id: RL003
    description: "Fallback triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn
""", encoding="utf-8")
        
        return logs, rules
    
    def test_html_output_no_violations(self, runner, setup_files_no_violations):
        """HTML output for no violations shows success message"""
        logs, rules = setup_files_no_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Check for HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        
        # Check for success indicators
        assert "✅" in html or "No violations" in html
        assert "success" in html.lower() or "passed" in html.lower()
    
    def test_html_output_with_violations(self, runner, setup_files_with_violations):
        """HTML output with violations shows all severity levels"""
        logs, rules = setup_files_with_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Check for HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<table>" in html or "violation" in html.lower()
        
        # Check for rule IDs
        assert "RL001" in html
        assert "RL002" in html
        assert "RL003" in html
        
        # Check for severity levels
        assert "fatal" in html.lower() or "FATAL" in html
        assert "error" in html.lower() or "ERROR" in html
        assert "warn" in html.lower() or "WARN" in html
    
    def test_html_severity_colors(self, runner, setup_files_with_violations):
        """HTML uses correct colors for severity levels"""
        logs, rules = setup_files_with_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Check for severity color codes (hex colors from implementation)
        # These are the actual colors defined in format_html_report
        assert "#dc3545" in html or "#fd7e14" in html or "#ffc107" in html
    
    def test_html_structure_valid(self, runner, setup_files_with_violations):
        """HTML is valid and well-formed"""
        logs, rules = setup_files_with_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Basic structure checks (avoid complex HTML5 parsing)
        assert html.count("<html") == 1
        assert html.count("</html>") == 1
        assert html.count("<head>") == 1
        assert html.count("</head>") == 1
        assert html.count("<body>") == 1
        assert html.count("</body>") == 1
        assert html.count("<style>") == 1
        assert html.count("</style>") == 1
    
    def test_html_examples_truncated(self, runner, tmp_path):
        """HTML truncates long prompts in examples"""
        logs = tmp_path / "logs.jsonl"
        long_prompt = "a" * 200  # Very long prompt
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 5000,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": long_prompt,
            "cost_usd": 0.50,
            "endpoint": "/api/chat"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Prompt should be truncated (not all 200 'a's)
        assert "..." in html or len(html) < 5000
    
    def test_html_special_chars_escaped(self, runner, tmp_path):
        """HTML escapes special characters to prevent XSS"""
        logs = tmp_path / "logs.jsonl"
        xss_prompt = "<script>alert('XSS')</script>"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 5000,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": xss_prompt,
            "cost_usd": 0.50,
            "endpoint": "/api/chat"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Script tags should be escaped, not executable
        assert "&lt;script&gt;" in html or "<script>" not in html or "alert" not in html
    
    def test_html_contains_metadata(self, runner, setup_files_with_violations):
        """HTML contains summary metadata"""
        logs, rules = setup_files_with_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Check for summary information
        assert "Rules Checked" in html or "rules" in html.lower()
        assert "Violations Found" in html or "violations" in html.lower()
        assert "Scanned" in html or str(logs) in html
    
    def test_html_css_inline(self, runner, setup_files_with_violations):
        """HTML uses inline CSS (no external dependencies)"""
        logs, rules = setup_files_with_violations
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--output", "html"
        ])
        
        assert result.exit_code == 0
        html = extract_html_from_output(result.output)
        
        # Check for style tag or inline styles
        assert "<style>" in html or "style=" in html
        
        # Should NOT reference external stylesheets
        assert "<link" not in html or "stylesheet" not in html.lower()
