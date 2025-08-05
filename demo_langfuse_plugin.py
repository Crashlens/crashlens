#!/usr/bin/env python3
"""
Live demonstration of CrashLens --source=langfuse plugin mode
"""

import os
import subprocess
from pathlib import Path

def show_cli_help():
    """Show the enhanced CLI help with new options"""
    print("🔍 CrashLens CLI with --source=langfuse Plugin")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            'C:/Users/LawLight/AppData/Local/pypoetry/Cache/virtualenvs/crashlens-vH6yKHau-py3.12/Scripts/python.exe',
            '-m', 'crashlens.cli', 'scan', '--help'
        ], capture_output=True, text=True, cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens')
        
        # Show relevant parts of help
        help_lines = result.stdout.split('\n')
        
        # Find and show the new options
        showing = False
        for line in help_lines:
            if '--source TEXT' in line:
                showing = True
            if showing and line.strip():
                print(f"   {line}")
            elif showing and not line.strip():
                break
        
        # Show additional options
        for line in help_lines:
            if '--hours-back' in line or '--limit' in line:
                print(f"   {line}")
                # Show the next line too (description)
                idx = help_lines.index(line)
                if idx + 1 < len(help_lines):
                    print(f"   {help_lines[idx + 1]}")
        
    except Exception as e:
        print(f"Error showing help: {e}")

def demonstrate_usage_patterns():
    """Show different usage patterns"""
    print("\n🚀 Usage Patterns")
    print("=" * 30)
    
    examples = [
        {
            'title': '1. Quick Langfuse Analysis',
            'command': 'crashlens scan --source=langfuse --simulate',
            'description': 'Fetch last 24h traces and simulate policy enforcement'
        },
        {
            'title': '2. Custom Time Window', 
            'command': 'crashlens scan --source=langfuse --hours-back=12 --limit=500',
            'description': 'Fetch last 12 hours, maximum 500 traces'
        },
        {
            'title': '3. File Path via --source',
            'command': 'crashlens scan --source=logs/traces.jsonl --simulate',
            'description': 'Use --source with explicit file path'
        },
        {
            'title': '4. Traditional File Argument',
            'command': 'crashlens scan logs/traces.jsonl --simulate',
            'description': 'Backward compatible file argument'
        },
        {
            'title': '5. Full Production Setup',
            'command': 'crashlens scan --source=langfuse --policy budget.yaml --slack-webhook $WEBHOOK',
            'description': 'Real enforcement with notifications'
        }
    ]
    
    for example in examples:
        print(f"\n📋 {example['title']}")
        print(f"   Command: {example['command']}")
        print(f"   Purpose: {example['description']}")

def test_error_handling():
    """Demonstrate error handling"""
    print("\n🛡️ Error Handling Demonstration")
    print("=" * 40)
    
    # Test 1: No arguments
    print("\n1. Testing with no arguments:")
    try:
        result = subprocess.run([
            'C:/Users/LawLight/AppData/Local/pypoetry/Cache/virtualenvs/crashlens-vH6yKHau-py3.12/Scripts/python.exe',
            '-m', 'crashlens.cli', 'scan'
        ], capture_output=True, text=True, cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens', timeout=5)
        
        print("   Output:", result.stderr.strip())
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Missing Langfuse credentials
    print("\n2. Testing Langfuse without credentials:")
    try:
        # Temporarily remove credentials if they exist
        old_key = os.environ.pop('LANGFUSE_PUBLIC_KEY', None)
        old_secret = os.environ.pop('LANGFUSE_SECRET_KEY', None)
        
        result = subprocess.run([
            'C:/Users/LawLight/AppData/Local/pypoetry/Cache/virtualenvs/crashlens-vH6yKHau-py3.12/Scripts/python.exe',
            '-c', 'from crashlens.langfuse_client import test_langfuse_connection; test_langfuse_connection()'
        ], capture_output=True, text=True, cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens', timeout=5)
        
        print("   Output:", result.stdout.strip())
        
        # Restore credentials
        if old_key:
            os.environ['LANGFUSE_PUBLIC_KEY'] = old_key
        if old_secret:
            os.environ['LANGFUSE_SECRET_KEY'] = old_secret
            
    except Exception as e:
        print(f"   Error: {e}")

def test_working_functionality():
    """Test functionality that should work"""
    print("\n✅ Working Functionality Test")
    print("=" * 35)
    
    # Test with existing log file
    log_file = r"c:\Users\LawLight\OneDrive\Desktop\crashlens\examples-logs\demo-logs.jsonl"
    
    if Path(log_file).exists():
        print(f"\n📂 Testing with existing log file: {Path(log_file).name}")
        
        try:
            result = subprocess.run([
                'C:/Users/LawLight/AppData/Local/pypoetry/Cache/virtualenvs/crashlens-vH6yKHau-py3.12/Scripts/python.exe',
                '-m', 'crashlens.cli', 'scan', 
                f'--source={log_file}', 
                '--simulate', 
                '--verbose'
            ], capture_output=True, text=True, cwd='c:\\Users\\LawLight\\OneDrive\\Desktop\\crashlens', timeout=10)
            
            if result.returncode == 0:
                print("   ✅ Success! Output:")
                # Show key lines from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ['📂', '📋', '📊', '🔍', '🚧', '✅']):
                        print(f"      {line}")
            else:
                print(f"   ❌ Failed with error: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print("   ⏰ Timeout (expected for some operations)")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print(f"   ⚠️  Test log file not found: {log_file}")

def main():
    """Run the demonstration"""
    print("🧪 CrashLens --source=langfuse Plugin Demo")
    print("=" * 50)
    
    show_cli_help()
    demonstrate_usage_patterns()
    test_error_handling()
    test_working_functionality()
    
    print("\n" + "=" * 50)
    print("🎉 Plugin Implementation Complete!")
    print("\n💡 To use with real Langfuse data:")
    print("   export LANGFUSE_PUBLIC_KEY='pk-your-key'")
    print("   export LANGFUSE_SECRET_KEY='sk-your-secret'")
    print("   crashlens scan --source=langfuse --simulate")

if __name__ == "__main__":
    main()
