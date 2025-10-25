"""
Tests for boolean logic composition in guard rules (AND/OR/NOT)
"""

import pytest
from crashlens.guard import evaluate_condition


class TestBooleanComposition:
    """Test AND/OR/NOT boolean composition in rule conditions"""
    
    def test_simple_atomic_condition_backward_compat(self):
        """Simple atomic conditions still work (backward compatibility)"""
        cond = {"if_model": "gpt-4o"}
        entry = {"model": "gpt-4o"}
        
        assert evaluate_condition(cond, entry) is True
        
        entry_mismatch = {"model": "gpt-3.5-turbo"}
        assert evaluate_condition(cond, entry_mismatch) is False
    
    def test_implicit_and_backward_compat(self):
        """Multiple conditions in flat dict are implicitly AND-ed"""
        cond = {
            "if_model": "gpt-4o",
            "if_tokens_gt": 1000
        }
        
        # Both conditions match
        entry_match = {"model": "gpt-4o", "tokens": 1500}
        assert evaluate_condition(cond, entry_match) is True
        
        # Only one condition matches
        entry_partial = {"model": "gpt-4o", "tokens": 500}
        assert evaluate_condition(cond, entry_partial) is False
    
    def test_or_composition_basic(self):
        """OR triggers when either branch is true"""
        cond = {
            "or": [
                {"if_model": "gpt-4o"},
                {"if_model": "claude-3"}
            ]
        }
        
        # First condition matches
        entry1 = {"model": "gpt-4o"}
        assert evaluate_condition(cond, entry1) is True
        
        # Second condition matches
        entry2 = {"model": "claude-3"}
        assert evaluate_condition(cond, entry2) is True
        
        # Neither matches
        entry3 = {"model": "gpt-3.5-turbo"}
        assert evaluate_condition(cond, entry3) is False
    
    def test_or_composition_multiple_conditions(self):
        """OR with more than 2 conditions"""
        cond = {
            "or": [
                {"if_model": "gpt-4o"},
                {"if_model": "claude-3"},
                {"if_tokens_gt": 5000}
            ]
        }
        
        # First matches
        entry1 = {"model": "gpt-4o", "tokens": 100}
        assert evaluate_condition(cond, entry1) is True
        
        # Third matches (tokens > 5000)
        entry2 = {"model": "unknown", "tokens": 6000}
        assert evaluate_condition(cond, entry2) is True
        
        # None match
        entry3 = {"model": "gpt-3.5-turbo", "tokens": 1000}
        assert evaluate_condition(cond, entry3) is False
    
    def test_and_composition_explicit(self):
        """Explicit AND composition"""
        cond = {
            "and": [
                {"if_model": "gpt-4o"},
                {"if_tokens_gt": 1000}
            ]
        }
        
        # Both match
        entry_match = {"model": "gpt-4o", "tokens": 1500}
        assert evaluate_condition(cond, entry_match) is True
        
        # Only model matches
        entry_partial1 = {"model": "gpt-4o", "tokens": 500}
        assert evaluate_condition(cond, entry_partial1) is False
        
        # Only tokens match
        entry_partial2 = {"model": "claude-3", "tokens": 1500}
        assert evaluate_condition(cond, entry_partial2) is False
    
    def test_not_composition_basic(self):
        """NOT negates condition result"""
        cond = {
            "not": {"if_model": "gpt-3.5-turbo"}
        }
        
        # Model is gpt-3.5-turbo (NOT negates to False)
        entry1 = {"model": "gpt-3.5-turbo"}
        assert evaluate_condition(cond, entry1) is False
        
        # Model is NOT gpt-3.5-turbo (NOT negates to True)
        entry2 = {"model": "gpt-4o"}
        assert evaluate_condition(cond, entry2) is True
    
    def test_not_with_complex_condition(self):
        """NOT can negate complex conditions"""
        cond = {
            "not": {
                "and": [
                    {"if_model": "gpt-4o"},
                    {"if_tokens_gt": 1000}
                ]
            }
        }
        
        # Both conditions match (NOT negates to False)
        entry1 = {"model": "gpt-4o", "tokens": 1500}
        assert evaluate_condition(cond, entry1) is False
        
        # Conditions don't match (NOT negates to True)
        entry2 = {"model": "gpt-4o", "tokens": 500}
        assert evaluate_condition(cond, entry2) is True
        
        entry3 = {"model": "claude-3", "tokens": 1500}
        assert evaluate_condition(cond, entry3) is True
    
    def test_nested_and_or_combination(self):
        """Nested AND inside OR"""
        cond = {
            "or": [
                {
                    "and": [
                        {"if_model": "gpt-4o"},
                        {"if_tokens_gt": 1000}
                    ]
                },
                {"if_cost_usd_gt": 0.50}
            ]
        }
        
        # First branch (AND) matches
        entry1 = {"model": "gpt-4o", "tokens": 1500, "cost_usd": 0.10}
        assert evaluate_condition(cond, entry1) is True
        
        # Second branch (cost) matches
        entry2 = {"model": "gpt-3.5-turbo", "tokens": 500, "cost_usd": 0.60}
        assert evaluate_condition(cond, entry2) is True
        
        # Neither branch matches
        entry3 = {"model": "gpt-4o", "tokens": 500, "cost_usd": 0.10}
        assert evaluate_condition(cond, entry3) is False
    
    def test_nested_or_inside_and(self):
        """Nested OR inside AND"""
        cond = {
            "and": [
                {"if_cost_usd_gt": 0.10},
                {
                    "or": [
                        {"if_model": "gpt-4o"},
                        {"if_retry_count_gt": 2}
                    ]
                }
            ]
        }
        
        # Both AND branches match (cost + first OR option)
        entry1 = {"model": "gpt-4o", "cost_usd": 0.20, "retry_count": 0}
        assert evaluate_condition(cond, entry1) is True
        
        # Both AND branches match (cost + second OR option)
        entry2 = {"model": "claude-3", "cost_usd": 0.20, "retry_count": 3}
        assert evaluate_condition(cond, entry2) is True
        
        # First AND branch fails (cost too low)
        entry3 = {"model": "gpt-4o", "cost_usd": 0.05, "retry_count": 0}
        assert evaluate_condition(cond, entry3) is False
        
        # Second AND branch fails (OR doesn't match)
        entry4 = {"model": "claude-3", "cost_usd": 0.20, "retry_count": 1}
        assert evaluate_condition(cond, entry4) is False
    
    def test_deeply_nested_composition(self):
        """Multiple levels of nesting"""
        cond = {
            "and": [
                {
                    "or": [
                        {"if_model": "gpt-4o"},
                        {"if_model": "claude-3"}
                    ]
                },
                {
                    "not": {
                        "if_fallback_triggered": True
                    }
                }
            ]
        }
        
        # Matches: model is gpt-4o AND fallback not triggered
        entry1 = {"model": "gpt-4o", "fallback_triggered": False}
        assert evaluate_condition(cond, entry1) is True
        
        # Matches: model is claude-3 AND fallback not triggered
        entry2 = {"model": "claude-3", "fallback_triggered": False}
        assert evaluate_condition(cond, entry2) is True
        
        # Fails: model matches but fallback WAS triggered
        entry3 = {"model": "gpt-4o", "fallback_triggered": True}
        assert evaluate_condition(cond, entry3) is False
        
        # Fails: model doesn't match (even though fallback not triggered)
        entry4 = {"model": "gpt-3.5-turbo", "fallback_triggered": False}
        assert evaluate_condition(cond, entry4) is False
    
    def test_empty_or_list(self):
        """Empty OR list returns False"""
        cond = {"or": []}
        entry = {"model": "gpt-4o"}
        
        # Empty OR has no conditions to satisfy
        assert evaluate_condition(cond, entry) is False
    
    def test_empty_and_list(self):
        """Empty AND list returns True (vacuous truth)"""
        cond = {"and": []}
        entry = {"model": "gpt-4o"}
        
        # Empty AND has no conditions to fail
        assert evaluate_condition(cond, entry) is True
    
    def test_or_with_invalid_type(self):
        """OR with non-list value returns False"""
        cond = {"or": "invalid"}
        entry = {"model": "gpt-4o"}
        
        assert evaluate_condition(cond, entry) is False
    
    def test_and_with_invalid_type(self):
        """AND with non-list value returns False"""
        cond = {"and": "invalid"}
        entry = {"model": "gpt-4o"}
        
        assert evaluate_condition(cond, entry) is False
    
    def test_not_with_invalid_type(self):
        """NOT with non-dict value returns False"""
        cond = {"not": "invalid"}
        entry = {"model": "gpt-4o"}
        
        assert evaluate_condition(cond, entry) is False
    
    def test_all_atomic_conditions_with_or(self):
        """OR composition works with all atomic condition types"""
        cond = {
            "or": [
                {"if_model": "gpt-4o"},
                {"if_tokens_gt": 5000},
                {"if_retry_count_gt": 3},
                {"if_fallback_triggered": True},
                {"if_cost_usd_gt": 1.0},
                {"if_response_time_gt": 10000},
                {"if_error_rate_gt": 50.0}
            ]
        }
        
        # Test each branch independently
        assert evaluate_condition(cond, {"model": "gpt-4o"}) is True
        assert evaluate_condition(cond, {"tokens": 6000}) is True
        assert evaluate_condition(cond, {"retry_count": 5}) is True
        assert evaluate_condition(cond, {"fallback_triggered": True}) is True
        assert evaluate_condition(cond, {"cost_usd": 1.5}) is True
        assert evaluate_condition(cond, {"response_time_ms": 15000}) is True
        assert evaluate_condition(cond, {"error_rate": 60.0}) is True
        
        # None match
        assert evaluate_condition(cond, {"model": "unknown", "tokens": 100}) is False
    
    def test_pii_detection_in_boolean_composition(self):
        """PII detection works within boolean composition"""
        cond = {
            "and": [
                {"if_model": "gpt-4o"},
                {"if_prompt_contains_pii": True}
            ]
        }
        
        # Model matches AND PII detected
        entry_with_pii = {
            "model": "gpt-4o",
            "prompt": "Contact me at user@example.com"
        }
        assert evaluate_condition(cond, entry_with_pii) is True
        
        # Model matches but NO PII
        entry_no_pii = {
            "model": "gpt-4o",
            "prompt": "What is the capital of France?"
        }
        assert evaluate_condition(cond, entry_no_pii) is False


