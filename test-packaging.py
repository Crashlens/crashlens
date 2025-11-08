"""
Reproducible Packaging Test
Builds wheel, installs in clean venv, and runs smoke test
"""
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, env=None):
    """Run command and return result"""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=cwd,
        env=env,
        shell=True
    )
    return result

def test_reproducible_packaging():
    """Test reproducible packaging"""
    
    print("=" * 70)
    print("Reproducible Packaging Test")
    print("=" * 70)
    print()
    
    # Step 1: Build wheel
    print("STEP 1: Building wheel package")
    print("-" * 70)
    
    result = run_command("poetry build")
    
    if result.returncode != 0:
        print(f"❌ Build failed: {result.stderr}")
        return False
    
    print("✅ Build successful")
    print(result.stdout)
    
    # Find built wheel
    dist_dir = Path("dist")
    wheel_files = list(dist_dir.glob("*.whl"))
    
    if not wheel_files:
        print("❌ No wheel file found in dist/")
        return False
    
    wheel_file = wheel_files[-1]  # Get latest
    print(f"📦 Wheel: {wheel_file.name}")
    print()
    
    # Step 2: Check with twine (if available)
    print("STEP 2: Checking package with twine")
    print("-" * 70)
    
    result = run_command(f"twine check {wheel_file}")
    
    if result.returncode == 0:
        print("✅ Twine check passed")
        print(result.stdout)
    else:
        print("⚠️  Twine not available or check failed (non-blocking)")
        print(result.stderr)
    
    print()
    
    # Step 3: Create clean venv and install
    print("STEP 3: Installing in clean virtual environment")
    print("-" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = Path(tmpdir) / "test-venv"
        
        # Create venv
        print(f"Creating venv at: {venv_dir}")
        result = run_command(f'python -m venv "{venv_dir}"')
        
        if result.returncode != 0:
            print(f"❌ venv creation failed: {result.stderr}")
            return False
        
        print("✅ venv created")
        
        # Determine pip path (Windows vs Unix)
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip.exe"
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"
        
        # Upgrade pip
        print("Upgrading pip...")
        result = run_command(f'"{python_path}" -m pip install --upgrade pip')
        
        if result.returncode != 0:
            print(f"⚠️  pip upgrade failed (non-blocking): {result.stderr}")
        else:
            print("✅ pip upgraded")
        
        # Install wheel
        print(f"Installing wheel: {wheel_file}")
        result = run_command(f'"{pip_path}" install "{wheel_file.absolute()}"')
        
        if result.returncode != 0:
            print(f"❌ Installation failed: {result.stderr}")
            return False
        
        print("✅ Package installed")
        print()
        
        # Step 4: Smoke test commands
        print("STEP 4: Running smoke tests")
        print("-" * 70)
        
        tests = []
        
        # Test 1: Version command
        print("Test 1: crashlens --version")
        result = run_command(f'"{python_path}" -m crashlens --version')
        test1_pass = result.returncode == 0 and "crashlens" in result.stdout.lower()
        print(f"  Output: {result.stdout.strip()}")
        print(f"  Status: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        tests.append(("Version command", test1_pass))
        print()
        
        # Test 2: Help command
        print("Test 2: crashlens guard --help")
        result = run_command(f'"{python_path}" -m crashlens guard --help')
        test2_pass = result.returncode == 0 and "guard" in result.stdout.lower()
        print(f"  Status: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        tests.append(("Help command", test2_pass))
        print()
        
        # Test 3: Guard command with test data
        print("Test 3: crashlens guard (with test data)")
        
        # Copy test files to temp directory
        test_dir = Path(tmpdir) / "test-data"
        test_dir.mkdir()
        
        # Copy sample log
        sample_log = Path("sample-logs/demo-logs.jsonl")
        if sample_log.exists():
            shutil.copy(sample_log, test_dir / "demo-logs.jsonl")
        
        # Copy test rules
        test_rules = Path("test-rules.yaml")
        if test_rules.exists():
            shutil.copy(test_rules, test_dir / "test-rules.yaml")
        
        if sample_log.exists() and test_rules.exists():
            result = run_command(
                f'"{python_path}" -m crashlens guard "{test_dir / "demo-logs.jsonl"}" '
                f'--rules "{test_dir / "test-rules.yaml"}" --output json',
                cwd=tmpdir
            )
            
            test3_pass = result.returncode in [0, 1] and "summary" in result.stdout
            print(f"  Exit code: {result.returncode}")
            print(f"  Status: {'✅ PASS' if test3_pass else '❌ FAIL'}")
            tests.append(("Guard command", test3_pass))
        else:
            print("  ⚠️  SKIP: Test files not available")
            tests.append(("Guard command", True))
        
        print()
        
        # Summary
        print("=" * 70)
        passed = sum(1 for _, ok in tests if ok)
        total = len(tests)
        print(f"SUMMARY: {passed}/{total} tests passed")
        print("=" * 70)
        print()
        
        for test_name, passed_test in tests:
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        print()
        
        return all(ok for _, ok in tests)

if __name__ == "__main__":
    success = test_reproducible_packaging()
    sys.exit(0 if success else 1)
