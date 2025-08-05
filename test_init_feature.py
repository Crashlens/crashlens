#!/usr/bin/env python3
"""
Test script for CrashLens v2.0 'crashlens init' feature
Tests the template scaffolding functionality
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the crashlens directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import the template mapping
try:
    from crashlens.cli import TEMPLATE_YAMLS
    
    print("🧪 Testing CrashLens v2.0 'crashlens init' feature")
    print("=" * 50)
    
    # Test 1: Verify all templates exist
    expected_templates = ["retry-limit", "fallback-escalation", "basic-safety", "cost-cap", "internal-only"]
    
    print("✅ Test 1: Template availability")
    for template in expected_templates:
        if template in TEMPLATE_YAMLS:
            content = TEMPLATE_YAMLS[template]
            rule_count = content.count('- id:')
            print(f"   ✅ {template}: {rule_count} rules, {len(content)} chars")
        else:
            print(f"   ❌ {template}: Missing!")
    
    print(f"\n📊 Total templates available: {len(TEMPLATE_YAMLS)}")
    
    # Test 2: Validate YAML structure
    print("\n✅ Test 2: YAML structure validation")
    import yaml
    
    for template_name, content in TEMPLATE_YAMLS.items():
        try:
            parsed = yaml.safe_load(content)
            if 'rules' in parsed and isinstance(parsed['rules'], list):
                print(f"   ✅ {template_name}: Valid YAML with {len(parsed['rules'])} rules")
            else:
                print(f"   ⚠️ {template_name}: Valid YAML but no rules section")
        except yaml.YAMLError as e:
            print(f"   ❌ {template_name}: Invalid YAML - {e}")
    
    # Test 3: Template content preview
    print("\n✅ Test 3: Template content preview")
    sample_template = "basic-safety"
    if sample_template in TEMPLATE_YAMLS:
        content = TEMPLATE_YAMLS[sample_template]
        lines = content.split('\n')[:10]  # First 10 lines
        print(f"\n📄 Preview of '{sample_template}' template:")
        for line in lines:
            print(f"   {line}")
        if len(content.split('\n')) > 10:
            print(f"   ... ({len(content.split('\n'))} total lines)")
    
    # Test 4: File writing simulation
    print(f"\n✅ Test 4: File writing simulation")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test-policy.yaml"
        test_content = TEMPLATE_YAMLS["retry-limit"]
        
        # Simulate writing file
        test_file.write_text(test_content, encoding='utf-8')
        
        # Verify file was created
        if test_file.exists():
            written_content = test_file.read_text(encoding='utf-8')
            if written_content == test_content:
                print(f"   ✅ File writing: Success")
                print(f"   📄 Test file: {test_file}")
                print(f"   📏 Size: {len(written_content)} bytes")
            else:
                print(f"   ❌ File writing: Content mismatch")
        else:
            print(f"   ❌ File writing: File not created")
    
    print(f"\n🎉 All tests completed!")
    print(f"\n💡 Usage examples:")
    print(f"   crashlens init --template basic-safety")
    print(f"   crashlens init --template cost-cap --output budget.yaml")
    print(f"   crashlens list-templates")
    print(f"   crashlens list-templates --verbose")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
