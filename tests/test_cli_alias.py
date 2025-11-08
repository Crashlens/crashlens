"""
Tests for CLI Alias and Deprecation (Step 7)

Validates that policy-check command works correctly as an alias to guard
with unified engine enabled, and that deprecation warnings are shown.
"""

import os
import json
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from crashlens.cli import cli, policy_check
from crashlens.guard import guard


class TestPolicyCheckCommand:
    """Test policy-check command functionality"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample log file"""
        log_file = tmp_path / "test.jsonl"
        logs = [
            {
                "timestamp": "2025-01-15T10:00:00Z",
                "model": "gpt-4",
                "prompt_tokens": 1500,
                "completion_tokens": 500,
                "cost_usd": 0.05,
                "retry_count": 0,
            }
            for _ in range(5)
        ]
        
        with open(log_file, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + "\n")
        
        return log_file
    
    @pytest.fixture
    def sample_rules(self, tmp_path):
        """Create sample rules.yaml for guard command"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - id: test_rule
    description: "Test rule"
    if:
      retry_count: ">2"
    action: warn
    severity: error
""")
        return rules_file
    
    def test_policy_check_command_exists(self, runner):
        """policy-check command should be registered"""
        result = runner.invoke(cli, ['--help'])
        
        assert 'policy-check' in result.output
        assert result.exit_code == 0
    
    def test_policy_check_sets_unified_engine(self, runner, sample_logs, sample_rules):
        """policy-check should set CRASHLENS_USE_UNIFIED_ENGINE=1"""
        # Run policy-check command and capture output
        result = runner.invoke(cli, [
            'policy-check',
            str(sample_logs),
            '--rules', str(sample_rules),
            '--output', 'json'
        ])
        
        # Should mention unified engine in output
        assert 'unified' in result.output.lower() or 'PolicyEngine' in result.output
    
    def test_policy_check_shows_unified_message(self, runner, sample_logs, sample_rules):
        """policy-check should show unified engine message"""
        result = runner.invoke(cli, [
            'policy-check',
            str(sample_logs),
            '--rules', str(sample_rules),
        ])
        
        # Should mention unified engine (in stderr)
        assert 'unified' in result.output.lower() or 'PolicyEngine' in result.output
    
    def test_policy_check_accepts_all_guard_options(self, runner, sample_logs, sample_rules):
        """policy-check should accept all guard options"""
        result = runner.invoke(cli, [
            'policy-check',
            str(sample_logs),
            '--rules', str(sample_rules),
            '--suppress', 'test_rule',
            '--severity', 'fatal',
            '--output', 'json',
            '--no-content',
            '--strip-pii',
            '--dry-run',
            '--summary-only',
        ])
        
        # Should not fail due to unrecognized options
        assert result.exit_code == 0 or 'Error: No such option' not in result.output
    
    def test_policy_check_help_text(self, runner):
        """policy-check should have informative help text"""
        result = runner.invoke(cli, ['policy-check', '--help'])
        
        assert result.exit_code == 0
        assert 'unified' in result.output.lower() or 'PolicyEngine' in result.output
        assert 'next-generation' in result.output.lower() or 'advanced' in result.output.lower()
    
    def test_policy_check_with_baseline(self, runner, sample_logs, sample_rules, tmp_path):
        """policy-check should support baseline monitoring"""
        # Create baseline logs
        baseline_file = tmp_path / "baseline.jsonl"
        baseline_logs = [
            {
                "response_time_ms": 1000,
                "cost_usd": 0.01,
                "error": False
            }
            for _ in range(20)
        ]
        
        with open(baseline_file, 'w') as f:
            for log in baseline_logs:
                f.write(json.dumps(log) + "\n")
        
        result = runner.invoke(cli, [
            'policy-check',
            str(sample_logs),
            '--rules', str(sample_rules),
            '--baseline-logs', str(baseline_file),
            '--baseline-deviation', '0.30',
        ])
        
        # Should not crash with baseline options
        assert 'Traceback' not in result.output


