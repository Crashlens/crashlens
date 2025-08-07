#!/usr/bin/env python3
"""
Quick validation test for CrashLens v2.0 plugin system
Tests import paths and basic functionality without API calls
"""

def test_cli_imports():
    """Test that CLI imports work with all plugins"""
    try:
        import sys
        import os
        
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Test individual imports
        print("🧪 Testing CLI imports...")
        
        # Test base CLI
        from crashlens import cli
        print("✅ Base CLI import successful")
        
        # Test plugin clients
        from crashlens.langfuse_client import LangfuseClient
        print("✅ Langfuse client import successful")
        
        from crashlens.helicone_client import HeliconeClient  
        print("✅ Helicone client import successful")
        
        from crashlens.openai_client import OpenAIClient
        print("✅ OpenAI client import successful")
        
        # Test policy engine
        from crashlens.policy.engine import PolicyEngine
        print("✅ Policy engine import successful")
        
        print("\n🎉 All core imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_policy_files():
    """Test that all policy files can be loaded"""
    import os
    import yaml
    
    policy_files = [
        "crashlens/config/modern-policy.yaml",
        "crashlens/config/crashlens-policy.yaml", 
        "policies/langfuse/block-gpt4-on-summary.yaml",
        "policies/langfuse/retry-loop-detector.yaml",
        "policies/langfuse/max-cost-per-trace.yaml",
        "policies/langfuse/fallback-chain-detector.yaml",
        "policies/langfuse/ci-sample.yaml"
    ]
    
    print("🧪 Testing policy file parsing...")
    
    for policy_file in policy_files:
        if os.path.exists(policy_file):
            try:
                with open(policy_file, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
                print(f"✅ {os.path.basename(policy_file)} parses correctly")
            except Exception as e:
                print(f"❌ {policy_file}: {e}")
        else:
            print(f"⚠️  {policy_file} not found")
    
    print("\n🎉 Policy validation complete!")

def test_cli_help():
    """Test that CLI help works with new options"""
    try:
        import subprocess
        import sys
        
        # Get the current Python executable
        python_exe = sys.executable
        
        print("🧪 Testing CLI help output...")
        
        # Test basic help
        result = subprocess.run([
            python_exe, "-m", "crashlens", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Basic CLI help works")
            if "--source" in result.stdout:
                print("✅ --source option found in help")
            else:
                print("⚠️  --source option not found in help")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
        
    except Exception as e:
        print(f"❌ CLI test error: {e}")

if __name__ == "__main__":
    print("🚀 CrashLens v2.0 Plugin System Validation")
    print("=" * 50)
    
    # Test imports
    import_success = test_cli_imports()
    print()
    
    # Test policy files
    test_policy_files()
    print()
    
    # Test CLI (if imports work)
    if import_success:
        test_cli_help()
    
    print("\n" + "=" * 50)
    print("🎯 Validation complete!")
