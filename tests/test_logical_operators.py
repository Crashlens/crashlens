#!/usr/bin/env python3
"""
Unit tests for logical operators (Step 5): all_of, any_of, not
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import evaluate_condition, guard


class TestEvaluateCondition:
    """Test evaluate_condition with logical operators."""
    
    def test_all_of_success(self):
        """all_of returns true when all conditions match."""
        cond = {
            "all_of": [
                {"if_model": "gpt-4"},
                {"if_tokens_gt": 100}
            ]
        }
        entry = {"model": "gpt-4", "tokens": 150}
        assert evaluate_condition(cond, entry) is True
    
    def test_all_of_failure(self):
        """all_of returns false if any condition fails."""
        cond = {
            "all_of": [
                {"if_model": "gpt-4"},
                {"if_tokens_gt": 100}
            ]
        }
        entry = {"model": "gpt-4", "tokens": 50}  # tokens too low
        assert evaluate_condition(cond, entry) is False
    
    def test_any_of_success(self):
        """any_of returns true if at least one condition matches."""
        cond = {
            "any_of": [
                {"if_model": "gpt-4"},
                {"if_model": "claude-3"}
            ]
        }
        entry = {"model": "claude-3"}
        assert evaluate_condition(cond, entry) is True
    
    def test_any_of_failure(self):
        """any_of returns false if no conditions match."""
        cond = {
            "any_of": [
                {"if_model": "gpt-4"},
                {"if_model": "claude-3"}
            ]
        }
        entry = {"model": "gpt-3.5-turbo"}
        assert evaluate_condition(cond, entry) is False
    
    def test_not_operator(self):
        """not operator negates condition result."""
        cond = {"not": {"if_model": "gpt-4"}}
        entry = {"model": "gpt-3.5-turbo"}
        assert evaluate_condition(cond, entry) is True
        
        entry = {"model": "gpt-4"}
        assert evaluate_condition(cond, entry) is False
    
    def test_and_alias_still_works(self):
        """Legacy 'and' syntax still works (backward compatibility)."""
        cond = {
            "and": [
                {"if_model": "gpt-4"},
                {"if_tokens_gt": 100}
            ]
        }
        entry = {"model": "gpt-4", "tokens": 150}
        assert evaluate_condition(cond, entry) is True
    
    def test_or_alias_still_works(self):
        """Legacy 'or' syntax still works (backward compatibility)."""
        cond = {
            "or": [
                {"if_model": "gpt-4"},
                {"if_model": "claude-3"}
            ]
        }
        entry = {"model": "claude-3"}
        assert evaluate_condition(cond, entry) is True
    
    def test_nested_all_of_any_of(self):
        """Nested logical operators work correctly."""
        cond = {
            "all_of": [
                {"if_cost_usd_gt": 0.10},
                {
                    "any_of": [
                        {"if_model": "gpt-4"},
                        {"if_retry_count_gt": 2}
                    ]
                }
            ]
        }
        
        # Match: cost high AND (model=gpt-4)
        entry = {"cost_usd": 0.20, "model": "gpt-4", "retry_count": 0}
        assert evaluate_condition(cond, entry) is True
        
        # Match: cost high AND (retry_count>2)
        entry = {"cost_usd": 0.20, "model": "gpt-3.5", "retry_count": 3}
        assert evaluate_condition(cond, entry) is True
        
        # No match: cost too low
        entry = {"cost_usd": 0.05, "model": "gpt-4", "retry_count": 3}
        assert evaluate_condition(cond, entry) is False
    
    def test_nested_not_with_all_of(self):
        """NOT combined with all_of."""
        cond = {
            "not": {
                "all_of": [
                    {"if_model": "gpt-4"},
                    {"if_tokens_gt": 1000}
                ]
            }
        }
        
        # True because NOT(model=gpt-4 AND tokens>1000) = NOT(false) = true
        entry = {"model": "gpt-4", "tokens": 500}
        assert evaluate_condition(cond, entry) is True
        
        # False because NOT(model=gpt-4 AND tokens>1000) = NOT(true) = false
        entry = {"model": "gpt-4", "tokens": 1500}
        assert evaluate_condition(cond, entry) is False
    
    def test_empty_all_of(self):
        """Empty all_of list returns true (vacuous truth)."""
        cond = {"all_of": []}
        entry = {"model": "gpt-4"}
        assert evaluate_condition(cond, entry) is True
    
    def test_empty_any_of(self):
        """Empty any_of list returns false (no match)."""
        cond = {"any_of": []}
        entry = {"model": "gpt-4"}
        assert evaluate_condition(cond, entry) is False
    
    def test_atomic_condition_still_works(self):
        """Simple atomic conditions work without operators."""
        cond = {"if_model": "gpt-4"}
        entry = {"model": "gpt-4"}
        assert evaluate_condition(cond, entry) is True
        
        entry = {"model": "gpt-3.5"}
        assert evaluate_condition(cond, entry) is False


class TestGuardWithLogicalOperators:
    """Test guard command with logical operators in rules."""
    
    @pytest.fixture
    def rules_with_logic(self, tmp_path):
        """Create rules file with logical operators."""
        rules_file = tmp_path / "logic-rules.yaml"
        rules_content = """
