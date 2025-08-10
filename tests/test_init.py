#!/usr/bin/env python3
"""
Unit tests for the enhanced Crashlens init command.
Tests non-interactive mode, config validation, version checking, and dry-run mode.
"""

import pytest
import os
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import the functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.cli import (
    init, _get_current_cli_version, _load_config_schema, _validate_config,
    _check_config_version_compatibility, _get_env_or_default, 
    _validate_template_selection, _print_workflow_yaml
)


class TestInitEnhancements:
    """Test suite for enhanced init command functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.test_env = {}
    
    def teardown_method(self):
        """Clean up test environment"""
        # Clean up environment variables
        env_vars = ['CRASHLENS_TEMPLATES', 'CRASHLENS_SEVERITY', 
                   'CRASHLENS_FAIL_ON_VIOLATIONS', 'CRASHLENS_LOGS_SOURCE',
                   'CRASHLENS_CREATE_WORKFLOW']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]


class TestNonInteractiveMode(TestInitEnhancements):
    """Test non-interactive mode functionality"""
    
    def test_non_interactive_with_valid_env_vars(self):
        """Test non-interactive mode with valid environment variables"""
        with self.runner.isolated_filesystem():
            os.environ.update({
                'CRASHLENS_TEMPLATES': 'retry-loop-prevention,model-overkill-detection',
                'CRASHLENS_SEVERITY': 'critical',
                'CRASHLENS_FAIL_ON_VIOLATIONS': 'true',
                'CRASHLENS_LOGS_SOURCE': 'langfuse',
                'CRASHLENS_CREATE_WORKFLOW': 'false'
            })
            
            result = self.runner.invoke(init, ['--non-interactive'])
            
            assert result.exit_code == 0
            assert "Running in non-interactive mode" in result.output
            assert "Policy templates: retry-loop-prevention,model-overkill-detection" in result.output
            assert "Severity threshold: critical" in result.output
            
            # Check config file was created
            config_path = Path('.crashlens/config.yaml')
            assert config_path.exists()
            
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert config['policy_template'] == 'retry-loop-prevention,model-overkill-detection'
            assert config['severity_threshold'] == 'critical'
            assert config['fail_on_violations'] is True
            assert config['logs_source'] == 'langfuse'
    
    def test_non_interactive_with_defaults(self):
        """Test non-interactive mode with default values"""
        with self.runner.isolated_filesystem():
            # Don't set any env vars, should use defaults
            result = self.runner.invoke(init, ['--non-interactive'])
            
            assert result.exit_code == 0
            assert "Policy templates: all" in result.output
            assert "Severity threshold: high" in result.output
            
            config_path = Path('.crashlens/config.yaml')
            assert config_path.exists()
            
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert config['policy_template'] == 'all'
            assert config['severity_threshold'] == 'high'
            assert config['fail_on_violations'] is True  # Default True
            assert config['logs_source'] == 'local'
    
    def test_non_interactive_with_invalid_env_vars(self):
        """Test non-interactive mode fails with invalid environment variables"""
        with self.runner.isolated_filesystem():
            os.environ.update({
                'CRASHLENS_TEMPLATES': 'invalid-template',
                'CRASHLENS_SEVERITY': 'invalid-severity',
                'CRASHLENS_LOGS_SOURCE': 'invalid-source'
            })
            
            result = self.runner.invoke(init, ['--non-interactive'])
            
            assert result.exit_code == 1
            assert "Invalid templates: invalid-template" in result.output
            assert "Invalid CRASHLENS_SEVERITY" in result.output
            assert "Invalid CRASHLENS_LOGS_SOURCE" in result.output
            assert "Non-interactive mode failed" in result.output


class TestConfigValidation(TestInitEnhancements):
    """Test configuration schema validation"""
    
    def test_load_config_schema(self):
        """Test loading the JSON schema"""
        schema = _load_config_schema()
        assert isinstance(schema, dict)
        assert 'type' in schema
        assert 'properties' in schema or 'required' in schema
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration"""
        valid_config = {
            'policy_template': 'all',
            'severity_threshold': 'high',
            'fail_on_violations': True,
            'logs_source': 'local',
            'version': '1.0.0'
        }
        
        errors = _validate_config(valid_config)
        assert len(errors) == 0
    
    def test_validate_invalid_config_missing_required(self):
        """Test validation catches missing required fields"""
        invalid_config = {
            'policy_template': 'all',
            # Missing required fields
        }
        
        errors = _validate_config(invalid_config)
        assert len(errors) > 0
        assert any('severity_threshold' in error for error in errors)
    
    def test_validate_invalid_config_wrong_types(self):
        """Test validation catches wrong value types"""
        invalid_config = {
            'policy_template': 'all',
            'severity_threshold': 'invalid-level',  # Invalid enum value
            'fail_on_violations': True,
            'logs_source': 'invalid-source',  # Invalid enum value
            'version': '1.0.0'
        }
        
        errors = _validate_config(invalid_config)
        assert len(errors) >= 2  # At least severity and logs_source errors