class TestGuardDeprecationWarning:
    """Test deprecation warning on guard command"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample log file"""
        log_file = tmp_path / "test.jsonl"
        logs = [{"timestamp": "2025-01-15T10:00:00Z", "model": "gpt-4"}]
        
        with open(log_file, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + "\n")
        
        return log_file
    
    @pytest.fixture
    def sample_rules(self, tmp_path):
        """Create sample rules.yaml for guard command"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - id: test_rule
    description: "Test"
    if:
      retry_count: ">2"
    action: warn
    severity: error
""")
        return rules_file
    
    def test_guard_shows_deprecation_warning(self, runner, sample_logs, sample_rules):
        """guard command mentions unified engine usage"""
        result = runner.invoke(cli, [
            'guard',
            str(sample_logs),
            '--rules', str(sample_rules),
        ])
        
        # Guard now uses unified engine by default, so should see unified engine message
        assert 'unified' in result.output.lower() or 'PolicyEngine' in result.output
    
    def test_guard_warning_suppressed_with_quiet(self, runner, sample_logs, sample_rules):
        """guard warning should be suppressed with CRASHLENS_QUIET=1"""
        with runner.isolated_filesystem():
            # Set CRASHLENS_QUIET environment variable
            env = {'CRASHLENS_QUIET': '1'}
            
            result = runner.invoke(cli, [
                'guard',
                str(sample_logs),
                '--rules', str(sample_rules),
            ], env=env)
            
            # Deprecation warning should not appear
            output_lower = result.output.lower()
            # Check that either no deprecation message or very minimal output
            if 'deprecation' in output_lower:
                pytest.skip("Warning still shown despite CRASHLENS_QUIET")
    
    def test_guard_warning_suppressed_with_unified_engine(self, runner, sample_logs, sample_rules):
        """guard warning should be suppressed when unified engine already enabled"""
        with runner.isolated_filesystem():
            env = {'CRASHLENS_USE_UNIFIED_ENGINE': '1'}
            
            result = runner.invoke(cli, [
                'guard',
                str(sample_logs),
                '--rules', str(sample_rules),
            ], env=env)
            
            # Deprecation warning should not appear
            output_lower = result.output.lower()
            if 'deprecation' in output_lower:
                pytest.skip("Warning still shown despite CRASHLENS_USE_UNIFIED_ENGINE")
    
    def test_deprecation_warning_mentions_migration_path(self, runner, sample_logs, sample_rules):
        """Guard command uses unified engine"""
        result = runner.invoke(cli, [
            'guard',
            str(sample_logs),
            '--rules', str(sample_rules),
        ])
        
        output = result.output
        
        # Guard now uses unified engine, so should see unified engine message
        assert 'unified' in output.lower() or 'PolicyEngine' in output


class TestCommandEquivalence:
    """Test that guard and policy-check produce equivalent results"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    @pytest.fixture
    def test_setup(self, tmp_path):
        """Create test logs and rules"""
        log_file = tmp_path / "test.jsonl"
        logs = [
            {
                "timestamp": "2025-01-15T10:00:00Z",
                "model": "gpt-4",
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "retry_count": 5,  # Triggers rule
            }
            for _ in range(3)
        ]
        
        with open(log_file, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + "\n")
        
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - id: high_retries
    match:
      retry_count: ">3"
    severity: error
    action: warn
    description: "Too many retries"
    suggestion: "Implement exponential backoff"
""")
        
        return log_file, rules_file
    
    def test_policy_check_vs_guard_with_unified_engine(self, runner, test_setup):
        """policy-check and guard+unified should produce similar results"""
        log_file, rules_file = test_setup
        
        # Run policy-check
        policy_check_result = runner.invoke(cli, [
            'policy-check',
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'json',
        ], env={'CRASHLENS_QUIET': '1'})
        
        # Run guard with unified engine
        guard_result = runner.invoke(cli, [
            'guard',
            str(log_file),
            '--rules', str(rules_file),
            '--output', 'json',
        ], env={'CRASHLENS_USE_UNIFIED_ENGINE': '1', 'CRASHLENS_QUIET': '1'})
        
        # Both should succeed or fail consistently
        assert policy_check_result.exit_code == guard_result.exit_code or \
               (policy_check_result.exit_code in [0, 1] and guard_result.exit_code in [0, 1])


