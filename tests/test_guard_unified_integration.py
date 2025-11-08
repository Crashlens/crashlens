"""
Tests for Step 4 Phase 2: Guard.py Integration with GuardPolicyEngineAdapter

This test suite verifies that the unified engine is properly wired into
the guard() CLI command when CRASHLENS_USE_UNIFIED_ENGINE=1.
"""

import json
import os
import sys
from pathlib import Path
from typing import List
import tempfile
import pytest
from click.testing import CliRunner

from typing import List, Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.cli import cli


def parse_json_from_output(output: str) -> Optional[dict]:
    """Parse multi-line JSON from command output."""
    output_lines = output.strip().split('\n')
    
    # Find the JSON block (starts with { and may span multiple lines)
    # Need to track brace depth to find the matching closing brace
    json_start_idx = None
    brace_depth = 0
    
    for i, line in enumerate(output_lines):
        if line.strip() == '{' and json_start_idx is None:
            json_start_idx = i
            brace_depth = 1
        elif json_start_idx is not None:
            # Count braces
            brace_depth += line.count('{') - line.count('}')
            if brace_depth == 0:
                # Found the matching closing brace
                json_end_idx = i + 1
                json_text = '\n'.join(output_lines[json_start_idx:json_end_idx])
                return json.loads(json_text)
    
    return None


class TestGuardUnifiedIntegration:
    """Test guard() function with unified engine enabled/disabled"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample rules.yaml
        self.rules_file = Path(self.temp_dir) / "rules.yaml"
        self.rules_file.write_text("""
rules:
  - id: high_cost_test
    description: "Test rule for high cost"
    if:
      cost_usd:
        ">": 0.01
    action: error
    severity: error
    suggestion: "Reduce model usage"
  
  - id: retry_test
    description: "Test rule for retries"
    if:
      retry_count:
        ">": 2
    action: warn
    severity: warn
    suggestion: "Implement backoff"
