"""
Tests for new features: HTML formatter, performance thresholds, and week-over-week delta
"""

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner
from crashlens.guard import format_html_report, eval_condition
from crashlens.cli import run_report


class TestHTMLFormatter:
    """Test HTML output formatter"""
    
    def test_html_formatter_no_violations(self):
        """HTML formatter handles zero violations correctly"""
        report = {
            "summary": {"total_rules": 2, "violations": 0},
            "rules": {
                "RL001": {"count": 0, "severity": "error", "description": "Test", "examples": []},
                "RL002": {"count": 0, "severity": "warn", "description": "Test 2", "examples": []}
            }
        }
        
        html = format_html_report(report, "test.jsonl")
        
        assert "<!DOCTYPE html>" in html
        assert "CrashLens Guard Report" in html
        assert "No violations detected" in html
        assert "✅" in html
    
    def test_html_formatter_with_violations(self):
        """HTML formatter renders violations with color-coded severity"""
        report = {
            "summary": {"total_rules": 2, "violations": 2},
            "rules": {
                "RL001": {
                    "count": 1,
                    "severity": "critical",
                    "description": "High cost",
                    "examples": [{
                        "timestamp": "2025-01-15T10:00:00Z",
                        "model": "gpt-4o",
                        "tokens": 3000,
                        "retry_count": 0,
                        "fallback_triggered": False,
                        "endpoint": "/api/chat"
                    }]
                },
                "RL002": {
                    "count": 2,
                    "severity": "medium",
                    "description": "Moderate retries",
                    "examples": []
                }
            }
        }
        
        html = format_html_report(report, "test.jsonl")
        
        # Check structure
        assert "<!DOCTYPE html>" in html
        assert "<html lang=\"en\">" in html
        assert "CrashLens Guard Report" in html
        
        # Check violations rendered
        assert "RL001" in html
        assert "High cost" in html
        assert "gpt-4o" in html
        assert "3000" in html
        
        # Check severity badge
        assert "CRITICAL" in html or "critical" in html.lower()
        assert "MEDIUM" in html or "medium" in html.lower()
        
        # Check inline styles for email compatibility
        assert "background-color" in html or "border-left-color" in html
        assert "#dc3545" in html  # Critical red color


class TestPerformanceThresholds:
    """Test performance threshold conditions"""
    
    def test_eval_condition_response_time_gt(self):
        """Response time threshold condition works correctly"""
        cond = {"if_response_time_gt": 5000}
        
        # Slow response (should match)
        entry_slow = {"response_time_ms": 6000.0}
        assert eval_condition(cond, entry_slow) is True
        
        # Fast response (should not match)
        entry_fast = {"response_time_ms": 3000.0}
        assert eval_condition(cond, entry_fast) is False
        
        # Missing field (defaults to 0, should not match)
        entry_missing = {}
        assert eval_condition(cond, entry_missing) is False
    
    def test_eval_condition_error_rate_gt(self):
        """Error rate threshold condition works correctly"""
        cond = {"if_error_rate_gt": 10.0}
        
        # High error rate (should match)
        entry_high = {"error_rate": 15.5}
        assert eval_condition(cond, entry_high) is True
        
        # Low error rate (should not match)
        entry_low = {"error_rate": 5.0}
        assert eval_condition(cond, entry_low) is False
        
        # Missing field (defaults to 0, should not match)
        entry_missing = {}
        assert eval_condition(cond, entry_missing) is False
    
    def test_eval_condition_combined_performance(self):
        """Multiple performance conditions work together (AND logic)"""
        cond = {
            "if_response_time_gt": 5000,
            "if_error_rate_gt": 10.0,
            "if_retry_count_gt": 1
        }
        
        # All conditions match
        entry_match = {
            "response_time_ms": 6000.0,
            "error_rate": 12.0,
            "retry_count": 3
        }
        assert eval_condition(cond, entry_match) is True
        
        # Only some conditions match (should fail)
        entry_partial = {
            "response_time_ms": 6000.0,
            "error_rate": 8.0,  # Below threshold
            "retry_count": 3
        }
        assert eval_condition(cond, entry_partial) is False


