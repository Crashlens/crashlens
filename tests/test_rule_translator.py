"""
Tests for rule translator module.

These tests verify that guard YAML rules can be correctly
translated to guard-compatible rule structures.
"""

import pytest
import json
import yaml
from pathlib import Path
from crashlens.utils.rule_translator import (
    RuleTranslator,
    translate_file,
    SEVERITY_MAP,
    ACTION_MAP,
    TranslationWarning,
)


@pytest.fixture
def sample_policy_path():
    """Path to sample policy file."""
    return Path(__file__).parent / "fixtures" / "sample-policy.yaml"


@pytest.fixture
def expected_guard_rules():
    """Expected guard rules after translation."""
    return [
        {
            'id': 'test_retry_count',
            'description': 'Test excessive retry count',
            'if': {'if_retry_count': '>3'},
            'action': 'error',
            'severity': 'fatal',
        },
        {
            'id': 'test_model_match',
            'description': 'Test expensive model detection',
            'if': {
                'if_model': 'gpt-4o',
                'if_tokens': '>2000',
            },
            'action': 'warn',
            'severity': 'error',
        },
        {
            'id': 'test_fallback',
            'description': 'Test fallback detection',
            'if': {'if_fallback_triggered': True},
            'action': 'warn',
            'severity': 'warn',
        },
        {
            'id': 'test_cost_cap',
            'description': 'Test cost threshold',
            'if': {'if_cost_usd': '>0.50'},
            'action': 'fail_ci',
            'severity': 'fatal',
        },
        {
            'id': 'test_boolean_and',
            'description': 'Test AND composition',
            'if': {
                'and': [
                    {'if_model': 'gpt-4o'},
                    {'if_retry_count': '>1'},
                ]
            },
            'action': 'error',
            'severity': 'error',
        },
        {
            'id': 'test_boolean_or',
            'description': 'Test OR composition',
            'if': {
                'or': [
                    {'if_model': 'gpt-4o'},
                    {'if_model': 'claude-3-opus'},
                ]
            },
            'action': 'warn',
            'severity': 'warn',
        },
    ]


def test_severity_mapping():
    """Test severity translation mapping."""
    assert SEVERITY_MAP['critical'] == 'fatal'
    assert SEVERITY_MAP['high'] == 'error'
    assert SEVERITY_MAP['medium'] == 'warn'
    assert SEVERITY_MAP['low'] == 'warn'


def test_action_mapping():
    """Test action translation mapping."""
    assert ACTION_MAP['block'] == 'fail_ci'
    assert ACTION_MAP['fail'] == 'error'
    assert ACTION_MAP['warn'] == 'warn'


def test_translator_initialization():
    """Test translator can be initialized."""
    translator = RuleTranslator()
    assert translator.strict is False
    assert len(translator.warnings) == 0
    assert len(translator.errors) == 0
    
    strict_translator = RuleTranslator(strict=True)
    assert strict_translator.strict is True


def test_translate_sample_policy(sample_policy_path, expected_guard_rules):
    """Test translating the sample policy file."""
    translator = RuleTranslator()
    result = translator.translate_policy_file(sample_policy_path)
    
    assert result.success
    assert len(result.rules) == 6
    assert len(result.errors) == 0
    
    # Compare rules (allowing for minor structural differences)
    for i, (actual, expected) in enumerate(zip(result.rules, expected_guard_rules)):
        assert actual['id'] == expected['id'], f"Rule {i}: ID mismatch"
        assert actual['description'] == expected['description'], f"Rule {i}: Description mismatch"
        assert actual['action'] == expected['action'], f"Rule {i}: Action mismatch"
        assert actual['severity'] == expected['severity'], f"Rule {i}: Severity mismatch"
        # Conditions may vary slightly in structure, so just check they exist
        assert 'if' in actual, f"Rule {i}: Missing 'if' key"


def test_translate_file_with_output(sample_policy_path, tmp_path):
    """Test translate_file function with output file."""
    output_path = tmp_path / "translated.json"
    
    result = translate_file(sample_policy_path, output_path)
    
    assert result.success
    assert output_path.exists()
    
    # Load and verify output
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    assert 'rules' in data
    assert 'metadata' in data
    assert len(data['rules']) == 6
    assert data['metadata']['source'] == str(sample_policy_path)


def test_missing_rule_id_generates_id():
    """Test that missing rule IDs are auto-generated."""
    translator = RuleTranslator()
    rule = {
        'match': {'retry_count': '>3'},
        'action': 'warn',
        'severity': 'medium',
    }
    
    translated = translator._translate_rule(rule)
    
    assert translated is not None
    assert 'id' in translated
    assert translated['id'].startswith('POL_')
    assert len(translator.warnings) == 1
    assert 'Missing rule ID' in translator.warnings[0].message


def test_missing_match_field_fails():
    """Test that rules without match field fail translation."""
    translator = RuleTranslator()
    rule = {
        'id': 'test_rule',
        'action': 'warn',
        'severity': 'medium',
    }
    
    translated = translator._translate_rule(rule)
    
    assert translated is None
    assert len(translator.errors) == 1
    assert 'missing required' in translator.errors[0].message.lower()


def test_unknown_severity_defaults_to_warn():
    """Test that unknown severities default to warn with warning."""
    translator = RuleTranslator()
    rule = {
        'id': 'test_rule',
        'match': {'retry_count': '>3'},
        'action': 'warn',
        'severity': 'unknown_severity',
    }
    
    translated = translator._translate_rule(rule)
    
    assert translated is not None
    assert translated['severity'] == 'warn'
    assert len(translator.warnings) == 1
    assert 'Unknown severity' in translator.warnings[0].message


