#!/usr/bin/env python3
"""
SMTP Configuration Management

Handles loading SMTP configuration from .crashlens/smtp.yaml with
environment variable override support. Provides graceful fallback
and comprehensive validation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import click
import yaml


class SMTPConfig:
    """
    SMTP configuration with cascading precedence:
    1. Environment variables (highest priority)
    2. YAML configuration file
    3. None (graceful failure)
    
    Configuration precedence allows secure credential management:
    - Developers use YAML files locally
    - CI/CD uses environment variables
    - Production uses secret managers via env vars
    """
    
    REQUIRED_KEYS = ['server', 'port', 'user', 'password', 'from']
    ENV_VAR_MAP = {
        'server': 'SMTP_SERVER',
        'port': 'SMTP_PORT',
        'user': 'SMTP_USER',
        'password': 'SMTP_PASSWORD',
        'from': 'SMTP_FROM'
    }
    
    def __init__(self, yaml_path: Optional[Path] = None):
        """
        Initialize SMTP configuration.
        
        Args:
            yaml_path: Path to YAML config file. If None, searches for
                      .crashlens/smtp.yaml in current directory and parents.
        
        Example YAML structure:
            server: smtp.gmail.com
            port: 587
            user: alerts@example.com
            password: app-specific-password
            from: CrashLens Alerts <alerts@example.com>
            use_tls: true  # optional, defaults to true
            timeout: 30    # optional, seconds
        """
        self.yaml_path = yaml_path or self._find_config_file()
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _find_config_file(self) -> Optional[Path]:
        """
        Search for .crashlens/smtp.yaml in current directory and parents.
        
        Returns:
            Path to config file if found, None otherwise
        """
        current = Path.cwd()
        
        # Search up to 5 levels (prevent infinite loop)
        for _ in range(5):
            config_path = current / '.crashlens' / 'smtp.yaml'
            if config_path.exists():
                return config_path
            
            # Move to parent directory
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent
        
        return None
    
    def _load_config(self) -> None:
        """
        Load configuration from YAML file if it exists.
        
        Raises:
            click.ClickException: If YAML is malformed or unreadable
        """
        if not self.yaml_path or not self.yaml_path.exists():
            return
        
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            # Validate that loaded data is a dictionary
            if not isinstance(self._config, dict):
                raise click.ClickException(
                    f"Invalid SMTP config at {self.yaml_path}: Expected dictionary, got {type(self._config).__name__}"
                )
            
        except yaml.YAMLError as e:
            raise click.ClickException(
                f"Failed to parse SMTP config at {self.yaml_path}: {e}"
            )
        except Exception as e:
            raise click.ClickException(
                f"Failed to read SMTP config at {self.yaml_path}: {e}"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with environment variable override.
        
        Precedence:
        1. Environment variable (e.g., SMTP_SERVER)
        2. YAML configuration value
        3. Default value
        
        Args:
            key: Configuration key (e.g., 'server', 'port', 'user')
            default: Default value if key not found in any source
        
        Returns:
            Configuration value or default
        
        Example:
            >>> config = SMTPConfig()
            >>> server = config.get('server')  # Checks $SMTP_SERVER then YAML
            >>> port = config.get('port', 587)  # Defaults to 587 if not set
        """
        # Check environment variable first (highest priority)
        env_var = self.ENV_VAR_MAP.get(key)
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                # Convert port to int if needed
                if key == 'port':
                    try:
                        return int(env_value)
                    except ValueError:
                        click.echo(
                            f"Warning: Invalid {env_var}='{env_value}', must be integer",
                            err=True
                        )
                        # Fall through to YAML/default
                else:
                    return env_value
        
        # Check YAML configuration
        yaml_value = self._config.get(key)
        if yaml_value is not None:
            return yaml_value
        
        # Return default
        return default
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration keys are present.
        
        Returns:
            Tuple of (is_valid, missing_keys)
            - is_valid: True if all required keys present, False otherwise
            - missing_keys: List of missing required key names
        
        Example:
            >>> config = SMTPConfig()
            >>> is_valid, missing = config.validate()
            >>> if not is_valid:
            ...     click.echo(f"Missing SMTP config: {', '.join(missing)}")
        """
        missing_keys = []
        
        for key in self.REQUIRED_KEYS:
            value = self.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_keys.append(key)
        
        return (len(missing_keys) == 0, missing_keys)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export merged configuration as dictionary.
        
        Applies environment variable overrides and includes optional keys.
        
        Returns:
            Dictionary with all configuration values
            
        Example:
            >>> config = SMTPConfig()
            >>> smtp_params = config.to_dict()
            >>> # Use with smtplib
            >>> import smtplib
            >>> server = smtplib.SMTP(smtp_params['server'], smtp_params['port'])
        """
        result = {}
        
        # Get all required keys
        for key in self.REQUIRED_KEYS:
            result[key] = self.get(key)
        
        # Get optional keys with defaults
        result['use_tls'] = self.get('use_tls', True)
        result['timeout'] = self.get('timeout', 30)
        
        return result
    
    def get_masked_dict(self) -> Dict[str, Any]:
        """
        Export configuration with sensitive values masked for logging.
        
        Returns:
            Dictionary with password masked as '***'
            
        Example:
            >>> config = SMTPConfig()
            >>> click.echo(f"SMTP config: {config.get_masked_dict()}")
            SMTP config: {'server': 'smtp.gmail.com', 'password': '***', ...}
        """
        masked = self.to_dict()
        if 'password' in masked:
            masked['password'] = '***'
        return masked
    
    @classmethod
    def create_example_config(cls, output_path: Path) -> None:
        """
        Create example .crashlens/smtp.yaml configuration file.
        
        Args:
            output_path: Path where example config should be written
        
        Example:
            >>> from pathlib import Path
            >>> SMTPConfig.create_example_config(Path('.crashlens/smtp.yaml'))
        """
        example = {
            'server': 'smtp.gmail.com',
            'port': 587,
            'user': 'alerts@example.com',
            'password': 'your-app-specific-password',
            'from': 'CrashLens Alerts <alerts@example.com>',
            'use_tls': True,
            'timeout': 30
        }
        
        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('# CrashLens SMTP Configuration\n')
            f.write('# Environment variables override these values:\n')
            for key, env_var in cls.ENV_VAR_MAP.items():
                f.write(f'#   ${env_var} overrides {key}\n')
            f.write('\n')
            yaml.dump(example, f, default_flow_style=False, sort_keys=False)