class TestWeekOverWeekDelta:
    """Test week-over-week comparison in report command"""
    
    def setup_method(self):
        """Create temporary log files for testing"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create current period logs
        self.current_logs = Path(self.temp_dir) / "current.jsonl"
        with open(self.current_logs, "w") as f:
            f.write(json.dumps({
                "model": "gpt-4o",
                "tokens": 1000,
                "cost_usd": 0.05,
                "endpoint": "/api/chat",
                "retry_count": 0,
                "fallback_triggered": False
            }) + "\n")
            f.write(json.dumps({
                "model": "gpt-3.5-turbo",
                "tokens": 500,
                "cost_usd": 0.01,
                "endpoint": "/api/chat",
                "retry_count": 1,
                "fallback_triggered": False
            }) + "\n")
        
        # Create previous period logs (lower cost)
        self.previous_logs = Path(self.temp_dir) / "previous.jsonl"
        with open(self.previous_logs, "w") as f:
            f.write(json.dumps({
                "model": "gpt-3.5-turbo",
                "tokens": 300,
                "cost_usd": 0.02,
                "endpoint": "/api/chat",
                "retry_count": 0,
                "fallback_triggered": False
            }) + "\n")
    
    def test_report_without_previous_logs(self):
        """Report works without previous logs (baseline)"""
        result = self.runner.invoke(run_report, [
            str(self.current_logs),
            "--output", "text"
        ])
        
        assert result.exit_code == 0
        assert "Total Spend: $0.06" in result.output
        assert "↑" not in result.output  # No trend indicator
        assert "↓" not in result.output
        assert "Week-over-Week" not in result.output
    
    def test_report_with_previous_logs_increase(self):
        """Report shows increase trend when costs go up"""
        result = self.runner.invoke(run_report, [
            str(self.current_logs),
            "--output", "text",
            "--previous-logs", str(self.previous_logs)
        ])
        
        assert result.exit_code == 0
        assert "Total Spend: $0.06" in result.output
        assert "↑" in result.output  # Increase indicator
        assert "Week-over-Week Comparison:" in result.output
        assert "Previous: $0.02" in result.output
        assert "Current: $0.06" in result.output
        assert "+200.0%" in result.output  # 3x increase
    
    def test_report_with_previous_logs_markdown(self):
        """Markdown output includes delta formatting"""
        result = self.runner.invoke(run_report, [
            str(self.current_logs),
            "--output", "md",
            "--previous-logs", str(self.previous_logs)
        ])
        
        assert result.exit_code == 0
        assert "**Total Spend**: $0.06" in result.output
        assert "↑" in result.output
        assert "### 📈 Week-over-Week Comparison" in result.output
        assert "+200.0%" in result.output
    
    def test_report_with_previous_logs_slack(self):
        """Slack output includes delta in spend field"""
        result = self.runner.invoke(run_report, [
            str(self.current_logs),
            "--output", "slack",
            "--previous-logs", str(self.previous_logs)
        ])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_json = json.loads(result.output)
        blocks = output_json["blocks"]
        
        # Find the spend field
        spend_field = None
        for block in blocks:
            if block.get("type") == "section" and "fields" in block:
                for field in block["fields"]:
                    if "*Total Spend:*" in field.get("text", ""):
                        spend_field = field["text"]
                        break
        
        assert spend_field is not None
        assert "$0.06" in spend_field
        assert "↑" in spend_field
        assert "+200.0%" in spend_field
    
    def test_report_with_previous_logs_decrease(self):
        """Report shows decrease trend when costs go down"""
        # Swap the files so current is lower than previous
        result = self.runner.invoke(run_report, [
            str(self.previous_logs),  # Lower cost as "current"
            "--output", "text",
            "--previous-logs", str(self.current_logs)  # Higher cost as "previous"
        ])
        
        assert result.exit_code == 0
        assert "↓" in result.output  # Decrease indicator
        assert "-66.7%" in result.output  # Approximate decrease
    
    def test_report_handles_missing_previous_file(self):
        """Report gracefully handles missing previous logs file"""
        result = self.runner.invoke(run_report, [
            str(self.current_logs),
            "--output", "text",
            "--previous-logs", str(Path(self.temp_dir) / "nonexistent.jsonl")
        ])
        
        # Click will exit with code 2 for missing file (expected behavior)
        assert result.exit_code == 2
        # Should show error message
        assert "does not exist" in result.output.lower() or "error" in result.output.lower()


class TestGuardWithNewConditions:
    """Integration tests for guard with performance threshold rules"""
    
    def test_guard_with_performance_rules(self):
        """Guard command works with new performance threshold conditions"""
        from crashlens.guard import guard
        
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create test logs with performance metrics
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({
                    "model": "gpt-4o",
                    "tokens": 1000,
                    "cost_usd": 0.05,
                    "response_time_ms": 6000.0,
                    "error_rate": 15.0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "prompt": "test prompt"
                }) + "\n")
            
            # Create rules with performance thresholds
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: PERF001
    description: "Slow response time"
    if:
      if_response_time_gt: 5000
    action: warn
    severity: warn
  
  - id: PERF002
    description: "High error rate"
    if:
      if_error_rate_gt: 10
    action: error
    severity: error
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--output", "text"
            ])
            
            assert result.exit_code == 0
            assert "PERF001" in result.output
            assert "PERF002" in result.output
            assert "Slow response time" in result.output
            assert "High error rate" in result.output


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
