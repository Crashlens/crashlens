"""
Unit tests for config loader and variable resolution.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from crashlens.config import load_config, resolve_variables_in_obj


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config cache before each test."""
    import crashlens.config.variables
    crashlens.config.variables._CONFIG = None
    yield
    crashlens.config.variables._CONFIG = None


class TestLoadConfig:
    """Test configuration loading."""
    
    def test_load_config_missing_file(self, tmp_path, monkeypatch):
        """Config returns empty dict when file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config == {}
    
    def test_load_config_with_yaml_file(self, tmp_path, monkeypatch):
        """Config loads from .crashlens/config.yaml."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        config_file = crashlens_dir / "config.yaml"
        config_file.write_text("env:\n  TEAM: platform\n  LIMIT: 1000\n")
        
        config = load_config()
        assert config['env']['TEAM'] == 'platform'
        assert config['env']['LIMIT'] == 1000
    
    def test_load_config_caching(self, tmp_path, monkeypatch):
        """Config is cached after first load."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        config_file = crashlens_dir / "config.yaml"
        config_file.write_text("env:\n  CACHED: true\n")
        
        config1 = load_config()
        # Modify file
        config_file.write_text("env:\n  CACHED: false\n")
        config2 = load_config()
        
        # Should return cached value
        assert config1 is config2
        assert config1['env']['CACHED'] is True


class TestResolveVariablesEnv:
    """Test environment variable resolution."""
    
    def test_resolve_simple_var(self):
        """Resolve $VAR from environment."""
        with patch.dict(os.environ, {'TEAM': 'platform'}):
            result = resolve_variables_in_obj('team=$TEAM')
            assert result == 'team=platform'
    
    def test_resolve_braced_var(self):
        """Resolve ${VAR} from environment."""
        with patch.dict(os.environ, {'THRESHOLD': '100'}):
            result = resolve_variables_in_obj('value=${THRESHOLD}')
            assert result == 'value=100'
    
    def test_resolve_multiple_vars(self):
        """Resolve multiple variables in same string."""
        with patch.dict(os.environ, {'ENV': 'prod', 'REGION': 'us-west'}):
            result = resolve_variables_in_obj('$ENV-$REGION')
            assert result == 'prod-us-west'
    
    def test_resolve_dict(self):
        """Resolve variables in dictionary values."""
        with patch.dict(os.environ, {'LIMIT': '50'}):
            result = resolve_variables_in_obj({
                'count': '> ${LIMIT}',
                'nested': {'value': '$LIMIT'}
            })
            assert result == {
                'count': '> 50',
                'nested': {'value': '50'}
            }
    
    def test_resolve_list(self):
        """Resolve variables in list items."""
        with patch.dict(os.environ, {'TAG': 'production'}):
            result = resolve_variables_in_obj(['$TAG', 'static', '${TAG}-app'])
            assert result == ['production', 'static', 'production-app']


class TestResolveVariablesConfig:
    """Test fallback to config file."""
    
    def test_resolve_from_config_env(self, tmp_path, monkeypatch):
        """Resolve variable from config.env mapping."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        config_file = crashlens_dir / "config.yaml"
        config_file.write_text("env:\n  TEAM: platform\n  LIMIT: 1000\n")
        
        result = resolve_variables_in_obj('team=$TEAM limit=${LIMIT}')
        assert result == 'team=platform limit=1000'
    
    def test_resolve_from_top_level_config(self, tmp_path, monkeypatch):
        """Resolve variable from top-level config key."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        config_file = crashlens_dir / "config.yaml"
        config_file.write_text("DEFAULT_MODEL: gpt-4\n")
        
        result = resolve_variables_in_obj('model=$DEFAULT_MODEL')
        assert result == 'model=gpt-4'
    
    def test_env_takes_precedence_over_config(self, tmp_path, monkeypatch):
        """Environment variable takes precedence over config."""
        monkeypatch.chdir(tmp_path)
        crashlens_dir = tmp_path / ".crashlens"
        crashlens_dir.mkdir()
        config_file = crashlens_dir / "config.yaml"
        config_file.write_text("env:\n  TEAM: from-config\n")
        
        with patch.dict(os.environ, {'TEAM': 'from-env'}):
            result = resolve_variables_in_obj('team=$TEAM')
            assert result == 'team=from-env'


class TestResolveVariablesRequired:
    """Test required flag behavior."""
    
    def test_required_raises_on_missing_var(self):
        """Required flag raises KeyError for missing variable."""
        with pytest.raises(KeyError, match="Missing variable: UNDEFINED"):
            resolve_variables_in_obj('value=$UNDEFINED', required=True)
    
    def test_required_succeeds_when_var_found(self):
        """Required flag doesn't raise when variable exists."""
        with patch.dict(os.environ, {'EXISTS': 'value'}):
            result = resolve_variables_in_obj('$EXISTS', required=True)
            assert result == 'value'
    
    def test_not_required_keeps_original(self):
        """Non-required mode keeps original string."""
        result = resolve_variables_in_obj('value=$UNDEFINED', required=False)
        assert result == 'value=$UNDEFINED'


class TestResolveVariablesEdgeCases:
    """Test edge cases."""
    
    def test_non_string_unchanged(self):
        """Non-string values pass through unchanged."""
        assert resolve_variables_in_obj(123) == 123
        assert resolve_variables_in_obj(None) is None
        assert resolve_variables_in_obj(True) is True
    
    def test_empty_string(self):
        """Empty string passes through."""
        assert resolve_variables_in_obj('') == ''
    
    def test_no_variables(self):
        """String without variables passes through."""
        assert resolve_variables_in_obj('plain text') == 'plain text'
