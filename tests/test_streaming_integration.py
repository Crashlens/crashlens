#!/usr/bin/env python3
"""
Unit tests for streaming integration in guard command (Step 3).
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from crashlens.guard import guard, STREAM_THRESHOLD_BYTES


@pytest.fixture
def sample_rules_yaml(tmp_path):
    """Create sample rules.yaml for testing."""
    rules_file = tmp_path / "rules.yaml"
    rules_content = """
rules:
  - id: RL_STREAM_001
    description: "Test rule for streaming"
    if:
      model: "gpt-4"
    action: fail_ci
    severity: error
"""
    rules_file.write_text(rules_content)
    return rules_file


def create_jsonl_file(path: Path, num_records: int, model: str = "gpt-4"):
    """Helper to create JSONL test files."""
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(num_records):
            record = {
                "id": i,
                "traceId": f"trace-{i}",
                "model": model if i % 2 == 0 else "gpt-3.5-turbo",
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
            f.write(json.dumps(record) + '\n')


class TestStreamingIntegration:
    """Test streaming reader integration with guard command."""
    
    def test_small_file_uses_normal_mode(self, tmp_path, sample_rules_yaml):
        """Small files use normal line-by-line mode."""
        # Create small file (< 10 MB)
        small_logs = tmp_path / "small.jsonl"
        create_jsonl_file(small_logs, 100)
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(small_logs),
                '--rules', str(sample_rules_yaml)
            ])
            
            # Should NOT mention streaming
            assert "streaming mode" not in result.output.lower()
            assert result.exit_code == 0
    
    @patch('crashlens.guard.STREAM_THRESHOLD_BYTES', 1024)  # 1 KB threshold for testing
    def test_large_file_uses_streaming_mode(self, tmp_path, sample_rules_yaml):
        """Large files trigger streaming mode."""
        # Create file larger than mocked threshold
        large_logs = tmp_path / "large.jsonl"
        create_jsonl_file(large_logs, 500)  # Should be > 1 KB
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(large_logs),
                '--rules', str(sample_rules_yaml)
            ])
            
            # Should mention streaming
            assert "streaming mode" in result.output.lower()
            assert result.exit_code == 0
    
    @patch('crashlens.guard.STREAM_THRESHOLD_BYTES', 1024)
    @patch('crashlens.guard.STREAM_BATCH_SIZE', 100)
    def test_streaming_processes_all_records(self, tmp_path, sample_rules_yaml):
        """Streaming mode processes all records correctly."""
        large_logs = tmp_path / "large.jsonl"
        # Create 300 records, 150 matching rule (gpt-4)
        create_jsonl_file(large_logs, 300)
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(large_logs),
                '--rules', str(sample_rules_yaml),
                '--output', 'json'
            ])
            
            # Parse JSON output (filter out all stderr messages)
            # Just extract everything between first { and last }
            output = result.output
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_output = output[start_idx:end_idx+1]
                report = json.loads(json_output)
            else:
                raise ValueError("No JSON found in output")
            
            # Should detect 150 violations (half the records)
            assert report['rules']['RL_STREAM_001']['count'] == 150
    
    @patch('crashlens.guard.STREAM_THRESHOLD_BYTES', 500)
    def test_streaming_with_malformed_lines(self, tmp_path, sample_rules_yaml):
        """Streaming mode handles malformed lines gracefully."""
        mixed_logs = tmp_path / "mixed.jsonl"
        
        with open(mixed_logs, 'w') as f:
            # Valid records
            for i in range(5):
                f.write(json.dumps({"id": i, "model": "gpt-4"}) + '\n')
            # Malformed
            f.write('{ invalid json\n')
            # More valid
            for i in range(5, 10):
                f.write(json.dumps({"id": i, "model": "gpt-4"}) + '\n')
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(mixed_logs),
                '--rules', str(sample_rules_yaml),
                '--output', 'json'
            ])
            
            # Should process all valid records
            lines = result.output.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith(('📊', '⚠️', '📋', '   Content:')) or not line.strip():
                    continue
                if line.strip() == '{':
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip() == '}' and in_json:
                    break
            
            json_output = '\n'.join(json_lines)
            report = json.loads(json_output)
            
            # 10 valid gpt-4 records
            assert report['rules']['RL_STREAM_001']['count'] == 10


class TestEnvironmentVariables:
    """Test environment variable configuration for streaming."""
    
    @patch.dict('os.environ', {'CRASHLENS_STREAM_THRESHOLD': '2048'})
    def test_custom_stream_threshold(self):
        """CRASHLENS_STREAM_THRESHOLD environment variable is respected."""
        # Re-import to pick up new env var
        import importlib
        import crashlens.guard as guard_module
        importlib.reload(guard_module)
        
        # Threshold should be 2048 bytes
        assert guard_module.STREAM_THRESHOLD_BYTES == 2048
    
    @patch.dict('os.environ', {'CRASHLENS_STREAM_BATCH_SIZE': '1000'})
    def test_custom_batch_size(self):
        """CRASHLENS_STREAM_BATCH_SIZE environment variable is respected."""
        import importlib
        import crashlens.guard as guard_module
        importlib.reload(guard_module)
        
        # Batch size should be 1000
        assert guard_module.STREAM_BATCH_SIZE == 1000


class TestStreamingPerformance:
    """Test streaming maintains performance characteristics."""
    
    @patch('crashlens.guard.STREAM_THRESHOLD_BYTES', 1024)
    def test_streaming_collects_examples(self, tmp_path, sample_rules_yaml):
        """Streaming mode still collects example violations."""
        large_logs = tmp_path / "large.jsonl"
        create_jsonl_file(large_logs, 200)
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(large_logs),
                '--rules', str(sample_rules_yaml),
                '--output', 'json'
            ])
            
            lines = result.output.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith(('📊', '⚠️', '📋')) or not line.strip():
                    continue
                if line.strip() == '{':
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip() == '}' and in_json:
                    break
            
            json_output = '\n'.join(json_lines)
            report = json.loads(json_output)
            
            # Should have examples collected
            examples = report['rules']['RL_STREAM_001']['examples']
            assert len(examples) > 0
            assert len(examples) <= 5  # Respects MAX_EXAMPLES default
    
    @patch('crashlens.guard.STREAM_THRESHOLD_BYTES', 1024)
    def test_streaming_respects_no_content_flag(self, tmp_path, sample_rules_yaml):
        """Streaming mode respects --no-content flag."""
        large_logs = tmp_path / "large.jsonl"
        create_jsonl_file(large_logs, 200)
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(large_logs),
                '--rules', str(sample_rules_yaml),
                '--output', 'json',
                '--no-content'
            ])
            
            lines = result.output.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith(('📊', '⚠️', '📋')) or not line.strip():
                    continue
                if line.strip() == '{':
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip() == '}' and in_json:
                    break
            
            json_output = '\n'.join(json_lines)
            report = json.loads(json_output)
            
            # Should have no examples when no-content is set
            examples = report['rules']['RL_STREAM_001']['examples']
            assert len(examples) == 0
