"""
CrashLens License Key System
Minimal paid feature gating for advanced policy rules
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LicenseChecker:
    """Handles license key validation and feature gating"""
    
    def __init__(self):
        self.license_key: Optional[str] = None
        self.license_source: Optional[str] = None
        self.valid_keys: Dict[str, Any] = {}
        self._load_valid_keys()
    
    def _load_valid_keys(self) -> None:
        """Load valid license keys from keys.yaml whitelist"""
        try:
            keys_file = Path(__file__).parent.parent / "keys.yaml"
            if keys_file.exists():
                with open(keys_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.valid_keys = {key: {} for key in data.get('valid_keys', [])}
            else:
                # Fallback for development - some built-in dev keys
                self.valid_keys = {
                    'FREE-TRIAL-123': {'type': 'trial'},
                    'STUDENT-DEV-456': {'type': 'student'},
                    'DEV-LOCAL-789': {'type': 'dev'}
                }
                logger.debug("No keys.yaml found, using built-in dev keys")
        except Exception as e:
            logger.warning(f"Failed to load license keys: {e}")
            self.valid_keys = {}
    
    def load_license_key(self, cli_key: Optional[str] = None) -> Optional[str]:
        """
        Load license key from multiple sources in priority order:
        1. CLI argument --license-key
        2. Environment variable CRASHLENS_LICENSE_KEY
        3. User config file ~/.crashlens/license.yaml
        4. Local override .crashlens_license
        
        Returns the license key if found, None otherwise
        """
        
        # 1. CLI argument (highest priority)
        if cli_key:
            self.license_key = cli_key.strip()
            self.license_source = "CLI argument"
            logger.debug(f"License key loaded from {self.license_source}")
            return self.license_key
        
        # 2. Environment variable
        env_key = os.getenv('CRASHLENS_LICENSE_KEY')
        if env_key:
            self.license_key = env_key.strip()
            self.license_source = "Environment variable CRASHLENS_LICENSE_KEY"
            logger.debug(f"License key loaded from {self.license_source}")
            return self.license_key
        
        # 3. User config file ~/.crashlens/license.yaml
        try:
            user_config = Path.home() / ".crashlens" / "license.yaml"
            if user_config.exists():
                with open(user_config, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'license_key' in data:
                        self.license_key = data['license_key'].strip()
                        self.license_source = f"User config {user_config}"
                        logger.debug(f"License key loaded from {self.license_source}")
                        return self.license_key
        except Exception as e:
            logger.debug(f"Could not read user config: {e}")
        
        # 4. Local override file .crashlens_license
        try:
            local_override = Path.cwd() / ".crashlens_license"
            if local_override.exists():
                with open(local_override, 'r', encoding='utf-8') as f:
                    key = f.read().strip()
                    if key:
                        self.license_key = key
                        self.license_source = "Local override .crashlens_license"
                        logger.debug(f"License key loaded from {self.license_source}")
                        return self.license_key
        except Exception as e:
            logger.debug(f"Could not read local override: {e}")
        
        # No license key found
        self.license_key = None
        self.license_source = None
        logger.debug("No license key found")
        return None
    
    def is_valid_key(self, key: str) -> bool:
        """Check if the provided key is in the valid keys whitelist"""
        if not key:
            return False
        
        normalized_key = key.strip().upper()
        return normalized_key in self.valid_keys
    
    def is_licensed(self) -> bool:
        """Check if current license key is valid"""
        if not self.license_key:
            return False
        return self.is_valid_key(self.license_key)
    
    def mask_license_key(self, key: Optional[str] = None) -> str:
        """Mask license key for safe display in logs"""
        if not key:
            key = self.license_key
        
        if not key:
            return "None"
        
        if len(key) <= 4:
            return "****"
        
        # Show first 4 chars, mask middle, show last 3
        if len(key) >= 8:
            return f"{key[:4]}****{key[-3:]}"
        else:
            return f"{key[:2]}****{key[-2:]}"
    
    def get_license_status(self) -> Dict[str, Any]:
        """Get comprehensive license status for debugging"""
        return {
            'has_key': self.license_key is not None,
            'is_valid': self.is_licensed(),
            'source': self.license_source,
            'masked_key': self.mask_license_key(),
            'valid_keys_count': len(self.valid_keys)
        }
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """Get list of features enabled by current license"""
        is_licensed = self.is_licensed()
        
        return {
            'advanced_policy_rules': is_licensed,
            'fallback_blocking': is_licensed,
            'cost_optimization': is_licensed,
            'premium_detectors': is_licensed,
            'detailed_analytics': is_licensed
        }
    
    def print_license_banner(self, debug: bool = False) -> None:
        """Print license status banner"""
        if self.is_licensed():
            print(f"🔓 CrashLens Pro features unlocked ({self.mask_license_key()})")
        else:
            print("🔒 CrashLens Free - Some advanced features require a Pro license")
            print("   Get a free trial key at crashlens.dev/upgrade")
        
        if debug:
            status = self.get_license_status()
            print(f"   Debug: Key source: {status['source']}")
            print(f"   Debug: Valid keys available: {status['valid_keys_count']}")


# Global license checker instance
_license_checker = LicenseChecker()


def get_license_checker() -> LicenseChecker:
    """Get the global license checker instance"""
    return _license_checker


def load_license_key(cli_key: Optional[str] = None) -> Optional[str]:
    """Convenience function to load license key"""
    return _license_checker.load_license_key(cli_key)


def is_valid_key(key: str) -> bool:
    """Convenience function to check if a key is valid"""
    return _license_checker.is_valid_key(key)


def is_licensed() -> bool:
    """Convenience function to check if currently licensed"""
    return _license_checker.is_licensed()


def requires_license_warning(rule_id: str) -> str:
    """Generate a warning message for license-gated rules"""
    return f"🔒 Premium rule blocked: {rule_id} (requires CrashLens Pro license)"


def get_upgrade_message() -> str:
    """Get the upgrade message with link"""
    return "Get your free trial key at crashlens.dev/upgrade"
