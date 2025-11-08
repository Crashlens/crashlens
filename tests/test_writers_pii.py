"""
Tests for CrashLens Writers - PII Handling and Format Consistency

Validates that all writers (JSON, Markdown, HTML, Text) consistently handle:
- PII scrubbing with --strip-pii flag
- Content removal with --no-content flag
- Proper formatting of violation reports
"""

import json
import re
from typing import Any, Dict

import pytest

from crashlens.writers import HTMLWriter, JSONWriter, MarkdownWriter, TextWriter


class TestWritersPIIHandling:
    """Test PII scrubbing consistency across all writers"""
    
    @pytest.fixture
    def sample_report_with_pii(self) -> Dict[str, Any]:
        """Create a sample report with PII in prompts"""
        return {
            "summary": {
                "violations": 2,
                "total_logs": 10
            },
            "rules": {
                "excessive_retries": {
                    "severity": "high",
                    "description": "Too many retry attempts",
                    "count": 2,
                    "examples": [
                        {
                            "timestamp": "2025-01-15T10:30:00Z",
                            "model": "gpt-4",
                            "tokens": 1500,
                            "retry_count": 5,
                            "fallback_triggered": True,
                            "endpoint": "https://api.openai.com/v1/chat/completions",
                            "prompt": "Send invoice to john.doe@example.com or call 555-123-4567"
                        },
                        {
                            "timestamp": "2025-01-15T10:35:00Z",
                            "model": "gpt-3.5-turbo",
                            "tokens": 800,
                            "retry_count": 4,
                            "fallback_triggered": False,
                            "endpoint": "https://api.openai.com/v1/chat/completions",
                            "prompt": "Credit card 4532-1234-5678-9010 and SSN 123-45-6789"
                        }
                    ]
                }
            }
        }
    
    @pytest.fixture
    def sample_report_no_violations(self) -> Dict[str, Any]:
        """Create a sample report with no violations"""
        return {
            "summary": {
                "violations": 0,
                "total_logs": 10
            },
            "rules": {
                "excessive_retries": {
                    "severity": "high",
                    "description": "Too many retry attempts",
                    "count": 0,
                    "examples": []
                }
            }
        }
    
    def test_json_writer_strips_pii(self, sample_report_with_pii):
        """JSON writer should redact PII when strip_pii=True"""
        writer = JSONWriter(strip_pii=True, no_content=False)
        output = writer.format(sample_report_with_pii)
        
        # Parse JSON output
        report = json.loads(output)
        
        # Check that email is redacted
        assert "john.doe@example.com" not in output
        assert "[EMAIL]" in output
        
        # Check that phone is redacted
        assert "555-123-4567" not in output
        assert "[PHONE]" in output
        
        # Check that SSN is redacted
        assert "123-45-6789" not in output
        assert "[SSN]" in output
        
        # Check that credit card is redacted
        assert "4532-1234-5678-9010" not in output
        assert "[CARD]" in output
    
    def test_json_writer_preserves_pii_when_disabled(self, sample_report_with_pii):
        """JSON writer should preserve PII when strip_pii=False"""
        writer = JSONWriter(strip_pii=False, no_content=False)
        output = writer.format(sample_report_with_pii)
        
        # Check that PII is preserved
        assert "john.doe@example.com" in output
        assert "555-123-4567" in output
        assert "123-45-6789" in output
        assert "4532-1234-5678-9010" in output
    
    def test_json_writer_no_content(self, sample_report_with_pii):
        """JSON writer should remove examples when no_content=True"""
        writer = JSONWriter(strip_pii=False, no_content=True)
        output = writer.format(sample_report_with_pii)
        
        # Parse JSON output
        report = json.loads(output)
        
        # Examples should be empty
        assert len(report["rules"]["excessive_retries"]["examples"]) == 0
        
        # Summary should still be present
        assert report["summary"]["violations"] == 2
    
    def test_markdown_writer_strips_pii(self, sample_report_with_pii):
        """Markdown writer should redact PII when strip_pii=True"""
        writer = MarkdownWriter(strip_pii=True, no_content=False)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Check that email is redacted
        assert "john.doe@example.com" not in output
        assert "[EMAIL]" in output
        
        # Check that phone is redacted
        assert "555-123-4567" not in output
        assert "[PHONE]" in output
        
        # Check that SSN is redacted
        assert "123-45-6789" not in output
        assert "[SSN]" in output
        
        # Check that credit card is redacted
        assert "4532-1234-5678-9010" not in output
        assert "[CARD]" in output
    
    def test_markdown_writer_no_content(self, sample_report_with_pii):
        """Markdown writer should omit examples when no_content=True"""
        writer = MarkdownWriter(strip_pii=False, no_content=True)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Examples section should not be present
        assert "**Example Violations**:" not in output
        
        # But violation count should still be shown
        assert "**Violation Count**: 2" in output
    
    def test_html_writer_strips_pii(self, sample_report_with_pii):
        """HTML writer should redact PII when strip_pii=True"""
        writer = HTMLWriter(strip_pii=True, no_content=False)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Check that email is redacted (HTML escaped)
        assert "john.doe@example.com" not in output
        assert "[EMAIL]" in output
        
        # Check that phone is redacted
        assert "555-123-4567" not in output
        assert "[PHONE]" in output
        
        # Check that SSN is redacted
        assert "123-45-6789" not in output
        assert "[SSN]" in output
        
        # Check that credit card is redacted
        assert "4532-1234-5678-9010" not in output
        assert "[CARD]" in output
    
    def test_html_writer_no_content(self, sample_report_with_pii):
        """HTML writer should omit examples when no_content=True"""
        writer = HTMLWriter(strip_pii=False, no_content=True)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Examples section should not be present
        assert "Example Violations:" not in output
        
        # But violation count should still be shown
        assert "Violation Count:" in output
        assert "2</span>" in output
    
    def test_html_writer_summary_only(self, sample_report_with_pii):
        """HTML writer should omit examples when summary_only=True"""
        writer = HTMLWriter(strip_pii=False, no_content=False)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl", summary_only=True)
        
        # Examples section should not be present
        assert "Example Violations:" not in output
        
        # Summary should still be shown
        assert "Violations Found:" in output
    
    def test_text_writer_strips_pii(self, sample_report_with_pii):
        """Text writer should redact PII when strip_pii=True"""
        writer = TextWriter(strip_pii=True, no_content=False)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Check that email is redacted
        assert "john.doe@example.com" not in output
        assert "[EMAIL]" in output
        
        # Check that phone is redacted
        assert "555-123-4567" not in output
        assert "[PHONE]" in output
        
        # Check that SSN is redacted
        assert "123-45-6789" not in output
        assert "[SSN]" in output
        
        # Check that credit card is redacted
        assert "4532-1234-5678-9010" not in output
        assert "[CARD]" in output
    
    def test_text_writer_no_content(self, sample_report_with_pii):
        """Text writer should omit examples when no_content=True"""
        writer = TextWriter(strip_pii=False, no_content=True)
        output = writer.format(sample_report_with_pii, "test-logs.jsonl")
        
        # Examples section should not be present
        assert "Examples:" not in output
        
        # But violation count should still be shown
        assert "Violation Count: 2" in output