""")
        
        # Create sample log file with violations
        self.log_file = Path(self.temp_dir) / "test.jsonl"
        self.log_file.write_text("""
{"traceId": "trace1", "model": "gpt-4", "cost_usd": 0.05, "retry_count": 1, "prompt": "test"}
{"traceId": "trace2", "model": "gpt-3.5-turbo", "cost_usd": 0.001, "retry_count": 5, "prompt": "test"}
{"traceId": "trace3", "model": "gpt-4", "cost_usd": 0.02, "retry_count": 0, "prompt": "test"}
""".strip())
        
        # Create clean log file (no violations)
        self.clean_log_file = Path(self.temp_dir) / "clean.jsonl"
        self.clean_log_file.write_text("""
{"traceId": "trace1", "model": "gpt-3.5-turbo", "cost_usd": 0.001, "retry_count": 1, "prompt": "test"}
{"traceId": "trace2", "model": "gpt-3.5-turbo", "cost_usd": 0.002, "retry_count": 0, "prompt": "test"}
""".strip())
    
    def teardown_method(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_guard_legacy_mode_default(self):
        """Test that guard uses legacy mode by default (USE_UNIFIED_ENGINE=0)"""
        # Ensure feature flag is disabled
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '0'
        
        result = self.runner.invoke(
            cli,
            ['guard', str(self.log_file), '--rules', str(self.rules_file), '--output', 'json'],
            env=env
        )
        
        # Should succeed (violations found)
        assert result.exit_code == 0
        
        # Should NOT contain unified engine message
        assert '🔧 Using unified PolicyEngine' not in result.output
        assert 'CRASHLENS_USE_UNIFIED_ENGINE=1' not in result.output
        
        # Parse JSON output to verify violations detected
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None, "No JSON output found"
        assert 'rules' in json_output
        assert 'high_cost_test' in json_output['rules']
        assert json_output['rules']['high_cost_test']['count'] > 0
    
    def test_guard_unified_mode_enabled(self):
        """Test that guard uses unified engine when USE_UNIFIED_ENGINE=1"""
        # Enable feature flag
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            ['guard', str(self.log_file), '--rules', str(self.rules_file), '--output', 'json'],
            env=env,
            catch_exceptions=False
        )
        
        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"
        
        # Should contain unified engine message
        assert '🔧 Using unified PolicyEngine' in result.output or '🔧 Using unified PolicyEngine' in result.stderr
        
        # Parse JSON output to verify violations detected
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None, "No JSON output found"
        assert 'rules' in json_output
        assert 'high_cost_test' in json_output['rules']
        assert json_output['rules']['high_cost_test']['count'] > 0
    
    def test_guard_unified_mode_with_suppressions(self):
        """Test that suppressions work correctly in unified mode"""
        # Enable feature flag
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.log_file),
                '--rules', str(self.rules_file),
                '--suppress', 'high_cost_test',
                '--output', 'json'
            ],
            env=env,
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        
        # Parse JSON output
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None
        
        # high_cost_test should be suppressed (count = 0 or not present)
        if 'high_cost_test' in json_output['rules']:
            assert json_output['rules']['high_cost_test']['count'] == 0
        
        # retry_test should still be detected
        assert 'retry_test' in json_output['rules']
        assert json_output['rules']['retry_test']['count'] > 0
    
    def test_guard_unified_mode_pii_stripping(self):
        """Test that PII stripping works in unified mode"""
        # Create log with PII
        pii_log = Path(self.temp_dir) / "pii.jsonl"
        pii_log.write_text("""
{"traceId": "trace1", "model": "gpt-4", "cost_usd": 0.05, "prompt": "Email: test@example.com"}
""".strip())
        
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(pii_log),
                '--rules', str(self.rules_file),
                '--strip-pii',
                '--output', 'json'
            ],
            env=env,
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        
        # Parse JSON output
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None
        
        # Check that PII is redacted in examples
        if 'high_cost_test' in json_output['rules']:
            examples = json_output['rules']['high_cost_test'].get('examples', [])
            for example in examples:
                if 'prompt' in example:
                    assert 'test@example.com' not in example['prompt']
                    assert '[REDACTED-EMAIL]' in example['prompt']
    
    def test_guard_unified_mode_no_content(self):
        """Test that --no-content flag works in unified mode"""
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.log_file),
                '--rules', str(self.rules_file),
                '--no-content',
                '--output', 'json'
            ],
            env=env,
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        
        # Parse JSON output
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None
        
        # Examples should be empty
        for rule_id, rule_data in json_output['rules'].items():
            assert rule_data.get('examples', []) == []
    
    def test_guard_unified_mode_fail_on_violations(self):
        """Test that --fail-on-violations works in unified mode"""
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        # Should fail on violations
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.log_file),
                '--rules', str(self.rules_file),
                '--fail-on-violations',
                '--output', 'json'
            ],
            env=env,
            catch_exceptions=False
        )
        
        # Should exit with code 1 (violations found)
        assert result.exit_code == 1
    
    def test_guard_unified_mode_clean_logs(self):
        """Test that clean logs produce no violations in unified mode"""
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.clean_log_file),
                '--rules', str(self.rules_file),
                '--output', 'json'
            ],
            env=env,
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        
        # Parse JSON output
        json_output = parse_json_from_output(result.output)
        
        assert json_output is not None
        assert json_output['summary']['violations'] == 0
    
    def test_guard_unified_vs_legacy_equivalence(self):
        """Test that unified and legacy modes produce equivalent results"""
        # Run with legacy mode
        env_legacy = os.environ.copy()
        env_legacy['CRASHLENS_USE_UNIFIED_ENGINE'] = '0'
        
        result_legacy = self.runner.invoke(
            cli,
            ['guard', str(self.log_file), '--rules', str(self.rules_file), '--output', 'json'],
            env=env_legacy,
            catch_exceptions=False
        )
        
        # Run with unified mode
        env_unified = os.environ.copy()
        env_unified['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result_unified = self.runner.invoke(
            cli,
            ['guard', str(self.log_file), '--rules', str(self.rules_file), '--output', 'json'],
            env=env_unified,
            catch_exceptions=False
        )
        
        assert result_legacy.exit_code == 0
        assert result_unified.exit_code == 0
        
        # Parse both outputs using the module-level helper
        json_legacy = parse_json_from_output(result_legacy.output)
        json_unified = parse_json_from_output(result_unified.output)
        
        assert json_legacy is not None
        assert json_unified is not None
        
        # Compare violation counts (should be identical)
        for rule_id in json_legacy['rules']:
            assert rule_id in json_unified['rules'], f"Rule {rule_id} missing in unified output"
            assert json_legacy['rules'][rule_id]['count'] == json_unified['rules'][rule_id]['count'], \
                f"Count mismatch for rule {rule_id}"
    
    def test_guard_unified_mode_markdown_output(self):
        """Test that markdown output works in unified mode"""
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.log_file),
                '--rules', str(self.rules_file),
                '--output', 'md'
            ],
            env=env,
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert '# CrashLens Guard Report' in result.output or 'Guard Report' in result.output
    
    def test_guard_unified_mode_error_handling(self):
        """Test error handling in unified mode"""
        # Create malformed rules file
        bad_rules = Path(self.temp_dir) / "bad_rules.yaml"
        bad_rules.write_text("invalid: yaml: content: [[[")
        
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        result = self.runner.invoke(
            cli,
            [
                'guard', str(self.log_file),
                '--rules', str(bad_rules),
                '--output', 'json'
            ],
            env=env
        )
        
        # Should fail gracefully
        assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
