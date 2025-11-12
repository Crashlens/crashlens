"""Validation script for all policy files."""

import sys
from pathlib import Path
from crashlens.policy.engine import PolicyEngine


def main():
    """Validate all policy files in the policies directory."""
    policies_dir = Path("policies")
    
    if not policies_dir.exists():
        print(f"❌ Policies directory not found: {policies_dir}")
        sys.exit(1)
    
    policy_files = sorted(policies_dir.glob("*.yaml"))
    
    if not policy_files:
        print(f"❌ No policy files found in {policies_dir}")
        sys.exit(1)
    
    print(f"🔍 Validating {len(policy_files)} policy files...\n")
    print("=" * 70)
    
    errors = []
    successes = []
    warnings = []
    
    for policy_file in policy_files:
        try:
            engine = PolicyEngine(policy_file)
            
            # Basic validation
            if len(engine.rules) == 0:
                errors.append((policy_file.name, "No rules found"))
                print(f"❌ {policy_file.name}: No rules found")
                continue
            
            # Check for global config
            has_global_config = bool(engine.global_config)
            has_cost_thresholds = bool(engine.cost_thresholds)
            has_fallback_monitoring = bool(engine.fallback_monitoring)
            
            # Check each rule
            for rule in engine.rules:
                if not hasattr(rule, 'id'):
                    errors.append((policy_file.name, f"Rule missing id"))
                    continue
                if not hasattr(rule, 'match'):
                    errors.append((policy_file.name, f"Rule {rule.id} missing match"))
                    continue
                if not hasattr(rule, 'action'):
                    errors.append((policy_file.name, f"Rule {rule.id} missing action"))
                    continue
                if not hasattr(rule, 'severity'):
                    errors.append((policy_file.name, f"Rule {rule.id} missing severity"))
                    continue
                if not hasattr(rule, 'suggestion') or len(rule.suggestion.strip()) < 10:
                    warnings.append((policy_file.name, f"Rule {rule.id} has short/missing suggestion"))
            
            successes.append(policy_file.name)
            
            # Print success with details
            print(f"✅ {policy_file.name}")
            print(f"   Rules: {len(engine.rules)}")
            print(f"   Max violations per rule: {engine.max_violations_per_rule}")
            
            if has_global_config:
                print(f"   Global config: {engine.global_config}")
            
            if has_cost_thresholds:
                warning_threshold = engine.cost_thresholds.get('warning_threshold', 'N/A')
                critical_threshold = engine.cost_thresholds.get('critical_threshold', 'N/A')
                print(f"   Cost thresholds: warning=${warning_threshold}, critical=${critical_threshold}")
            
            if has_fallback_monitoring:
                print(f"   Fallback monitoring: {engine.fallback_monitoring}")
            
            print()
            
        except Exception as e:
            errors.append((policy_file.name, str(e)))
            print(f"❌ {policy_file.name}")
            print(f"   Error: {e}")
            print()
    
    # Print warnings
    if warnings:
        print("\n⚠️  WARNINGS:")
        print("=" * 70)
        for filename, warning in warnings:
            print(f"   {filename}: {warning}")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Successful: {len(successes)}/{len(policy_files)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    print(f"❌ Failed: {len(errors)}/{len(policy_files)}")
    
    if errors:
        print("\n❌ ERRORS:")
        for filename, error in errors:
            print(f"   {filename}: {error}")
        sys.exit(1)
    else:
        print("\n🎉 All policies validated successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