class TestVersionCompatibility(TestInitEnhancements):
    """Test version compatibility checking"""
    
    def test_get_current_cli_version(self):
        """Test getting current CLI version"""
        version = _get_current_cli_version()
        assert isinstance(version, str)
        assert len(version.split('.')) >= 2  # At least major.minor
    
    def test_version_compatibility_newer_config(self):
        """Test warning when config version is newer than CLI"""
        config_data = {
            'version': '2.0.0'  # Assume CLI is older
        }
        
        with patch('crashlens.cli._get_current_cli_version', return_value='1.0.0'):
            warning = _check_config_version_compatibility(config_data)
            assert warning is not None
            assert "newer version" in warning
            assert "incompatible" in warning
    
    def test_version_compatibility_older_config(self):
        """Test no warning when config version is older than CLI"""
        config_data = {
            'version': '1.0.0'
        }
        
        with patch('crashlens.cli._get_current_cli_version', return_value='2.0.0'):
            warning = _check_config_version_compatibility(config_data)
            assert warning is None
    
    def test_version_compatibility_same_version(self):
        """Test no warning when versions are the same"""
        config_data = {
            'version': '1.0.0'
        }
        
        with patch('crashlens.cli._get_current_cli_version', return_value='1.0.0'):
            warning = _check_config_version_compatibility(config_data)
            assert warning is None


class TestEnvironmentVariables(TestInitEnhancements):
    """Test environment variable handling"""
    
    def test_get_env_or_default_string(self):
        """Test getting string environment variable"""
        os.environ['TEST_VAR'] = 'test_value'
        result = _get_env_or_default('TEST_VAR', 'default_value')
        assert result == 'test_value'
        del os.environ['TEST_VAR']
    
    def test_get_env_or_default_missing(self):
        """Test default value when environment variable missing"""
        result = _get_env_or_default('MISSING_VAR', 'default_value')
        assert result == 'default_value'
    
    def test_get_env_or_default_bool_true(self):
        """Test boolean conversion for true values"""
        test_values = ['true', '1', 'yes', 'on', 'TRUE', 'True']
        for value in test_values:
            os.environ['TEST_BOOL'] = value
            result = _get_env_or_default('TEST_BOOL', False, bool)
            assert result is True
            del os.environ['TEST_BOOL']
    
    def test_get_env_or_default_bool_false(self):
        """Test boolean conversion for false values"""
        test_values = ['false', '0', 'no', 'off', 'FALSE', 'False']
        for value in test_values:
            os.environ['TEST_BOOL'] = value
            result = _get_env_or_default('TEST_BOOL', True, bool)
            assert result is False
            del os.environ['TEST_BOOL']


