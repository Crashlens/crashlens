#!/usr/bin/env python3
"""
Unit tests for HTML formatter with --summary-only support (Step 8)
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import format_html_report, guard


class TestHTMLFormatter:
    """Test HTML formatter functionality."""
    
    def test_format_html_basic(self):
        """HTML formatter generates valid HTML."""
        report = {
            'summary': {'violations': 1},
            'rules': {
                'TEST_001': {
                    'description': 'Test rule',
                    'severity': 'error',
                    'count': 1,
                    'examples': [
                        {'model': 'gpt-4', 'tokens': 1000}
                    ]
                }
            }
        }
        
        html = format_html_report(report, 'logs.jsonl')
        
        assert '<!DOCTYPE html>' in html
        assert 'CrashLens Guard Report' in html
        assert 'TEST_001' in html
        assert 'Test rule' in html
    
    def test_format_html_summary_only(self):
        """Summary-only mode omits examples."""
        report = {
            'summary': {'violations': 1},
            'rules': {
                'TEST_001': {
                    'description': 'Test rule',
                    'severity': 'error',
                    'count': 1,
                    'examples': [
                        {'model': 'gpt-4', 'tokens': 1000, 'prompt': 'sensitive data'}
                    ]
                }
            }
        }
        
        html_full = format_html_report(report, 'logs.jsonl', summary_only=False)
        html_summary = format_html_report(report, 'logs.jsonl', summary_only=True)
        
        # Full report should have examples
        assert 'Example Violations' in html_full
        assert 'gpt-4' in html_full
        
        # Summary-only should NOT have examples
        assert 'Example Violations' not in html_summary
        assert 'gpt-4' not in html_summary
    
    def test_format_html_no_violations(self):
        """HTML formatter handles zero violations."""
        report = {
            'summary': {'violations': 0},
            'rules': {
                'TEST_001': {
                    'description': 'Test rule',
                    'severity': 'error',
                    'count': 0,
                    'examples': []
                }
            }
        }
        
        html = format_html_report(report, 'logs.jsonl')
        
        assert 'No violations detected' in html
        assert '✅' in html


class TestGuardHTMLOutput:
    """Test guard command with HTML output."""
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample logs."""
        logs_file = tmp_path / "logs.jsonl"
        logs_content = """{"traceId": "t1", "model": "gpt-4", "tokens": 1500}
{"traceId": "t2", "model": "gpt-3.5", "tokens": 500}
"""
        logs_file.write_text(logs_content)
        return logs_file
    
    @pytest.fixture
    def simple_rules(self, tmp_path):
        """Create simple rules file."""
        rules_file = tmp_path / "rules.yaml"
        rules_content = """
rules:
  - id: HTML_001
    description: "Test rule"
    if:
      if_model: "gpt-4"
    action: warn
    severity: warn
"""
        rules_file.write_text(rules_content)
        return rules_file
    
    def test_guard_html_output(self, tmp_path, sample_logs, simple_rules):
        """Guard generates HTML output."""
        runner = CliRunner()
        
        result = runner.invoke(guard, [
            str(sample_logs),
            '--rules', str(simple_rules),
            '--output', 'html'
        ])
        
        assert result.exit_code in [0, 1]
        assert '<!DOCTYPE html>' in result.output
        assert 'CrashLens Guard Report' in result.output
        assert 'HTML_001' in result.output
    
    def test_guard_html_summary_only_param(self, tmp_path, sample_logs, simple_rules):
        """HTML formatter respects summary_only parameter."""
        runner = CliRunner()
        
        # Call guard without --summary-only flag (which overrides format)
        result = runner.invoke(guard, [
            str(sample_logs),
            '--rules', str(simple_rules),
            '--output', 'html'
        ])
        
        assert result.exit_code in [0, 1]
        assert '<!DOCTYPE html>' in result.output
        
        # Verify HTML formatter itself supports summary_only parameter
        from crashlens.guard import format_html_report
        report = {
            'summary': {'violations': 1},
            'rules': {
                'TEST': {
                    'description': 'Test',
                    'severity': 'warn',
                    'count': 1,
                    'examples': [{'model': 'gpt-4'}]
                }
            }
        }
        html_summary = format_html_report(report, 'logs.jsonl', summary_only=True)
        assert 'Example Violations' not in html_summary


class TestHTMLEscaping:
    """Test HTML special character escaping."""
    
    def test_escapes_special_chars(self):
        """HTML formatter escapes special characters."""
        report = {
            'summary': {'violations': 1},
            'rules': {
                'TEST<script>': {
                    'description': 'Test & rule',
                    'severity': 'error',
                    'count': 1,
                    'examples': [
                        {'model': '<gpt-4>', 'prompt': 'Test & test'}
                    ]
                }
            }
        }
        
        html = format_html_report(report, 'logs.jsonl')
        
        # Should escape < > &
        assert '<script>' not in html
        assert '&lt;script&gt;' in html or 'TEST&' in html  # Escaped form
        assert '<gpt-4>' not in html
        assert '&lt;gpt-4&gt;' in html or '&lt;' in html