def load_smtp_config(yaml_path: Optional[Path] = None) -> Optional[SMTPConfig]:
    """
    Load SMTP configuration from YAML file or environment variables.
    
    This is the main entry point for getting SMTP configuration.
    Falls back gracefully if configuration is incomplete.
    
    Args:
        yaml_path: Optional explicit path to YAML config file
    
    Returns:
        SMTPConfig instance if valid configuration found, None otherwise
    
    Example:
        >>> config = load_smtp_config()
        >>> if config:
        ...     smtp_params = config.to_dict()
        ...     send_email(smtp_params, recipient, subject, body)
        ... else:
        ...     click.echo("Warning: SMTP not configured, skipping email")
    """
    try:
        config = SMTPConfig(yaml_path)
        is_valid, missing = config.validate()
        
        if not is_valid:
            click.echo(
                f"⚠️  Warning: Incomplete SMTP configuration. Missing: {', '.join(missing)}",
                err=True
            )
            click.echo(
                "   Set environment variables or create .crashlens/smtp.yaml",
                err=True
            )
            return None
        
        return config
        
    except click.ClickException:
        # Re-raise Click exceptions (they'll be handled by CLI)
        raise
    except Exception as e:
        click.echo(f"⚠️  Warning: Failed to load SMTP config: {e}", err=True)
        return None
