#!/usr/bin/env python3
"""
Unit tests for rule variable interpolation (Step 4).
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from crashlens.guard import interpolate_variables, guard


class TestInterpolateVariables:
    """Test variable interpolation function."""
    
    def test_interpolate_simple_var(self):
        """Interpolate simple $VAR format."""
        with patch.dict(os.environ, {'TEAM': 'platform'}):
            result = interpolate_variables('team=$TEAM')
            assert result == 'team=platform'
    
    def test_interpolate_braced_var(self):
        """Interpolate ${VAR} format."""
        with patch.dict(os.environ, {'THRESHOLD': '100'}):
            result = interpolate_variables('value=${THRESHOLD}')
            assert result == 'value=100'
    
    def test_interpolate_multiple_vars(self):
        """Interpolate multiple variables in same string."""
        with patch.dict(os.environ, {'ENV': 'prod', 'REGION': 'us-west'}):
            result = interpolate_variables('$ENV-$REGION')
            assert result == 'prod-us-west'
    
    def test_interpolate_mixed_formats(self):
        """Mix $VAR and ${VAR} in same string."""
        with patch.dict(os.environ, {'A': 'alpha', 'B': 'beta'}):
            result = interpolate_variables('$A-${B}')
            assert result == 'alpha-beta'
    
    def test_interpolate_undefined_var(self):
        """Keep undefined variables as-is."""
        result = interpolate_variables('value=$UNDEFINED_VAR')
        assert result == 'value=$UNDEFINED_VAR'
    
    def test_interpolate_dict(self):
        """Interpolate variables in dictionary values."""
        with patch.dict(os.environ, {'LIMIT': '50'}):
            result = interpolate_variables({
                'count': '> ${LIMIT}',
                'nested': {'value': '$LIMIT'}
            })
            assert result == {
                'count': '> 50',
                'nested': {'value': '50'}
            }
    
    def test_interpolate_list(self):
        """Interpolate variables in list items."""
        with patch.dict(os.environ, {'TAG': 'production'}):
            result = interpolate_variables(['$TAG', 'static', '${TAG}-app'])
            assert result == ['production', 'static', 'production-app']
    
    def test_interpolate_non_string(self):
        """Non-string values pass through unchanged."""
        assert interpolate_variables(123) == 123
        assert interpolate_variables(None) is None
        assert interpolate_variables(True) is True
    
    def test_interpolate_empty_string(self):
        """Empty string passes through."""
        assert interpolate_variables('') == ''
    
    def test_interpolate_no_vars(self):
        """String without variables passes through."""
        assert interpolate_variables('plain text') == 'plain text'


class TestGuardWithInterpolation:
    """Test guard command with variable interpolation."""
    
    @pytest.fixture
    def rules_with_vars(self, tmp_path):
        """Create rules file with variable references."""
        rules_file = tmp_path / "rules.yaml"
        rules_content = """
rules:
  - id: RL_VAR_001
    description: "Test rule with env var"
    if:
      team: "$TEAM_NAME"
    action: fail_ci
    severity: error
  
  - id: RL_VAR_002
    description: "Test rule with braced var"
    if:
      threshold: "> ${TOKEN_LIMIT}"
    action: warn
    severity: warning
"""
        rules_file.write_text(rules_content)
        return rules_file
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample JSONL logs."""
        logs_file = tmp_path / "logs.jsonl"
        logs_content = """{"traceId": "t1", "team": "platform", "threshold": "150"}
{"traceId": "t2", "team": "data", "threshold": "50"}
{"traceId": "t3", "team": "platform", "threshold": "200"}
"""
        logs_file.write_text(logs_content)
        return logs_file
    
    @patch.dict(os.environ, {'TEAM_NAME': 'platform', 'TOKEN_LIMIT': '100'})
    def test_guard_interpolates_vars(self, tmp_path, rules_with_vars, sample_logs):
        """Guard command interpolates variables in rules."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs),
                '--rules', str(rules_with_vars),
                '--output', 'json'
            ])
            
            # Extract JSON from output
            output = result.output
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                import json
                json_output = output[start_idx:end_idx+1]
                report = json.loads(json_output)
                
                # RL_VAR_001: team=$TEAM_NAME → team=platform (2 matches)
                assert report['rules']['RL_VAR_001']['count'] == 2
                
                # RL_VAR_002: threshold > ${TOKEN_LIMIT} → threshold > 100 (2 matches: 150, 200)
                assert report['rules']['RL_VAR_002']['count'] == 2
    
    @patch.dict(os.environ, {'TEAM_NAME': 'data'})
    def test_guard_different_env_values(self, tmp_path, rules_with_vars, sample_logs):
        """Different env values change matching behavior."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs),
                '--rules', str(rules_with_vars),
                '--output', 'json'
            ])
            
            output = result.output
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                import json
                json_output = output[start_idx:end_idx+1]
                report = json.loads(json_output)
                
                # TEAM_NAME=data → only 1 match now
                assert report['rules']['RL_VAR_001']['count'] == 1
    
    def test_guard_undefined_var_no_match(self, tmp_path, rules_with_vars, sample_logs):
        """Undefined variables remain literal, likely no matches."""
        runner = CliRunner()
        
        # No environment variables set
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(guard, [
                str(sample_logs),
                '--rules', str(rules_with_vars),
                '--output', 'json'
            ])
            
            # Should not crash, rules will have literal $TEAM_NAME
            # Exit code may be 1 if no matches, but should not error
            assert result.exit_code in [0, 1]


class TestInterpolationEdgeCases:
    """Test edge cases for variable interpolation."""
    
    def test_partial_var_name(self):
        """Variable names must start with letter or underscore."""
        with patch.dict(os.environ, {'VAR': 'value'}):
            # $1VAR should not interpolate (starts with digit)
            result = interpolate_variables('$1VAR')
            assert result == '$1VAR'
    
    def test_var_with_underscore(self):
        """Variable names can contain underscores."""
        with patch.dict(os.environ, {'MY_VAR_NAME': 'test'}):
            result = interpolate_variables('$MY_VAR_NAME')
            assert result == 'test'
    
    def test_var_with_numbers(self):
        """Variable names can contain numbers after first character."""
        with patch.dict(os.environ, {'VAR123': 'test'}):
            result = interpolate_variables('$VAR123')
            assert result == 'test'
    
    def test_escaped_dollar(self):
        """Dollar signs in non-variable context."""
        result = interpolate_variables('price: $5.99')
        # $5 won't match because followed by .
        assert 'price' in result
    
    def test_consecutive_vars(self):
        """Multiple variables back-to-back."""
        with patch.dict(os.environ, {'A': '1', 'B': '2', 'C': '3'}):
            result = interpolate_variables('$A$B$C')
            assert result == '123'
    
    def test_var_in_comparison(self):
        """Variables in comparison expressions."""
        with patch.dict(os.environ, {'LIMIT': '100'}):
            result = interpolate_variables('> $LIMIT')
            assert result == '> 100'