class TestWritersFormatConsistency:
    """Test that all writers produce consistent structural output"""
    
    @pytest.fixture
    def sample_report(self) -> Dict[str, Any]:
        """Create a simple sample report"""
        return {
            "summary": {
                "violations": 1,
                "total_logs": 5
            },
            "rules": {
                "test_rule": {
                    "severity": "medium",
                    "description": "Test rule description",
                    "count": 1,
                    "examples": [
                        {
                            "timestamp": "2025-01-15T10:30:00Z",
                            "model": "gpt-4",
                            "tokens": 1000,
                            "retry_count": 2,
                            "fallback_triggered": False,
                            "endpoint": "https://api.example.com",
                            "prompt": "Test prompt"
                        }
                    ]
                }
            }
        }
    
    def test_all_writers_handle_no_violations(self, sample_report):
        """All writers should handle zero violations gracefully"""
        no_violations_report = {
            "summary": {"violations": 0, "total_logs": 5},
            "rules": {"test_rule": {"severity": "low", "description": "Test", "count": 0, "examples": []}}
        }
        
        json_writer = JSONWriter()
        json_output = json_writer.format(no_violations_report)
        assert "0" in json_output
        
        md_writer = MarkdownWriter()
        md_output = md_writer.format(no_violations_report, "test.jsonl")
        assert "No violations detected" in md_output or "Violations Found**: 0" in md_output
        
        html_writer = HTMLWriter()
        html_output = html_writer.format(no_violations_report, "test.jsonl")
        assert "No violations detected" in html_output or "0</span>" in html_output
        
        text_writer = TextWriter()
        text_output = text_writer.format(no_violations_report, "test.jsonl")
        assert "No violations detected" in text_output or "Violations Found: 0" in text_output
    
    def test_all_writers_include_metadata(self, sample_report):
        """All writers should include basic metadata"""
        logfile = "test-logs.jsonl"
        
        json_writer = JSONWriter()
        json_output = json_writer.format(sample_report)
        json_data = json.loads(json_output)
        assert json_data["summary"]["violations"] == 1
        
        md_writer = MarkdownWriter()
        md_output = md_writer.format(sample_report, logfile)
        assert logfile in md_output
        assert "Violations Found" in md_output
        
        html_writer = HTMLWriter()
        html_output = html_writer.format(sample_report, logfile)
        assert logfile in html_output
        assert "Violations Found" in html_output
        
        text_writer = TextWriter()
        text_output = text_writer.format(sample_report, logfile)
        assert logfile in text_output
        assert "Violations Found" in text_output
    
    def test_all_writers_show_severity(self, sample_report):
        """All writers should display severity information"""
        json_writer = JSONWriter()
        json_output = json_writer.format(sample_report)
        assert "medium" in json_output
        
        md_writer = MarkdownWriter()
        md_output = md_writer.format(sample_report, "test.jsonl")
        assert "medium" in md_output.lower()
        
        html_writer = HTMLWriter()
        html_output = html_writer.format(sample_report, "test.jsonl")
        assert "medium" in html_output.lower()
        
        text_writer = TextWriter()
        text_output = text_writer.format(sample_report, "test.jsonl")
        assert "MEDIUM" in text_output


