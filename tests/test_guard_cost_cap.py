#!/usr/bin/env python3
"""
Tests for Cost Cap CLI Flag in Guard Command
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import guard


class TestCostCapFlag:
    """Test --cost-cap flag functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        
        # Sample logs with known costs
        self.logs_content = """{"model": "gpt-4", "cost_usd": 0.50, "tokens": 1000}
{"model": "gpt-4", "cost_usd": 0.30, "tokens": 600}
{"model": "gpt-3.5-turbo", "cost_usd": 0.10, "tokens": 200}
{"model": "gpt-3.5-turbo", "cost_usd": 0.15, "tokens": 300}
"""
        # Total cost: 0.50 + 0.30 + 0.10 + 0.15 = 1.05
        
        # Simple rules file
        self.rules_content = """version: 1
rules:
  - id: test_rule
    description: Test rule
    if:
      model: gpt-4
    severity: warn
"""
    
    def test_cost_cap_flag_in_help(self):
        """--cost-cap flag appears in help text"""
        result = self.runner.invoke(guard, ['--help'])
        
        assert '--cost-cap' in result.output
        assert 'Maximum allowed total cost' in result.output
    
    def test_cost_cap_not_exceeded(self):
        """Cost cap not exceeded, no violation"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap higher than total (1.05 < 2.00)
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '2.00'
            ])
            
            # Should not fail
            assert result.exit_code == 0
            
            # Should show cost cap status
            assert 'Cost Cap:' in result.output
            assert 'remaining' in result.output
    
    def test_cost_cap_exceeded(self):
        """Cost cap exceeded, violation triggered"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap lower than total (1.05 > 0.50)
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '0.50',
                '--fail-on-violations'
            ])
            
            # Should fail with cost cap exceeded
            assert result.exit_code == 1
            
            # Should show cost cap exceeded message
            assert 'COST CAP EXCEEDED' in result.output
            assert 'over by' in result.output
    
    def test_cost_cap_exact_match(self):
        """Cost exactly equals cap (no violation)"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap exactly equal to total (1.05 == 1.05)
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '1.05'
            ])
            
            # Should not fail (equal is OK)
            assert result.exit_code == 0
            
            # Should show $0.00 remaining
            assert 'Cost Cap:' in result.output
    
    def test_cost_cap_just_under(self):
        """Cost just under cap (no violation)"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap just above total (1.05 < 1.10)
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '1.10'
            ])
            
            # Should not fail
            assert result.exit_code == 0
            
            # Should show small amount remaining
            assert '$0.05' in result.output or '$0.0500' in result.output
    
    def test_cost_cap_json_output(self):
        """Cost cap info included in JSON output"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with JSON output
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '0.50',
                '--output', 'json'
            ])
            
            import json
            output_json = json.loads(result.output)
            
            # Check summary includes cost cap info
            assert 'total_cost' in output_json['summary']
            assert 'cost_cap' in output_json['summary']
            assert 'cost_cap_exceeded' in output_json['summary']
            assert output_json['summary']['cost_cap'] == 0.50
            assert output_json['summary']['cost_cap_exceeded'] is True
    
    def test_cost_cap_synthetic_violation(self):
        """Cost cap creates synthetic violation rule"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap exceeded
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '0.50',
                '--output', 'json'
            ])
            
            import json
            output_json = json.loads(result.output)
            
            # Should have cost_cap_exceeded rule
            assert 'cost_cap_exceeded' in output_json['rules']
            assert output_json['rules']['cost_cap_exceeded']['count'] > 0
            assert output_json['rules']['cost_cap_exceeded']['severity'] == 'fatal'
    
    def test_no_cost_cap_no_tracking(self):
        """Without --cost-cap, no cost tracking"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run without cost cap
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--output', 'json'
            ])
            
            import json
            output_json = json.loads(result.output)
            
            # Summary should have None for cost cap fields
            assert output_json['summary']['total_cost'] is None
            assert output_json['summary']['cost_cap'] is None
            assert output_json['summary']['cost_cap_exceeded'] is False
    
    def test_cost_cap_zero_logs(self):
        """Cost cap with empty logs"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text("")  # Empty
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with cost cap
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '1.00'
            ])
            
            # Should show $0.00 / $1.00
            assert result.exit_code == 0
            assert '$0.00' in result.output or '$0.0000' in result.output
    
    def test_cost_cap_markdown_output(self):
        """Cost cap displayed in markdown output"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with markdown output
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '0.50',
                '--output', 'md'
            ])
            
            # Should show cost cap in markdown
            assert 'COST CAP EXCEEDED' in result.output or 'Cost Cap' in result.output
    
    def test_cost_cap_html_output(self):
        """Cost cap displayed in HTML output"""
        with self.runner.isolated_filesystem():
            # Create files
            log_file = Path('logs.jsonl')
            log_file.write_text(self.logs_content)
            
            rules_file = Path('rules.yaml')
            rules_file.write_text(self.rules_content)
            
            # Run with HTML output
            result = self.runner.invoke(guard, [
                'logs.jsonl',
                '--rules', 'rules.yaml',
                '--cost-cap', '0.50',
                '--output', 'html'
            ])
            
            # HTML should include cost cap info
            assert 'cost' in result.output.lower()
