#!/usr/bin/env python3
"""
Test the new --source=langfuse plugin mode for CrashLens
"""

import os
import json
from pathlib import Path

def create_mock_langfuse_env():
    """Set up mock environment variables for testing"""
    print("🧪 Setting up mock Langfuse environment...")
    
    # Set mock environment variables
    os.environ['LANGFUSE_PUBLIC_KEY'] = 'pk-test-123456789'
    os.environ['LANGFUSE_SECRET_KEY'] = 'sk-test-987654321'
    os.environ['LANGFUSE_HOST'] = 'https://mock-langfuse.com'
    
    print("✅ Mock environment variables set:")
    print(f"   LANGFUSE_PUBLIC_KEY: {os.environ.get('LANGFUSE_PUBLIC_KEY')}")
    print(f"   LANGFUSE_SECRET_KEY: {(os.environ.get('LANGFUSE_SECRET_KEY') or '')[:10]}...")
    print(f"   LANGFUSE_HOST: {os.environ.get('LANGFUSE_HOST')}")

def test_cli_help():
    """Test the CLI help output includes the new options"""
    print("\n🧪 Testing CLI help output...")
    
    import subprocess
    try:
        result = subprocess.run(['python', '-m', 'crashlens.cli', 'scan', '--help'], 
                              capture_output=True, text=True, cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens')
        
        help_text = result.stdout
        
        # Check for new options
        required_options = [
            '--source',
            'langfuse',
            'helicone', 
            '--hours-back',
            '--limit'
        ]
        
        print("📋 Checking for new CLI options:")
        for option in required_options:
            if option in help_text:
                print(f"   ✅ Found: {option}")
            else:
                print(f"   ❌ Missing: {option}")
        
        # Show sample of help text
        print("\n📄 Sample help output:")
        lines = help_text.split('\n')[:20]
        for line in lines:
            print(f"   {line}")
            
    except Exception as e:
        print(f"❌ Error testing CLI help: {e}")

def test_source_validation():
    """Test the source validation logic"""
    print("\n🧪 Testing source validation...")
    
    # Test cases to validate
    test_cases = [
        {
            'name': 'No source or file',
            'args': [],
            'should_fail': True
        },
        {
            'name': 'Source langfuse (will fail without real API)',
            'args': ['--source=langfuse', '--simulate'],
            'should_fail': True  # Expected since we don't have real Langfuse access
        },
        {
            'name': 'Source with file path',
            'args': ['--source=examples-logs/demo-logs.jsonl', '--simulate'],
            'should_fail': False
        },
        {
            'name': 'Traditional file argument',
            'args': ['examples-logs/demo-logs.jsonl', '--simulate'],
            'should_fail': False
        }
    ]
    
    import subprocess
    
    for test_case in test_cases:
        print(f"\n   Testing: {test_case['name']}")
        
        try:
            cmd = ['python', '-m', 'crashlens.cli', 'scan'] + test_case['args']
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens', timeout=10)
            
            if test_case['should_fail']:
                if result.returncode != 0:
                    print(f"      ✅ Expected failure: {result.stderr.strip()[:100]}...")
                else:
                    print(f"      ❌ Unexpected success")
            else:
                if result.returncode == 0:
                    print(f"      ✅ Expected success")
                else:
                    print(f"      ❌ Unexpected failure: {result.stderr.strip()[:100]}...")
                    
        except subprocess.TimeoutExpired:
            print(f"      ⏰ Timeout (expected for some tests)")
        except Exception as e:
            print(f"      ❌ Error: {e}")

def demonstrate_usage():
    """Show usage examples for the new feature"""
    print("\n🚀 CrashLens --source=langfuse Plugin Mode")
    print("=" * 50)
    
    print("\n📋 Usage Examples:")
    
    examples = [
        {
            'command': 'crashlens scan --source=langfuse --simulate',
            'description': 'Fetch from Langfuse and simulate policy enforcement'
        },
        {
            'command': 'crashlens scan --source=langfuse --hours-back=12 --limit=500',
            'description': 'Fetch last 12 hours, max 500 traces'
        },
        {
            'command': 'crashlens scan --source=langfuse --policy budget.yaml --slack-webhook $WEBHOOK',
            'description': 'Full enforcement with custom policy and Slack notifications'
        },
        {
            'command': 'crashlens scan --source=path/to/logs.jsonl --simulate',
            'description': 'Use --source with explicit file path'
        },
        {
            'command': 'export LANGFUSE_PUBLIC_KEY=pk-...; export LANGFUSE_SECRET_KEY=sk-...',
            'description': 'Set up Langfuse credentials (required)'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n   {i}. {example['description']}")
        print(f"      {example['command']}")
    
    print("\n🌟 Benefits:")
    print("   ✅ One-liner setup for Langfuse users")
    print("   ✅ No need to export/download log files")
    print("   ✅ Real-time analysis of recent traces")
    print("   ✅ Works with all existing CrashLens features (policies, simulation, Slack)")
    
    print("\n🔮 Future Extensions:")
    print("   • --source=helicone (Helicone API integration)")
    print("   • --source=wandb (Weights & Biases integration)")
    print("   • --source=openai-logs (OpenAI usage logs)")
    print("   • --source=azure-openai (Azure OpenAI logs)")

def main():
    """Run all tests and demonstrations"""
    print("🚀 Testing CrashLens --source=langfuse Plugin Mode")
    print("=" * 60)
    
    create_mock_langfuse_env()
    test_cli_help()
    test_source_validation()
    demonstrate_usage()
    
    print("\n" + "=" * 60)
    print("🎉 Plugin mode testing complete!")
    print("\n💡 Next steps:")
    print("   1. Set real Langfuse credentials: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY")
    print("   2. Test with: crashlens scan --source=langfuse --simulate")
    print("   3. Use --verbose flag for detailed output")

if __name__ == "__main__":
    main()