class TestBooleanCompositionEdgeCases:
    """Edge cases for boolean composition"""
    
    def test_mixed_boolean_and_atomic_conditions(self):
        """When using boolean operators, wrap in explicit 'and' for clarity"""
        # This test documents that mixing boolean operators with atomic conditions
        # at the same level creates ambiguity. Use explicit wrapping instead.
        
        # Better approach: use explicit AND
        cond_explicit = {
            "and": [
                {"if_model": "gpt-4o"},
                {
                    "or": [
                        {"if_tokens_gt": 1000},
                        {"if_cost_usd_gt": 0.50}
                    ]
                }
            ]
        }
        
        # Both model AND one OR branch match
        entry1 = {"model": "gpt-4o", "tokens": 1500, "cost_usd": 0.10}
        assert evaluate_condition(cond_explicit, entry1) is True
        
        # Model matches but OR doesn't
        entry2 = {"model": "gpt-4o", "tokens": 500, "cost_usd": 0.10}
        assert evaluate_condition(cond_explicit, entry2) is False
        
        # OR matches but model doesn't
        entry3 = {"model": "claude-3", "tokens": 1500, "cost_usd": 0.10}
        assert evaluate_condition(cond_explicit, entry3) is False
    
    def test_single_item_or_list(self):
        """OR with single item behaves correctly"""
        cond = {"or": [{"if_model": "gpt-4o"}]}
        
        entry_match = {"model": "gpt-4o"}
        assert evaluate_condition(cond, entry_match) is True
        
        entry_no_match = {"model": "claude-3"}
        assert evaluate_condition(cond, entry_no_match) is False
    
    def test_single_item_and_list(self):
        """AND with single item behaves correctly"""
        cond = {"and": [{"if_model": "gpt-4o"}]}
        
        entry_match = {"model": "gpt-4o"}
        assert evaluate_condition(cond, entry_match) is True
        
        entry_no_match = {"model": "claude-3"}
        assert evaluate_condition(cond, entry_no_match) is False
    
    def test_not_with_empty_dict(self):
        """NOT with empty dict returns True (negation of vacuous truth)"""
        cond = {"not": {}}
        entry = {"model": "gpt-4o"}
        
        # Empty dict evaluates to True, NOT negates to False
        # Actually, empty dict with no conditions returns True (all conditions pass)
        # So NOT {} should return False
        assert evaluate_condition(cond, entry) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