class TestTemplateValidation(TestInitEnhancements):
    """Test template selection validation"""
    
    def test_validate_template_all(self):
        """Test validation of 'all' template selection"""
        available = ['template1', 'template2', 'all']
        errors = _validate_template_selection('all', available)
        assert len(errors) == 0
    
    def test_validate_template_valid_list(self):
        """Test validation of valid template list"""
        available = ['template1', 'template2', 'template3', 'all']
        errors = _validate_template_selection('template1,template2', available)
        assert len(errors) == 0
    
    def test_validate_template_invalid_list(self):
        """Test validation catches invalid templates"""
        available = ['template1', 'template2', 'all']
        errors = _validate_template_selection('template1,invalid_template', available)
        assert len(errors) == 1
        assert 'invalid_template' in errors[0]
    
    def test_validate_template_whitespace_handling(self):
        """Test template validation handles whitespace correctly"""
        available = ['template1', 'template2', 'all']
        errors = _validate_template_selection(' template1 , template2 ', available)
        assert len(errors) == 0


class TestDryRunMode(TestInitEnhancements):
    """Test dry-run workflow functionality"""
    
    def test_dry_run_workflow_output(self):
        """Test dry-run mode outputs workflow YAML"""
        with self.runner.isolated_filesystem():
            os.environ.update({
                'CRASHLENS_TEMPLATES': 'all',
                'CRASHLENS_SEVERITY': 'high',
                'CRASHLENS_FAIL_ON_VIOLATIONS': 'true',
                'CRASHLENS_LOGS_SOURCE': 'local'
            })
            
            result = self.runner.invoke(init, ['--non-interactive', '--dry-run-workflow'])
            
            assert result.exit_code == 0
            assert "Dry run mode - printing workflow YAML" in result.output
            assert "name: Crashlens Policy Check" in result.output
            assert "uses: actions/checkout@" in result.output
            assert "no files written" in result.output
            
            # Ensure no actual files were created
            assert not Path('.crashlens/config.yaml').exists()
            assert not Path('.github/workflows/crashlens.yml').exists()


class TestAtomicFileOperations(TestInitEnhancements):
    """Test atomic file operations"""
    
    def test_config_file_atomic_write(self):
        """Test that config file writes are atomic"""
        with self.runner.isolated_filesystem():
            os.environ.update({
                'CRASHLENS_TEMPLATES': 'all',
                'CRASHLENS_SEVERITY': 'high',
                'CRASHLENS_FAIL_ON_VIOLATIONS': 'true',
                'CRASHLENS_LOGS_SOURCE': 'local'
            })
            
            # Mock an exception during write to test cleanup
            with patch('yaml.dump', side_effect=Exception("Test exception")):
                result = self.runner.invoke(init, ['--non-interactive'])
                
                assert result.exit_code == 1
                # Ensure no partial files remain
                assert not Path('.crashlens/config.yaml.tmp').exists()


class TestErrorHandling(TestInitEnhancements):
    """Test error handling and edge cases"""
    
    def test_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt"""
        with self.runner.isolated_filesystem():
            with patch('click.prompt', side_effect=KeyboardInterrupt()):
                result = self.runner.invoke(init)
                
                assert result.exit_code == 1
                assert "Setup cancelled by user" in result.output
    
    def test_permission_error_handling(self):
        """Test handling of file permission errors"""
        with self.runner.isolated_filesystem():
            # Create read-only directory
            os.makedirs('.crashlens', exist_ok=True)
            os.chmod('.crashlens', 0o444)  # Read-only
            
            try:
                os.environ.update({
                    'CRASHLENS_TEMPLATES': 'all',
                    'CRASHLENS_SEVERITY': 'high',
                    'CRASHLENS_FAIL_ON_VIOLATIONS': 'true',
                    'CRASHLENS_LOGS_SOURCE': 'local'
                })
                
                result = self.runner.invoke(init, ['--non-interactive'])
                
                assert result.exit_code == 1
                assert "Error during setup" in result.output
            finally:
                # Cleanup - restore write permissions
                os.chmod('.crashlens', 0o755)


if __name__ == '__main__':
    pytest.main([__file__])