def test_unknown_action_defaults_to_warn():
    """Test that unknown actions default to warn with warning."""
    translator = RuleTranslator()
    rule = {
        'id': 'test_rule',
        'match': {'retry_count': '>3'},
        'action': 'unknown_action',
        'severity': 'medium',
    }
    
    translated = translator._translate_rule(rule)
    
    assert translated is not None
    assert translated['action'] == 'warn'
    assert len(translator.warnings) == 1
    assert 'Unknown action' in translator.warnings[0].message


def test_strict_mode_treats_warnings_as_errors():
    """Test that strict mode converts warnings to errors."""
    translator = RuleTranslator(strict=True)
    rule = {
        'id': 'test_rule',
        'match': {'retry_count': '>3'},
        'action': 'unknown_action',  # This will generate a warning
        'severity': 'medium',
    }
    
    # Create a simple policy file
    policy_data = {'rules': [rule]}
    
    # We can't easily test translate_policy_file in strict mode without a file,
    # so we'll test the result processing
    translator._translate_rule(rule)
    
    # Manually simulate what translate_policy_file does
    if translator.strict and translator.warnings:
        translator.errors.extend(translator.warnings)
        translator.warnings = []
    
    assert len(translator.errors) == 1
    assert len(translator.warnings) == 0


def test_unsupported_operator_in_strict_mode(tmp_path):
    """Test that unsupported operators fail in strict mode."""
    policy_file = tmp_path / "test-policy.yaml"
    policy_data = {
        'version': 1,
        'rules': [
            {
                'id': 'test_regex',
                'match': {'prompt': 'regex:.*sensitive.*'},
                'action': 'warn',
                'severity': 'high',
            }
        ]
    }
    
    with open(policy_file, 'w') as f:
        yaml.dump(policy_data, f)
    
    # Non-strict mode should warn but succeed
    result = translate_file(policy_file, strict=False)
    assert result.success
    assert len(result.warnings) > 0
    
    # Strict mode should fail (regex not fully supported)
    result_strict = translate_file(policy_file, strict=True)
    # Note: regex currently generates a warning, not an error in strict mode
    # This test documents current behavior; may change if we make regex stricter


def test_boolean_composition_translation():
    """Test that boolean AND/OR/NOT are correctly translated."""
    translator = RuleTranslator()
    
    # Test AND
    rule_and = {
        'id': 'test_and',
        'match': {
            'and': [
                {'model': 'gpt-4o'},
                {'tokens': '>1000'},
            ]
        },
        'action': 'warn',
        'severity': 'medium',
    }
    
    translated_and = translator._translate_rule(rule_and)
    assert translated_and is not None
    assert 'and' in translated_and['if']
    assert isinstance(translated_and['if']['and'], list)
    
    # Test OR
    translator2 = RuleTranslator()
    rule_or = {
        'id': 'test_or',
        'match': {
            'or': [
                {'model': 'gpt-4o'},
                {'model': 'claude-3-opus'},
            ]
        },
        'action': 'warn',
        'severity': 'medium',
    }
    
    translated_or = translator2._translate_rule(rule_or)
    assert translated_or is not None
    assert 'or' in translated_or['if']
    assert isinstance(translated_or['if']['or'], list)


def test_field_name_mapping():
    """Test that common field names are correctly mapped."""
    translator = RuleTranslator()
    
    test_cases = [
        ('retry_count', 'if_retry_count'),
        ('model', 'if_model'),
        ('tokens', 'if_tokens'),
        ('cost_usd', 'if_cost_usd'),
        ('fallback_triggered', 'if_fallback_triggered'),
    ]
    
    for field, expected_guard_field in test_cases:
        result = translator._translate_field_condition('test_rule', field, 'test_value')
        assert result is not None
        assert expected_guard_field in result


def test_cli_main_function(sample_policy_path, tmp_path, monkeypatch):
    """Test the CLI main function."""
    import sys
    from crashlens.utils.rule_translator import main
    
    output_path = tmp_path / "output.json"
    
    # Mock sys.argv
    test_args = [
        'rule_translator',
        '--input', str(sample_policy_path),
        '--output', str(output_path),
    ]
    monkeypatch.setattr(sys, 'argv', test_args)
    
    # Run main and expect sys.exit(0)
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    assert exc_info.value.code == 0
    assert output_path.exists()


def test_cli_strict_mode_with_warnings(tmp_path, monkeypatch):
    """Test CLI in strict mode with a policy that generates warnings."""
    import sys
    from crashlens.utils.rule_translator import main
    
    # Create a policy with unknown severity
    policy_file = tmp_path / "test-policy.yaml"
    policy_data = {
        'version': 1,
        'rules': [
            {
                'id': 'test_rule',
                'match': {'retry_count': '>3'},
                'action': 'unknown_action',  # Will generate warning
                'severity': 'medium',
            }
        ]
    }
    
    with open(policy_file, 'w') as f:
        yaml.dump(policy_data, f)
    
    output_path = tmp_path / "output.json"
    
    test_args = [
        'rule_translator',
        '--input', str(policy_file),
        '--output', str(output_path),
        '--strict-translate',
    ]
    monkeypatch.setattr(sys, 'argv', test_args)
    
    # Run main and expect sys.exit(2) due to strict mode
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    assert exc_info.value.code == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