class TestWritersEdgeCases:
    """Test edge cases and error handling"""
    
    def test_json_writer_empty_examples(self):
        """JSON writer should handle empty examples list"""
        report = {
            "summary": {"violations": 1, "total_logs": 1},
            "rules": {"rule1": {"severity": "low", "description": "Test", "count": 1, "examples": []}}
        }
        
        writer = JSONWriter(strip_pii=True)
        output = writer.format(report)
        
        # Should not crash
        assert "rule1" in output
    
    def test_markdown_writer_missing_fields(self):
        """Markdown writer should handle missing optional fields"""
        report = {
            "summary": {"violations": 1, "total_logs": 1},
            "rules": {
                "rule1": {
                    "severity": "low",
                    "description": "Test",
                    "count": 1,
                    "examples": [
                        {
                            "timestamp": "2025-01-15T10:30:00Z",
                            # Missing model, tokens, etc.
                        }
                    ]
                }
            }
        }
        
        writer = MarkdownWriter()
        output = writer.format(report, "test.jsonl")
        
        # Should handle N/A gracefully
        assert "N/A" in output
    
    def test_html_writer_special_characters(self):
        """HTML writer should escape special HTML characters"""
        report = {
            "summary": {"violations": 1, "total_logs": 1},
            "rules": {
                "rule<script>": {
                    "severity": "high",
                    "description": "Test <b>description</b>",
                    "count": 1,
                    "examples": []
                }
            }
        }
        
        writer = HTMLWriter()
        output = writer.format(report, "test.jsonl")
        
        # Should escape HTML
        assert "&lt;script&gt;" in output or "script" not in output
        assert "&lt;b&gt;" in output or "<b>description</b>" not in output
    
    def test_text_writer_long_prompts(self):
        """Text writer should truncate long prompts"""
        long_prompt = "A" * 200
        report = {
            "summary": {"violations": 1, "total_logs": 1},
            "rules": {
                "rule1": {
                    "severity": "low",
                    "description": "Test",
                    "count": 1,
                    "examples": [
                        {
                            "timestamp": "2025-01-15T10:30:00Z",
                            "model": "gpt-4",
                            "tokens": 1000,
                            "prompt": long_prompt
                        }
                    ]
                }
            }
        }
        
        writer = TextWriter()
        output = writer.format(report, "test.jsonl")
        
        # Should truncate to 60 chars
        assert len(output.split("prompt=")[1].split("\n")[0].strip()) <= 70  # Allow some buffer
