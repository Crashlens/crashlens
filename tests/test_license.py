"""
Unit tests for the license gating system
Tests license key validation and feature gating logic
"""

import unittest
from unittest.mock import patch, mock_open
import tempfile
import os
from pathlib import Path
import yaml

from crashlens.license_checker import LicenseChecker, get_license_checker, load_license_key
from crashlens.policy.engine import PolicyEngine, PolicyRule, PolicyAction, PolicySeverity


class TestLicenseChecker(unittest.TestCase):
    """Test the LicenseChecker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.checker = LicenseChecker()
        # Set up some test keys
        self.checker.valid_keys = {
            'VALID-TEST-123': {'type': 'test'},
            'TRIAL-KEY-456': {'type': 'trial'},
            'DEV-LOCAL-789': {'type': 'dev'}
        }
    
    def test_valid_key(self):
        """Test validation of a valid license key"""
        self.assertTrue(self.checker.is_valid_key('VALID-TEST-123'))
        self.assertTrue(self.checker.is_valid_key('TRIAL-KEY-456'))
        self.assertTrue(self.checker.is_valid_key('DEV-LOCAL-789'))
    
    def test_invalid_key(self):
        """Test validation of invalid license keys"""
        self.assertFalse(self.checker.is_valid_key('INVALID-KEY'))
        self.assertFalse(self.checker.is_valid_key(''))
        self.assertFalse(self.checker.is_valid_key(None))
        self.assertFalse(self.checker.is_valid_key('WRONG-123'))
    
    def test_no_key(self):
        """Test behavior when no license key is provided"""
        checker = LicenseChecker()
        self.assertIsNone(checker.license_key)
        self.assertFalse(checker.is_licensed())
    
    def test_key_loading_priority_cli(self):
        """Test that CLI key takes priority over environment"""
        with patch.dict(os.environ, {'CRASHLENS_LICENSE_KEY': 'ENV-KEY-123'}):
            key = self.checker.load_license_key(cli_key='CLI-KEY-456')
            self.assertEqual(key, 'CLI-KEY-456')
            self.assertEqual(self.checker.license_source, 'CLI argument')
    
    def test_key_loading_priority_env(self):
        """Test that environment key is used when no CLI key"""
        with patch.dict(os.environ, {'CRASHLENS_LICENSE_KEY': 'ENV-KEY-123'}):
            key = self.checker.load_license_key()
            self.assertEqual(key, 'ENV-KEY-123')
            self.assertEqual(self.checker.license_source, 'Environment variable CRASHLENS_LICENSE_KEY')
    
    def test_key_masking(self):
        """Test that license keys are properly masked in output"""
        self.checker.license_key = 'SECRET-LICENSE-KEY'
        masked = self.checker.mask_license_key()
        self.assertEqual(masked, 'SECR****KEY')
        
        # Test short keys
        self.checker.license_key = 'ABC'
        masked = self.checker.mask_license_key()
        self.assertEqual(masked, '****')
    
    def test_get_enabled_features(self):
        """Test the get_enabled_features() function"""
        # Without license
        self.checker.license_key = None
        features = self.checker.get_enabled_features()
        self.assertFalse(features['advanced_policy_rules'])
        
        # With valid license
        self.checker.license_key = 'VALID-TEST-123'
        features = self.checker.get_enabled_features()
        self.assertTrue(features['advanced_policy_rules'])
        self.assertTrue(features['cost_optimization'])


class TestPolicyGating(unittest.TestCase):
    """Test policy rule gating based on license status"""
    
    def setUp(self):
        """Set up test policy rules"""
        self.free_rule = PolicyRule(
            id='free-rule',
            description='Free tier rule',
            match={'model': 'gpt-3.5-turbo'},
            action=PolicyAction.WARN,
            severity=PolicySeverity.LOW,
            suggestion='Consider upgrading model',
            requires_license=False
        )
        
        self.premium_rule = PolicyRule(
            id='premium-rule',
            description='Premium tier rule',
            match={'usage.total_tokens': '>5000'},
            action=PolicyAction.BLOCK,
            severity=PolicySeverity.HIGH,
            suggestion='Optimize token usage',
            requires_license=True
        )
    
    def test_gated_rule_skipped_without_license(self):
        """Test that gated rules are skipped when no valid license"""
        # Create a temporary policy file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            policy_data = {
                'rules': [
                    {
                        'id': 'free-rule',
                        'description': 'Free rule',
                        'match': {'model': 'gpt-4'},
                        'action': 'warn',
                        'severity': 'low',
                        'suggestion': 'Use cheaper model',
                        'requires_license': False
                    },
                    {
                        'id': 'premium-rule',
                        'description': 'Premium rule',
                        'match': {'usage.total_tokens': '>5000'},
                        'action': 'block',
                        'severity': 'high',
                        'suggestion': 'Optimize tokens',
                        'requires_license': True
                    }
                ]
            }
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            engine = PolicyEngine(Path(policy_file))
            
            log_entries = [
                {'model': 'gpt-4', 'usage': {'total_tokens': 6000}}
            ]
            
            # Test without license - should skip premium rules
            violations, skipped_rules = engine.evaluate_logs(log_entries, strict_license=False)
            
            # Should have 1 violation from free rule, 1 skipped premium rule
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].rule_id, 'free-rule')
            self.assertEqual(len(skipped_rules), 1)
            self.assertIn('premium-rule', skipped_rules)
            
        finally:
            os.unlink(policy_file)
    
    def test_gated_rule_runs_with_valid_license(self):
        """Test that gated rules run normally with valid license"""
        # Create a temporary policy file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            policy_data = {
                'rules': [
                    {
                        'id': 'free-rule',
                        'description': 'Free rule',
                        'match': {'model': 'gpt-4'},
                        'action': 'warn',
                        'severity': 'low',
                        'suggestion': 'Use cheaper model',
                        'requires_license': False
                    },
                    {
                        'id': 'premium-rule',
                        'description': 'Premium rule',
                        'match': {'usage.total_tokens': '>5000'},
                        'action': 'block',
                        'severity': 'high',
                        'suggestion': 'Optimize tokens',
                        'requires_license': True
                    }
                ]
            }
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            engine = PolicyEngine(Path(policy_file))
            
            # Set up global license checker with valid license
            checker = get_license_checker()
            original_key = checker.license_key
            checker.license_key = 'VALID-TEST-123'
            checker.valid_keys = {'VALID-TEST-123': {'type': 'test'}}
            
            log_entries = [
                {'model': 'gpt-4', 'usage': {'total_tokens': 6000}}
            ]
            
            violations, skipped_rules = engine.evaluate_logs(log_entries, strict_license=False)
            
            # Should have 2 violations (both rules run), 0 skipped
            self.assertEqual(len(violations), 2)
            self.assertEqual(len(skipped_rules), 0)
            
            # Check both rules fired
            rule_ids = [v.rule_id for v in violations]
            self.assertIn('free-rule', rule_ids)
            self.assertIn('premium-rule', rule_ids)
            
            # Restore original state
            checker.license_key = original_key
            
        finally:
            os.unlink(policy_file)
    
    def test_non_gated_rule_runs_normally(self):
        """Test that non-gated rules always run regardless of license"""
        # Create a temporary policy file with only non-gated rules
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            policy_data = {
                'rules': [
                    {
                        'id': 'free-rule-1',
                        'description': 'Free rule 1',
                        'match': {'model': 'gpt-4'},
                        'action': 'warn',
                        'severity': 'low',
                        'suggestion': 'Use cheaper model',
                        'requires_license': False
                    },
                    {
                        'id': 'free-rule-2',
                        'description': 'Free rule 2',
                        'match': {'usage.total_tokens': '>1000'},
                        'action': 'warn',
                        'severity': 'medium',
                        'suggestion': 'Reduce token usage',
                        'requires_license': False
                    }
                ]
            }
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            engine = PolicyEngine(Path(policy_file))
            
            # Set up global license checker with no license
            checker = get_license_checker()
            original_key = checker.license_key
            checker.license_key = None
            
            log_entries = [
                {'model': 'gpt-4', 'usage': {'total_tokens': 2000}}
            ]
            
            violations, skipped_rules = engine.evaluate_logs(log_entries, strict_license=False)
            
            # Should have 2 violations (both rules run), 0 skipped
            self.assertEqual(len(violations), 2)
            self.assertEqual(len(skipped_rules), 0)
            
            # Check both rules fired
            rule_ids = [v.rule_id for v in violations]
            self.assertIn('free-rule-1', rule_ids)
            self.assertIn('free-rule-2', rule_ids)
            
            # Restore original state
            checker.license_key = original_key
            
        finally:
            os.unlink(policy_file)


class TestGlobalLicenseChecker(unittest.TestCase):
    """Test the global license checker functions"""
    
    def test_get_license_checker_singleton(self):
        """Test that get_license_checker returns singleton instance"""
        checker1 = get_license_checker()
        checker2 = get_license_checker()
        self.assertIs(checker1, checker2)
    
    def test_load_license_key_function(self):
        """Test the standalone load_license_key function"""
        with patch.dict(os.environ, {'CRASHLENS_LICENSE_KEY': 'FUNC-TEST-123'}):
            key = load_license_key()
            self.assertEqual(key, 'FUNC-TEST-123')
            
            # Check via the checker instance
            checker = get_license_checker()
            self.assertEqual(checker.license_source, 'Environment variable CRASHLENS_LICENSE_KEY')


class TestLicenseIntegration(unittest.TestCase):
    """Integration tests for license system with CLI"""
    
    def test_masked_key_in_banner(self):
        """Test that license keys are masked in CLI banners"""
        checker = LicenseChecker()
        checker.license_key = 'SECRET-LICENSE-KEY'
        checker.license_source = 'CLI argument'
        
        # Should not expose the full key
        masked = checker.mask_license_key()
        self.assertNotIn('SECRET', masked)
        self.assertNotIn('LICENSE', masked)
        self.assertTrue(masked.endswith('KEY'))
    
    def test_upgrade_suggestion_without_license(self):
        """Test that upgrade suggestions appear when no license"""
        checker = LicenseChecker()
        self.assertFalse(checker.is_licensed())
        
        # Should suggest upgrade paths
        features = checker.get_enabled_features()
        self.assertFalse(features['advanced_policy_rules'])  # No features without license


if __name__ == '__main__':
    unittest.main()
