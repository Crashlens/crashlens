#!/usr/bin/env python3
"""
Tests for SMTP Configuration Management
"""

import os
from pathlib import Path

import pytest
import yaml

from crashlens.config.smtp_config import SMTPConfig, load_smtp_config


class TestSMTPConfig:
    """Test SMTP configuration loading and validation"""
    
    def test_load_from_yaml(self, tmp_path):
        """Load configuration from YAML file"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'secret123',
            'from': 'Test <test@example.com>'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        
        assert config.get('server') == 'smtp.test.com'
        assert config.get('port') == 587
        assert config.get('user') == 'test@example.com'
        assert config.get('password') == 'secret123'
        assert config.get('from') == 'Test <test@example.com>'
    
    def test_env_var_override(self, tmp_path, monkeypatch):
        """Environment variables override YAML values"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.yaml.com',
            'port': 587,
            'user': 'yaml@example.com',
            'password': 'yaml-pass',
            'from': 'YAML <yaml@example.com>'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Set environment variables
        monkeypatch.setenv('SMTP_SERVER', 'smtp.env.com')
        monkeypatch.setenv('SMTP_USER', 'env@example.com')
        
        config = SMTPConfig(yaml_path=config_file)
        
        # Env vars should override YAML
        assert config.get('server') == 'smtp.env.com'
        assert config.get('user') == 'env@example.com'
        
        # Non-overridden values come from YAML
        assert config.get('password') == 'yaml-pass'
        assert config.get('from') == 'YAML <yaml@example.com>'
    
    def test_validate_complete_config(self, tmp_path):
        """Validation passes with all required keys"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'secret123',
            'from': 'Test <test@example.com>'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        is_valid, missing = config.validate()
        
        assert is_valid is True
        assert len(missing) == 0
    
    def test_validate_missing_keys(self, tmp_path):
        """Validation fails with missing required keys"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            # Missing: port, user, password, from
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        is_valid, missing = config.validate()
        
        assert is_valid is False
        assert 'port' in missing
        assert 'user' in missing
        assert 'password' in missing
        assert 'from' in missing
    
    def test_validate_empty_values(self, tmp_path):
        """Validation fails with empty string values"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': '',  # Empty string
            'port': 587,
            'user': '   ',  # Whitespace only
            'password': 'secret',
            'from': 'test@example.com'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        is_valid, missing = config.validate()
        
        assert is_valid is False
        assert 'server' in missing  # Empty string counts as missing
        assert 'user' in missing    # Whitespace counts as missing
    
    def test_to_dict_includes_optional_defaults(self, tmp_path):
        """to_dict() includes optional keys with defaults"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'secret123',
            'from': 'Test <test@example.com>'
            # No use_tls or timeout specified
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        result = config.to_dict()
        
        assert result['use_tls'] is True  # Default
        assert result['timeout'] == 30    # Default
    
    def test_to_dict_custom_optional_values(self, tmp_path):
        """to_dict() uses custom optional values from YAML"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'secret123',
            'from': 'Test <test@example.com>',
            'use_tls': False,
            'timeout': 60
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        result = config.to_dict()
        
        assert result['use_tls'] is False
        assert result['timeout'] == 60
    
    def test_get_masked_dict_hides_password(self, tmp_path):
        """get_masked_dict() masks sensitive password"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'supersecret',
            'from': 'Test <test@example.com>'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = SMTPConfig(yaml_path=config_file)
        masked = config.get_masked_dict()
        
        assert masked['password'] == '***'
        assert masked['server'] == 'smtp.test.com'
        assert masked['user'] == 'test@example.com'
    
    def test_no_yaml_file_returns_empty_config(self):
        """SMTPConfig works without YAML file (env vars only)"""
        config = SMTPConfig(yaml_path=None)
        
        # Should not crash, returns None for missing keys
        assert config.get('server') is None
        assert config.get('port') is None
    
    def test_malformed_yaml_raises_exception(self, tmp_path):
        """Malformed YAML raises ClickException"""
        config_file = tmp_path / 'smtp.yaml'
        
        with open(config_file, 'w') as f:
            f.write('{ invalid yaml content [')
        
        from click import ClickException
        with pytest.raises(ClickException, match='Failed to parse'):
            SMTPConfig(yaml_path=config_file)
    
    def test_non_dict_yaml_raises_exception(self, tmp_path):
        """YAML with non-dict root raises ClickException"""
        config_file = tmp_path / 'smtp.yaml'
        
        with open(config_file, 'w') as f:
            yaml.dump(['list', 'of', 'values'], f)
        
        from click import ClickException
        with pytest.raises(ClickException, match='Expected dictionary'):
            SMTPConfig(yaml_path=config_file)
    
    def test_port_string_to_int_conversion(self, tmp_path, monkeypatch):
        """Port from environment variable converts string to int"""
        monkeypatch.setenv('SMTP_SERVER', 'smtp.test.com')
        monkeypatch.setenv('SMTP_PORT', '25')  # String port
        monkeypatch.setenv('SMTP_USER', 'test@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'secret')
        monkeypatch.setenv('SMTP_FROM', 'test@example.com')
        
        config = SMTPConfig()
        
        assert config.get('port') == 25
        assert isinstance(config.get('port'), int)
    
    def test_invalid_port_falls_back_to_yaml(self, tmp_path, monkeypatch):
        """Invalid port env var falls back to YAML value"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {'port': 587}
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        monkeypatch.setenv('SMTP_PORT', 'not-a-number')
        
        config = SMTPConfig(yaml_path=config_file)
        
        # Should fall back to YAML value
        assert config.get('port') == 587
    
    def test_create_example_config(self, tmp_path):
        """create_example_config() generates valid YAML"""
        output_path = tmp_path / '.crashlens' / 'smtp.yaml'
        
        SMTPConfig.create_example_config(output_path)
        
        assert output_path.exists()
        
        # Load and validate example
        with open(output_path, 'r') as f:
            content = f.read()
            assert 'server:' in content
            assert 'Environment variables override' in content
        
        # Should be valid YAML
        config = SMTPConfig(yaml_path=output_path)
        assert config.get('server') is not None


class TestLoadSMTPConfig:
    """Test load_smtp_config() helper function"""
    
    def test_load_valid_config(self, tmp_path):
        """load_smtp_config() returns SMTPConfig for valid config"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            'port': 587,
            'user': 'test@example.com',
            'password': 'secret123',
            'from': 'Test <test@example.com>'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = load_smtp_config(yaml_path=config_file)
        
        assert config is not None
        assert config.get('server') == 'smtp.test.com'
    
    def test_load_incomplete_config_returns_none(self, tmp_path):
        """load_smtp_config() returns None for incomplete config"""
        config_file = tmp_path / 'smtp.yaml'
        config_data = {
            'server': 'smtp.test.com',
            # Missing required keys
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = load_smtp_config(yaml_path=config_file)
        
        assert config is None
    
    def test_load_nonexistent_file_returns_none(self):
        """load_smtp_config() returns None if file doesn't exist"""
        config = load_smtp_config(yaml_path=Path('/nonexistent/smtp.yaml'))
        
        # Should not crash, just return None
        assert config is None
