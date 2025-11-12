"""Test that all policy files are valid and load correctly."""

import pytest
from pathlib import Path
from crashlens.policy.engine import PolicyEngine


@pytest.fixture
def policies_dir():
    """Return path to policies directory."""
    return Path(__file__).parent.parent / "policies"


def test_all_policies_load(policies_dir):
    """Test that all policy files load without errors."""
    policy_files = list(policies_dir.glob("*.yaml"))
    assert len(policy_files) > 0, "No policy files found"
    
    errors = []
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            # Verify basic structure
            assert hasattr(engine, 'rules'), f"{policy_file.name}: No rules found"
            assert len(engine.rules) > 0, f"{policy_file.name}: Empty rules list"
            
            # Verify rule structure
            for rule in engine.rules:
                assert hasattr(rule, 'id'), f"{policy_file.name}: Rule missing id"
                assert hasattr(rule, 'description'), f"{policy_file.name}: Rule missing description"
                assert hasattr(rule, 'match'), f"{policy_file.name}: Rule missing match conditions"
                
        except Exception as e:
            errors.append(f"{policy_file.name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Policy loading errors:\n" + "\n".join(errors))


def test_policy_global_settings(policies_dir):
    """Test that global settings are properly loaded."""
    policy_file = policies_dir / "fallback-chain-detector.yaml"
    if not policy_file.exists():
        pytest.skip(f"Policy file {policy_file.name} not found")
    
    engine = PolicyEngine(policy_file)
    
    # Verify global settings
    assert hasattr(engine, 'global_config'), "Missing global_config"
    assert engine.max_violations_per_rule > 0, "Invalid max_violations_per_rule"
    assert hasattr(engine, 'cost_thresholds'), "Missing cost_thresholds"


def test_policy_match_operators(policies_dir):
    """Test that all match operators are valid."""
    valid_operators = {">", ">=", "<", "<=", "==", "!=", "in:", "not_in:", "regex:", "not_empty", "empty"}
    
    policy_files = list(policies_dir.glob("*.yaml"))
    invalid_operators = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            for rule in engine.rules:
                for field, condition in rule.match.items():
                    if isinstance(condition, str):
                        # Extract operator
                        operator = None
                        if condition.startswith("in:") or condition.startswith("not_in:") or condition.startswith("regex:"):
                            operator = condition.split(":")[0] + ":"
                        elif condition in ["not_empty", "empty"]:
                            operator = condition
                        elif any(condition.startswith(op) for op in [">", ">=", "<", "<=", "==", "!="]):
                            for op in [">=", "<=", "==", "!=", ">", "<"]:  # Check longer operators first
                                if condition.startswith(op):
                                    operator = op
                                    break
                        
                        if operator and operator not in valid_operators:
                            invalid_operators.append(
                                f"{policy_file.name}: Rule {rule.id}: Invalid operator '{operator}' in field '{field}'"
                            )
        except Exception as e:
            # Skip files that fail to load (will be caught by test_all_policies_load)
            pass
    
    if invalid_operators:
        pytest.fail(f"Invalid operators found:\n" + "\n".join(invalid_operators))


def test_policy_severity_levels(policies_dir):
    """Test that all severity levels are valid."""
    valid_severities = {"critical", "high", "medium", "low"}
    
    policy_files = list(policies_dir.glob("*.yaml"))
    invalid_severities = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            for rule in engine.rules:
                if hasattr(rule, 'severity'):
                    severity_value = rule.severity.value if hasattr(rule.severity, 'value') else str(rule.severity)
                    if severity_value not in valid_severities:
                        invalid_severities.append(
                            f"{policy_file.name}: Rule {rule.id}: Invalid severity '{severity_value}'"
                        )
        except Exception:
            pass
    
    if invalid_severities:
        pytest.fail(f"Invalid severities found:\n" + "\n".join(invalid_severities))


def test_policy_actions(policies_dir):
    """Test that all actions are valid."""
    valid_actions = {"fail", "warn", "block"}
    
    policy_files = list(policies_dir.glob("*.yaml"))
    invalid_actions = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            for rule in engine.rules:
                if hasattr(rule, 'action'):
                    action_value = rule.action.value if hasattr(rule.action, 'value') else str(rule.action)
                    if action_value not in valid_actions:
                        invalid_actions.append(
                            f"{policy_file.name}: Rule {rule.id}: Invalid action '{action_value}'"
                        )
        except Exception:
            pass
    
    if invalid_actions:
        pytest.fail(f"Invalid actions found:\n" + "\n".join(invalid_actions))


def test_policy_suggestions_present(policies_dir):
    """Test that all rules have suggestions."""
    policy_files = list(policies_dir.glob("*.yaml"))
    missing_suggestions = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            for rule in engine.rules:
                if not hasattr(rule, 'suggestion') or not rule.suggestion or len(rule.suggestion.strip()) < 10:
                    missing_suggestions.append(
                        f"{policy_file.name}: Rule {rule.id}: Missing or too short suggestion"
                    )
        except Exception:
            pass
    
    if missing_suggestions:
        pytest.fail(f"Missing/inadequate suggestions:\n" + "\n".join(missing_suggestions))


def test_policy_field_names(policies_dir):
    """Test that policy files don't use incorrect field names."""
    # Fields that should NOT appear (common mistakes)
    invalid_fields = {
        'input.model': 'Should be: model',
        'output.token_count': 'Should be: usage.completion_tokens',
        'input.prompt_tokens': 'Should be: usage.prompt_tokens',
        'status': 'Should be: level (for ERROR) or metadata.status',
        'duration': 'Should be: metadata.duration',
    }
    
    policy_files = list(policies_dir.glob("*.yaml"))
    field_errors = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            for rule in engine.rules:
                for field in rule.match.keys():
                    if field in invalid_fields:
                        field_errors.append(
                            f"{policy_file.name}: Rule {rule.id}: Invalid field '{field}' - {invalid_fields[field]}"
                        )
        except Exception:
            pass
    
    if field_errors:
        pytest.fail(f"Invalid field names found:\n" + "\n".join(field_errors))


def test_fixed_policies_load_correctly():
    """Test that the policies we specifically fixed load correctly."""
    policies_to_test = [
        "fallback-chain-detector.yaml",
        "block-gpt4-on-summary.yaml",
        "retry-loop-detector.yaml",
        "max-cost-per-trace.yaml",
        "ci-sample.yaml",
        "budget-protection.yaml",
        "model-overkill-detection.yaml",
        "fallback-storm-detection.yaml",
    ]
    
    policies_dir = Path(__file__).parent.parent / "policies"
    
    for policy_name in policies_to_test:
        policy_file = policies_dir / policy_name
        if not policy_file.exists():
            continue  # Skip if doesn't exist
            
        try:
            engine = PolicyEngine(policy_file)
            
            # Verify loaded successfully
            assert len(engine.rules) > 0, f"{policy_name}: No rules loaded"
            
            # Verify global config loaded (if present)
            assert hasattr(engine, 'global_config'), f"{policy_name}: Missing global_config"
            assert hasattr(engine, 'max_violations_per_rule'), f"{policy_name}: Missing max_violations_per_rule"
            
            print(f"✅ {policy_name}: {len(engine.rules)} rules loaded")
            
        except Exception as e:
            pytest.fail(f"❌ {policy_name} failed to load: {str(e)}")
