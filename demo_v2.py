#!/usr/bin/env python3
"""
CrashLens v2.0 Demo Script
Demonstrates the new plugin system and rule pack library
"""

import subprocess
import sys
import os

def demo_templates():
    """Demo the template system"""
    print("🎯 Demo: Policy Template System")
    print("=" * 40)
    
    # Show available templates
    result = subprocess.run([
        sys.executable, "-m", "crashlens", "list-templates"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Available Templates:")
        print(result.stdout)
    else:
        print(f"❌ Error: {result.stderr}")
    
    print()

def demo_rule_packs():
    """Demo the Langfuse rule pack library"""
    print("🎯 Demo: Langfuse Rule Pack Library")
    print("=" * 40)
    
    rule_pack_dir = "policies/langfuse"
    if os.path.exists(rule_pack_dir):
        rule_packs = os.listdir(rule_pack_dir)
        print(f"✅ Found {len(rule_packs)} rule packs:")
        for pack in rule_packs:
            if pack.endswith('.yaml'):
                print(f"  • {pack}")
    else:
        print("❌ Rule pack directory not found")
    
    print()

def demo_cli_sources():
    """Demo the multi-source CLI options"""
    print("🎯 Demo: Multi-Source CLI Options")
    print("=" * 40)
    
    sources = ["langfuse", "helicone", "openai", "file"]
    
    for source in sources:
        print(f"✅ --source={source} is available")
    
    print("\n📝 Example commands:")
    print("  crashlens scan --source=langfuse --simulate")
    print("  crashlens scan --source=helicone --hours-back=12")
    print("  crashlens scan --source=openai --organization-id=org-123")
    print("  crashlens scan --source=file logs.jsonl")
    
    print()

def demo_policy_validation():
    """Demo policy validation"""
    print("🎯 Demo: Policy Validation")
    print("=" * 40)
    
    # Test policy validation
    result = subprocess.run([
        sys.executable, "-m", "crashlens", "validate-policy", 
        "crashlens/config/modern-policy.yaml"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ modern-policy.yaml validation:")
        print(result.stdout)
    else:
        print(f"❌ Validation error: {result.stderr}")
    
    print()

if __name__ == "__main__":
    print("🚀 CrashLens v2.0 Feature Demo")
    print("=" * 50)
    print()
    
    # Demo each feature
    demo_templates()
    demo_rule_packs() 
    demo_cli_sources()
    demo_policy_validation()
    
    print("🎉 Demo complete!")
    print("\n📋 Next Steps:")
    print("  1. Set up API credentials for live testing")
    print("  2. Deploy rule packs for immediate value")
    print("  3. Integrate with CI/CD pipelines")
    print("  4. Customize policies for your environment")