rules:
  - id: LOGIC_001
    description: "Test all_of"
    if:
      all_of:
        - if_model: "gpt-4"
        - if_tokens_gt: 1000
    action: fail_ci
    severity: error
  
  - id: LOGIC_002
    description: "Test any_of"
    if:
      any_of:
        - if_model: "claude-3"
        - if_cost_usd_gt: 0.50
    action: warn
    severity: warning
  
  - id: LOGIC_003
    description: "Test not"
    if:
      not:
        if_model: "gpt-3.5-turbo"
    action: warn
    severity: warning
"""
        rules_file.write_text(rules_content)
        return rules_file
    
    @pytest.fixture
    def sample_logs(self, tmp_path):
        """Create sample JSONL logs."""
        logs_file = tmp_path / "logs.jsonl"
        logs_content = """{"traceId": "t1", "model": "gpt-4", "tokens": 1500, "cost_usd": 0.30}
{"traceId": "t2", "model": "gpt-3.5-turbo", "tokens": 500, "cost_usd": 0.02}
{"traceId": "t3", "model": "claude-3", "tokens": 800, "cost_usd": 0.15}
{"traceId": "t4", "model": "gpt-4", "tokens": 500, "cost_usd": 0.10}
{"traceId": "t5", "model": "llama-2", "tokens": 2000, "cost_usd": 0.60}
"""
        logs_file.write_text(logs_content)
        return logs_file
    
    def test_guard_all_of_operator(self, tmp_path, rules_with_logic, sample_logs):
        """Guard correctly evaluates all_of rules."""
        runner = CliRunner()
        
        result = runner.invoke(guard, [
            str(sample_logs),
            '--rules', str(rules_with_logic),
            '--output', 'json'
        ])
        
        # Extract JSON
        output = result.output
        start_idx = output.find('{')
        end_idx = output.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            import json
            json_output = output[start_idx:end_idx+1]
            report = json.loads(json_output)
            
            # LOGIC_001: all_of (model=gpt-4 AND tokens>1000)
            # Matches: t1 (gpt-4, 1500 tokens)
            assert report['rules']['LOGIC_001']['count'] == 1
    
    def test_guard_any_of_operator(self, tmp_path, rules_with_logic, sample_logs):
        """Guard correctly evaluates any_of rules."""
        runner = CliRunner()
        
        result = runner.invoke(guard, [
            str(sample_logs),
            '--rules', str(rules_with_logic),
            '--output', 'json'
        ])
        
        output = result.output
        start_idx = output.find('{')
        end_idx = output.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            import json
            json_output = output[start_idx:end_idx+1]
            report = json.loads(json_output)
            
            # LOGIC_002: any_of (model=claude-3 OR cost>0.50)
            # Matches: t3 (claude-3), t5 (cost=0.60)
            assert report['rules']['LOGIC_002']['count'] == 2
    
    def test_guard_not_operator(self, tmp_path, rules_with_logic, sample_logs):
        """Guard correctly evaluates not rules."""
        runner = CliRunner()
        
        result = runner.invoke(guard, [
            str(sample_logs),
            '--rules', str(rules_with_logic),
            '--output', 'json'
        ])
        
        output = result.output
        start_idx = output.find('{')
        end_idx = output.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            import json
            json_output = output[start_idx:end_idx+1]
            report = json.loads(json_output)
            
            # LOGIC_003: not (model != gpt-3.5-turbo)
            # Matches: t1, t3, t4, t5 (all except t2)
            assert report['rules']['LOGIC_003']['count'] == 4


class TestComplexLogicalExpressions:
    """Test complex nested logical expressions."""
    
    def test_triple_nested(self):
        """Test deeply nested operators."""
        cond = {
            "all_of": [
                {"if_cost_usd_gt": 0.05},
                {
                    "any_of": [
                        {
                            "all_of": [
                                {"if_model": "gpt-4"},
                                {"if_tokens_gt": 1000}
                            ]
                        },
                        {"if_retry_count_gt": 3}
                    ]
                }
            ]
        }
        
        # Match: cost>0.05 AND ((model=gpt-4 AND tokens>1000) OR retry>3)
        entry = {"cost_usd": 0.10, "model": "gpt-4", "tokens": 1500, "retry_count": 0}
        assert evaluate_condition(cond, entry) is True
        
        entry = {"cost_usd": 0.10, "model": "gpt-3.5", "tokens": 500, "retry_count": 5}
        assert evaluate_condition(cond, entry) is True
        
        # No match: cost too low
        entry = {"cost_usd": 0.01, "model": "gpt-4", "tokens": 1500, "retry_count": 5}
        assert evaluate_condition(cond, entry) is False
    
    def test_multiple_nots(self):
        """Double NOT should cancel out."""
        cond = {
            "not": {
                "not": {"if_model": "gpt-4"}
            }
        }
        entry = {"model": "gpt-4"}
        assert evaluate_condition(cond, entry) is True
        
        entry = {"model": "gpt-3.5"}
        assert evaluate_condition(cond, entry) is False
