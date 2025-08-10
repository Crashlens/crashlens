#!/usr/bin/env python3
"""
Unit tests for the crashlens simulate command.

Tests cover all scenarios, parameter validation, file operations, 
and edge cases to ensure robust behavior.
"""

import pytest
import json
import random
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Import the simulate command and helper functions
from crashlens.cli import simulate, _parse_models, _generate_traces, _calculate_cost, _write_jsonl_traces


class TestSimulateCommand:
    """Test the main simulate command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_simulate_basic_success(self):
        """Test basic successful simulation."""
        output_file = self.temp_dir / "test.jsonl"
        
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '5',
            '--seed', '42'
        ])
        
        assert result.exit_code == 0
        assert "Generated 5 traces" in result.output
        assert output_file.exists()
        
        # Validate JSONL format
        traces = []
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                trace = json.loads(line.strip())
                traces.append(trace)
        
        assert len(traces) == 5
        
        # Validate trace structure
        for trace in traces:
            assert "traceId" in trace
            assert "startTime" in trace
            assert "endTime" in trace
            assert "input" in trace
            assert "usage" in trace
            assert "cost" in trace
            assert "output" in trace
            assert "status" in trace
    
    def test_simulate_all_scenarios(self):
        """Test all available scenarios."""
        scenarios = ['normal', 'retry-loop', 'model-overkill', 'slow', 'mixed-errors']
        
        for scenario in scenarios:
            output_file = self.temp_dir / f"test_{scenario}.jsonl"
            
            result = self.runner.invoke(simulate, [
                '--output', str(output_file),
                '--count', '3',
                '--scenario', scenario,
                '--seed', '42'
            ])
            
            assert result.exit_code == 0, f"Failed for scenario: {scenario}"
            assert output_file.exists()
            
            # Verify traces were generated
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 3
    
    def test_simulate_deterministic_with_seed(self):
        """Test that same seed produces same output structure."""
        output_file1 = self.temp_dir / "deterministic1.jsonl"
        output_file2 = self.temp_dir / "deterministic2.jsonl"
        
        # Generate with same seed
        for output_file in [output_file1, output_file2]:
            result = self.runner.invoke(simulate, [
                '--output', str(output_file),
                '--count', '5',
                '--seed', '12345'
            ])
            assert result.exit_code == 0
        
        # Compare trace structures (not timestamps which vary)
        def get_trace_signatures(file_path):
            signatures = []
            with open(file_path, 'r') as f:
                for line in f:
                    trace = json.loads(line.strip())
                    # Create signature excluding timestamps
                    sig = {
                        'traceId_prefix': trace['traceId'].split('_')[0],
                        'model': trace['input']['model'],
                        'prompt_tokens': trace['usage']['prompt_tokens'],
                        'completion_tokens': trace['usage']['completion_tokens'],
                        'status': trace['status']
                    }
                    signatures.append(sig)
            return signatures
        
        sigs1 = get_trace_signatures(output_file1)
        sigs2 = get_trace_signatures(output_file2)
        
        # Should have same structure with same seed
        assert len(sigs1) == len(sigs2) == 5
        assert sigs1 == sigs2
    
    def test_simulate_custom_models(self):
        """Test custom model specification."""
        output_file = self.temp_dir / "custom_models.jsonl"
        
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '3',
            '--models', 'gpt-4,claude-3',
            '--seed', '42'
        ])
        
        assert result.exit_code == 0
        
        # Verify only specified models are used
        traces = []
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                trace = json.loads(line.strip())
                traces.append(trace)
        
        used_models = {trace['input']['model'] for trace in traces}
        assert used_models.issubset({'gpt-4', 'claude-3'})
    
    def test_simulate_error_rate(self):
        """Test error rate parameter affects output."""
        output_file = self.temp_dir / "error_test.jsonl"
        
        # Test with high error rate
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '10',
            '--error-rate', '0.8',
            '--seed', '42'
        ])
        
        assert result.exit_code == 0
        
        # Count error traces
        error_count = 0
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                trace = json.loads(line.strip())
                if trace['status'] in ['error', 'timeout']:
                    error_count += 1
        
        # With high error rate and seed 42, should have several errors
        assert error_count > 0
    
    def test_simulate_file_overwrite_prompt(self):
        """Test file overwrite behavior without --force."""
        output_file = self.temp_dir / "existing.jsonl"
        
        # Create existing file
        output_file.write_text("existing content")
        
        # Try to overwrite without --force
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '2'
        ], input='n\n')  # Answer 'no' to overwrite prompt
        
        assert result.exit_code == 1
        assert "Operation cancelled" in result.output
        
        # File should still have original content
        assert output_file.read_text() == "existing content"
    
    def test_simulate_force_overwrite(self):
        """Test force overwrite with --force flag."""
        output_file = self.temp_dir / "force_overwrite.jsonl"
        
        # Create existing file
        output_file.write_text("existing content")
        
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '2',
            '--force',
            '--seed', '42'
        ])
        
        assert result.exit_code == 0
        assert "Generated 2 traces" in result.output
        
        # File should be overwritten
        assert "existing content" not in output_file.read_text()
    
    def test_simulate_validation_errors(self):
        """Test parameter validation."""
        output_file = self.temp_dir / "validation.jsonl"
        
        # Test zero count
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '0'
        ])
        assert result.exit_code == 1
        assert "count must be greater than 0" in result.output
        
        # Test invalid error rate
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '5',
            '--error-rate', '1.5'
        ])
        assert result.exit_code == 1
        assert "error-rate must be between 0.0 and 1.0" in result.output
        
        # Test invalid error rate (negative)
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '5',
            '--error-rate', '-0.1'
        ])
        assert result.exit_code == 1
        assert "error-rate must be between 0.0 and 1.0" in result.output
    
    @patch('crashlens.cli.HAS_FAKER', False)
    def test_simulate_without_faker(self):
        """Test error handling when faker is not available."""
        output_file = self.temp_dir / "no_faker.jsonl"
        
        result = self.runner.invoke(simulate, [
            '--output', str(output_file),
            '--count', '2'
        ])
        
        assert result.exit_code == 1
        assert "faker package not installed" in result.output


class TestHelperFunctions:
    """Test helper functions for the simulate command."""
    
    def test_parse_models_default(self):
        """Test default model parsing."""
        models = _parse_models("")
        expected_defaults = ['gpt-4o', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4']
        assert models == expected_defaults
    
    def test_parse_models_custom(self):
        """Test custom model parsing."""
        models = _parse_models("gpt-4,claude-3,palm-2")
        assert models == ['gpt-4', 'claude-3', 'palm-2']
    
    def test_parse_models_with_spaces(self):
        """Test model parsing with spaces."""
        models = _parse_models("gpt-4 , claude-3 ,  palm-2  ")
        assert models == ['gpt-4', 'claude-3', 'palm-2']
    
    def test_parse_models_empty_returns_default(self):
        """Test that empty string returns defaults."""
        models = _parse_models("   ")
        expected_defaults = ['gpt-4o', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4']
        assert models == expected_defaults
    
    def test_calculate_cost_known_models(self):
        """Test cost calculation for known models."""
        # Test GPT-4o
        cost = _calculate_cost('gpt-4o', 1000, 500)
        expected = (1000 / 1000 * 0.005) + (500 / 1000 * 0.015)
        assert abs(cost - expected) < 0.000001
        
        # Test GPT-3.5-turbo (cheaper)
        cost = _calculate_cost('gpt-3.5-turbo', 1000, 500)
        expected = (1000 / 1000 * 0.0005) + (500 / 1000 * 0.0015)
        assert abs(cost - expected) < 0.000001
    
    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown models uses defaults."""
        cost = _calculate_cost('unknown-model', 1000, 500)
        expected = (1000 / 1000 * 0.002) + (500 / 1000 * 0.006)
        assert abs(cost - expected) < 0.000001
    
    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        cost = _calculate_cost('gpt-4o', 0, 0)
        assert cost == 0.0
    
    def test_write_jsonl_traces(self):
        """Test JSONL writing functionality."""
        temp_dir = Path(tempfile.mkdtemp())
        output_file = temp_dir / "test_write.jsonl"
        
        traces = [
            {"traceId": "test1", "model": "gpt-4o", "cost": 0.001},
            {"traceId": "test2", "model": "gpt-3.5", "cost": 0.0005}
        ]
        
        try:
            _write_jsonl_traces(output_file, traces)
            
            assert output_file.exists()
            
            # Read back and verify
            read_traces = []
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    read_traces.append(json.loads(line.strip()))
            
            assert read_traces == traces
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_write_jsonl_creates_directories(self):
        """Test that JSONL writer creates parent directories."""
        temp_dir = Path(tempfile.mkdtemp())
        nested_file = temp_dir / "nested" / "deep" / "test.jsonl"
        
        traces = [{"traceId": "test", "cost": 0.001}]
        
        try:
            _write_jsonl_traces(nested_file, traces)
            
            assert nested_file.exists()
            assert nested_file.parent.exists()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestScenarioGeneration:
    """Test different scenario generation patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        random.seed(42)  # For reproducible tests
        
        # Mock faker for consistent testing
        self.fake_mock = MagicMock()
        self.fake_mock.sentence.return_value = "Test sentence"
        self.fake_mock.text.return_value = "Test response text"
    
    def test_generate_normal_traces(self):
        """Test normal trace generation."""
        traces = _generate_traces(5, 'normal', ['gpt-4o'], 0.2, self.fake_mock)
        
        assert len(traces) == 5
        
        for trace in traces:
            assert trace['input']['model'] == 'gpt-4o'
            assert 'traceId' in trace
            assert trace['traceId'].startswith('trace_')
    
    def test_generate_retry_loop_traces(self):
        """Test retry loop trace generation."""
        traces = _generate_traces(10, 'retry-loop', ['gpt-4o'], 0.2, self.fake_mock)
        
        # Should have retry patterns (same traceId for retries)
        trace_ids = [trace['traceId'] for trace in traces]
        unique_ids = set(trace_ids)
        
        # Should have fewer unique trace IDs than total traces (due to retries)
        assert len(unique_ids) < len(traces)
        
        # Check for retry metadata
        retry_traces = [trace for trace in traces if 'metadata' in trace]
        assert len(retry_traces) > 0
        
        # Verify retry attempt numbers
        for trace in retry_traces:
            assert 'retry_attempt' in trace['metadata']
            assert trace['metadata']['retry_attempt'] >= 1
    
    def test_generate_model_overkill_traces(self):
        """Test model overkill trace generation."""
        models = ['gpt-4o', 'gpt-3.5-turbo', 'gpt-4']
        traces = _generate_traces(10, 'model-overkill', models, 0.1, self.fake_mock)
        
        # Should have some traces with low token counts (overkill pattern)
        low_token_traces = [trace for trace in traces 
                          if trace['usage']['prompt_tokens'] <= 15]
        
        # With model-overkill scenario, should have several low token traces
        assert len(low_token_traces) > 0
    
    def test_generate_slow_traces(self):
        """Test slow trace generation."""
        traces = _generate_traces(5, 'slow', ['gpt-4o'], 0.1, self.fake_mock)
        
        # Check for duration_ms field and slow durations
        slow_traces = [trace for trace in traces 
                      if 'duration_ms' in trace and trace.get('duration_ms', 0) >= 5000]
        
        # Most traces should be slow in this scenario
        assert len(slow_traces) >= 3
    
    def test_generate_mixed_error_traces(self):
        """Test mixed error trace generation."""
        traces = _generate_traces(10, 'mixed-errors', ['gpt-4o'], 0.5, self.fake_mock)
        
        # Should have variety of error types
        error_traces = [trace for trace in traces if trace['status'] != 'success']
        metadata_types = {trace.get('metadata', {}).get('error_type') 
                         for trace in error_traces if 'metadata' in trace}
        
        # Should have some metadata with error types
        assert len(metadata_types) > 0
        assert None not in metadata_types or len(metadata_types) > 1


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_permission_error_handling(self):
        """Test handling of permission errors during file writing."""
        # This is hard to test reliably across platforms,
        # but we can test the error message handling
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Try to write to a directory instead of a file
            # This should cause an error
            traces = [{"traceId": "test", "cost": 0.001}]
            
            with pytest.raises(Exception) as exc_info:
                _write_jsonl_traces(temp_dir, traces)  # Directory, not file
            
            # Check that some kind of error message is present
            error_msg = str(exc_info.value)
            assert any(phrase in error_msg.lower() for phrase in [
                'permission denied', 'failed to write', 'is a directory'
            ])
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