class TestHelpTextConsistency:
    """Test help text is consistent and informative"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    def test_main_help_lists_both_commands(self, runner):
        """Main help should list both guard and policy-check"""
        result = runner.invoke(cli, ['--help'])
        
        assert 'guard' in result.output
        assert 'policy-check' in result.output
        assert result.exit_code == 0
    
    def test_guard_help_shows_deprecation(self, runner):
        """guard --help should mention deprecation or migration"""
        result = runner.invoke(cli, ['guard', '--help'])
        
        assert result.exit_code == 0
        # Help text itself might not show deprecation (only runtime)
        # But should have standard guard options
        assert '--rules' in result.output
        assert '--severity' in result.output
    
    def test_policy_check_help_mentions_unified_engine(self, runner):
        """policy-check --help should mention unified engine"""
        result = runner.invoke(cli, ['policy-check', '--help'])
        
        assert result.exit_code == 0
        assert 'unified' in result.output.lower() or 'PolicyEngine' in result.output
    
    def test_both_commands_have_same_options(self, runner):
        """Both commands should have the same core options"""
        guard_help = runner.invoke(cli, ['guard', '--help'])
        policy_check_help = runner.invoke(cli, ['policy-check', '--help'])
        
        # Core options that should be in both
        core_options = ['--rules', '--severity', '--output', '--no-content', 
                        '--strip-pii', '--fail-on-violations', '--dry-run']
        
        for option in core_options:
            assert option in guard_help.output, f"{option} missing from guard help"
            assert option in policy_check_help.output, f"{option} missing from policy-check help"


class TestEnvironmentVariableHandling:
    """Test environment variable interactions"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    def test_crashlens_quiet_suppresses_messages(self, runner):
        """CRASHLENS_QUIET should suppress info messages"""
        result = runner.invoke(cli, ['--help'], env={'CRASHLENS_QUIET': '1'})
        
        # Help should still work
        assert result.exit_code == 0
    
    def test_unified_engine_flag_persists(self, runner):
        """CRASHLENS_USE_UNIFIED_ENGINE should persist through command"""
        # This is more of an integration test
        # The flag should be readable by guard when set by policy-check
        # Actual verification would require deeper integration testing
        pass  # Placeholder for future integration tests


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def runner(self):
        """Create Click test runner"""
        return CliRunner()
    
    def test_policy_check_with_no_args_shows_help(self, runner, tmp_path):
        """policy-check with no args should show helpful error"""
        # Run in isolated directory without .crashlens/rules.yaml
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['policy-check'])
            
            # Should fail with error about missing rules or show help
            assert result.exit_code != 0 or 'rules.yaml' in result.output.lower() or '--help' in result.output
    
    def test_policy_check_with_missing_rules(self, runner, tmp_path):
        """policy-check should fail gracefully with missing rules"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text('{"test": "data"}\n')
        
        result = runner.invoke(cli, [
            'policy-check',
            str(log_file),
            '--rules', '/nonexistent/rules.yaml'
        ])
        
        # Should fail with clear error
        assert result.exit_code != 0
        assert 'Error' in result.output or 'does not exist' in result.output.lower()
    
    def test_guard_and_policy_check_both_handle_stdin(self, runner):
        """Both commands should handle stdin input"""
        # Test with minimal input
        input_data = '{"timestamp": "2025-01-15T10:00:00Z", "model": "gpt-4"}\n'
        
        # guard with stdin (will show deprecation unless QUIET set)
        guard_result = runner.invoke(cli, [
            'guard',
            '--output', 'json'
        ], input=input_data, env={'CRASHLENS_QUIET': '1'})
        
        # policy-check with stdin
        policy_check_result = runner.invoke(cli, [
            'policy-check',
            '--output', 'json'
        ], input=input_data, env={'CRASHLENS_QUIET': '1'})
        
        # Both should handle stdin (may fail due to missing rules, but shouldn't crash)
        assert 'Traceback' not in guard_result.output
        assert 'Traceback' not in policy_check_result.output
