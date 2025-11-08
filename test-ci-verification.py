"""
CI Pipeline Verification
Checks that all GitHub Actions workflows are using guard correctly
"""
import sys
from pathlib import Path
import yaml

def verify_ci_pipelines():
    """Verify CI pipelines use guard correctly"""
    
    print("=" * 70)
    print("CI Pipeline Verification")
    print("=" * 70)
    print()
    
    workflows_dir = Path(".github/workflows")
    
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return False
    
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    if not workflow_files:
        print("❌ No workflow files found")
        return False
    
    print(f"Found {len(workflow_files)} workflow files")
    print()
    
    issues = []
    passed = 0
    
    for workflow_file in workflow_files:
        print(f"Checking: {workflow_file.name}")
        print("-" * 70)
        
        try:
            content = workflow_file.read_text(encoding='utf-8', errors='replace')
            
            # Check for policy-check references
            if "policy-check" in content.lower():
                issues.append(f"{workflow_file.name}: Contains 'policy-check' reference")
                print("  ❌ Contains 'policy-check' reference")
            else:
                print("  ✅ No 'policy-check' references")
            
            # Check if it uses guard
            if "crashlens guard" in content:
                print("  ✅ Uses 'crashlens guard'")
                
                # Parse YAML to check structure
                try:
                    workflow_data = yaml.safe_load(content)
                    
                    # Check for GUARD_ENFORCE awareness (optional but good)
                    if "GUARD_ENFORCE" in content:
                        print("  ✅ GUARD_ENFORCE aware")
                    else:
                        print("  ℹ️  Not using GUARD_ENFORCE (optional)")
                    
                    # Check for fail-on-violations flag
                    if "--fail-on-violations" in content:
                        print("  ✅ Uses --fail-on-violations")
                    else:
                        print("  ⚠️  Not using --fail-on-violations")
                    
                except yaml.YAMLError as e:
                    print(f"  ⚠️  Could not parse YAML: {e}")
            
            elif "crashlens" in content:
                print("  ℹ️  Uses crashlens (not guard specifically)")
            else:
                print("  ℹ️  Does not use crashlens")
            
            print()
            passed += 1
            
        except Exception as e:
            issues.append(f"{workflow_file.name}: Error reading file: {e}")
            print(f"  ❌ Error: {e}")
            print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Workflows checked: {len(workflow_files)}")
    print(f"Issues found: {len(issues)}")
    print()
    
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  ❌ {issue}")
        print()
        return False
    else:
        print("✅ All workflows verified successfully")
        print()
        return True

if __name__ == "__main__":
    success = verify_ci_pipelines()
    sys.exit(0 if success else 1)
