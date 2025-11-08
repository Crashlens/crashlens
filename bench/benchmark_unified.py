#!/usr/bin/env python3
"""
CrashLens Unified Engine Performance Benchmark (Cross-Platform)

Compares legacy guard vs unified engine performance with proper metrics collection.
Works on Windows, Linux, and macOS.
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import psutil
except ImportError:
    print("Warning: psutil not installed. Memory tracking will be limited.")
    psutil = None


@dataclass
class BenchmarkResult:
    """Stores benchmark results for a single run"""
    name: str
    wall_time: float
    cpu_time: float
    peak_memory_mb: float
    exit_code: int
    output_size: int
    timestamp: str


class PerformanceBenchmark:
    """Main benchmark runner"""
    
    # Performance thresholds from spec
    MAX_TIME_OVERHEAD_PERCENT = 15
    MAX_MEMORY_OVERHEAD_PERCENT = 25
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logs_dir = project_root / "sample-logs"
        self.results_dir = project_root / "bench" / "results"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results: List[BenchmarkResult] = []
        
        # Create results directory
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_command(self, name: str, cmd: List[str]) -> BenchmarkResult:
        """Run a command and collect performance metrics"""
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*60}")
        
        # Start time
        start_time = time.time()
        start_cpu = time.process_time()
        
        # Track memory if psutil available
        peak_memory_mb = 0.0
        if psutil:
            process = None
            try:
                # Run process
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.project_root
                )
                process = psutil.Process(proc.pid)
                
                # Monitor memory usage
                while proc.poll() is None:
                    try:
                        mem_info = process.memory_info()
                        current_mb = mem_info.rss / (1024 * 1024)
                        peak_memory_mb = max(peak_memory_mb, current_mb)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    time.sleep(0.1)
                
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode
                output_size = len(stdout) + len(stderr)
                
            except Exception as e:
                print(f"Error running command: {e}")
                exit_code = -1
                output_size = 0
        else:
            # Fallback without memory tracking
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    cwd=self.project_root,
                    timeout=300
                )
                exit_code = result.returncode
                output_size = len(result.stdout) + len(result.stderr)
            except subprocess.TimeoutExpired:
                print("Command timed out after 300s")
                exit_code = -1
                output_size = 0
            except Exception as e:
                print(f"Error running command: {e}")
                exit_code = -1
                output_size = 0
        
        # Calculate elapsed time
        wall_time = time.time() - start_time
        cpu_time = time.process_time() - start_cpu
        
        result = BenchmarkResult(
            name=name,
            wall_time=wall_time,
            cpu_time=cpu_time,
            peak_memory_mb=peak_memory_mb,
            exit_code=exit_code,
            output_size=output_size,
            timestamp=self.timestamp
        )
        
        print(f"  Wall Time:   {wall_time:.3f}s")
        print(f"  CPU Time:    {cpu_time:.3f}s")
        print(f"  Peak Memory: {peak_memory_mb:.1f}MB")
        print(f"  Exit Code:   {exit_code}")
        
        self.results.append(result)
        return result
    
    def run_benchmarks(self):
        """Run all benchmark scenarios"""
        print("="*60)
        print("CrashLens Unified Engine Performance Benchmarks")
        print("="*60)
        print(f"Project Root: {self.project_root}")
        print(f"Results Dir:  {self.results_dir}")
        print(f"Timestamp:    {self.timestamp}")
        print("")
        
        # Check for test data
        test_log = self.logs_dir / "demo-logs.jsonl"
        if not test_log.exists():
            print(f"Error: demo-logs.jsonl not found at {test_log}")
            sys.exit(1)
        
        # Determine rules file
        rules_file = self.project_root / ".crashlens" / "rules.yaml"
        if not rules_file.exists():
            rules_file = self.project_root / "policies" / "retry-loop-detector.yaml"
        
        if not rules_file.exists():
            print(f"Error: No rules.yaml found")
            sys.exit(1)
        
        print(f"Using rules: {rules_file}")
        print(f"Using logs:  {test_log}")
        print("")
        
        # Common args
        common_args = [
            str(test_log),
            "--rules", str(rules_file),
            "--output", "json",
            "--dry-run"
        ]
        
        # Benchmark 1: Legacy Guard (Baseline)
        self.run_command(
            "legacy_guard",
            ["poetry", "run", "crashlens", "guard"] + common_args
        )
        
        # Benchmark 2: Unified Guard (via env var)
        env = os.environ.copy()
        env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        # Note: We need to modify run_command to accept env
        # For now, set it globally
        os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        self.run_command(
            "unified_guard_basic",
            ["poetry", "run", "crashlens", "guard"] + common_args
        )
        
        # Benchmark 3: Policy-Check (auto unified)
        self.run_command(
            "policy_check",
            ["poetry", "run", "crashlens", "policy-check"] + common_args
        )
        
        # Benchmark 4: Unified with detectors (future)
        # This is a placeholder for when detector flags are implemented
        self.run_command(
            "unified_guard_detectors",
            ["poetry", "run", "crashlens", "policy-check"] + common_args
        )
        
        # Clean up env
        if 'CRASHLENS_USE_UNIFIED_ENGINE' in os.environ:
            del os.environ['CRASHLENS_USE_UNIFIED_ENGINE']
    
    def analyze_results(self):
        """Analyze benchmark results and check thresholds"""
        print("\n" + "="*60)
        print("Performance Analysis")
        print("="*60)
        
        if len(self.results) < 2:
            print("Not enough results to compare")
            return
        
        # Find baseline (legacy guard)
        baseline = next((r for r in self.results if r.name == "legacy_guard"), None)
        if not baseline:
            print("Error: No baseline (legacy_guard) result found")
            return
        
        # Find unified basic
        unified = next((r for r in self.results if r.name == "unified_guard_basic"), None)
        if not unified:
            unified = next((r for r in self.results if r.name == "policy_check"), None)
        
        if not unified:
            print("Error: No unified engine result found")
            return
        
        print(f"\nBaseline (Legacy Guard):")
        print(f"  Wall Time:   {baseline.wall_time:.3f}s")
        print(f"  CPU Time:    {baseline.cpu_time:.3f}s")
        print(f"  Peak Memory: {baseline.peak_memory_mb:.1f}MB")
        
        print(f"\nUnified Engine (Basic):")
        print(f"  Wall Time:   {unified.wall_time:.3f}s")
        print(f"  CPU Time:    {unified.cpu_time:.3f}s")
        print(f"  Peak Memory: {unified.peak_memory_mb:.1f}MB")
        
        # Calculate overhead
        time_overhead = ((unified.wall_time - baseline.wall_time) / baseline.wall_time) * 100
        memory_overhead = ((unified.peak_memory_mb - baseline.peak_memory_mb) / baseline.peak_memory_mb) * 100 if baseline.peak_memory_mb > 0 else 0
        
        print(f"\nOverhead:")
        print(f"  Time:   {time_overhead:+.1f}%")
        print(f"  Memory: {memory_overhead:+.1f}%")
        
        print(f"\nThresholds:")
        print(f"  Max Time Overhead:   ±{self.MAX_TIME_OVERHEAD_PERCENT}%")
        print(f"  Max Memory Overhead: ±{self.MAX_MEMORY_OVERHEAD_PERCENT}%")
        
        # Check pass/fail
        time_pass = abs(time_overhead) <= self.MAX_TIME_OVERHEAD_PERCENT
        memory_pass = abs(memory_overhead) <= self.MAX_MEMORY_OVERHEAD_PERCENT
        
        print(f"\nResults:")
        print(f"  Time Overhead:   {'✅ PASS' if time_pass else '❌ FAIL'}")
        print(f"  Memory Overhead: {'✅ PASS' if memory_pass else '❌ FAIL'}")
        
        overall_pass = time_pass and memory_pass
        print(f"\n{'='*60}")
        print(f"Overall: {'✅ BENCHMARKS PASSED' if overall_pass else '❌ BENCHMARKS FAILED'}")
        print(f"{'='*60}")
        
        return overall_pass
    
    def save_results(self):
        """Save results to JSON file"""
        output_file = self.results_dir / f"benchmark_{self.timestamp}.json"
        
        results_dict = {
            "timestamp": self.timestamp,
            "thresholds": {
                "max_time_overhead_percent": self.MAX_TIME_OVERHEAD_PERCENT,
                "max_memory_overhead_percent": self.MAX_MEMORY_OVERHEAD_PERCENT
            },
            "results": [
                {
                    "name": r.name,
                    "wall_time": r.wall_time,
                    "cpu_time": r.cpu_time,
                    "peak_memory_mb": r.peak_memory_mb,
                    "exit_code": r.exit_code,
                    "output_size": r.output_size,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point"""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"CrashLens Performance Benchmarks")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("")
    
    # Create benchmark runner
    benchmark = PerformanceBenchmark(project_root)
    
    # Run benchmarks
    try:
        benchmark.run_benchmarks()
        benchmark.analyze_results()
        benchmark.save_results()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError running benchmarks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
