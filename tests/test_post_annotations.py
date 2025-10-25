#!/usr/bin/env python3
"""
Unit tests for GitHub Checks API annotation posting.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add tools to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from post_crashlens_annotations import (
    load_report,
    build_annotations,
    post_check_run
)


@pytest.fixture
def sample_report():
    """Sample guard report for testing."""
    return {
        'summary': {
            'total_rules': 2,
            'violations': 2
        },
        'rules': {
            'RL001': {
                'count': 2,
                'severity': 'error',
                'description': 'Excessive retry count',
                'examples': [
                    {
                        'model': 'gpt-4',
                        'tokens': 1000,
                        'timestamp': '2024-01-15T10:30:00Z',
                        'endpoint': '/v1/chat/completions',
                        'line': 42
                    },
                    {
                        'model': 'gpt-3.5-turbo',
                        'tokens': 500,
                        'timestamp': '2024-01-15T10:31:00Z'
                    }
                ]
            },
            'RL002': {
                'count': 1,
                'severity': 'warning',
                'description': 'High token usage',
                'examples': [
                    {
                        'model': 'gpt-4',
                        'tokens': 5000,
                        'file': 'src/app.py',
                        'line_number': 123
                    }
                ]
            },
            'RL003': {
                'count': 0,
                'severity': 'info',
                'description': 'No violations',
                'examples': []
            }
        }
    }


@pytest.fixture
def sample_report_file(tmp_path, sample_report):
    """Create a temporary report file."""
    report_path = tmp_path / 'report.json'
    with open(report_path, 'w') as f:
        json.dump(sample_report, f)
    return report_path


class TestLoadReport:
    """Test report loading."""
    
    def test_load_valid_report(self, sample_report_file, sample_report):
        """Load a valid report file."""
        report = load_report(sample_report_file)
        assert report == sample_report
    
    def test_load_nonexistent_file(self, tmp_path):
        """Raise error for missing file."""
        with pytest.raises(FileNotFoundError):
            load_report(tmp_path / 'nonexistent.json')
    
    def test_load_invalid_json(self, tmp_path):
        """Raise error for invalid JSON."""
        bad_file = tmp_path / 'bad.json'
        bad_file.write_text('{ invalid json')
        
        with pytest.raises(json.JSONDecodeError):
            load_report(bad_file)


class TestBuildAnnotations:
    """Test annotation building from report."""
    
    def test_build_annotations_basic(self, sample_report):
        """Build annotations from sample report."""
        annotations = build_annotations(sample_report)
        
        # Should have 3 annotations (2 from RL001, 1 from RL002)
        assert len(annotations) == 3
        
        # Check first annotation
        assert annotations[0]['annotation_level'] == 'failure'  # error severity
        assert 'RL001' in annotations[0]['message']
        assert annotations[0]['title'] == 'Rule RL001 violated'
        
        # Check that warning severity maps correctly
        warning_annotations = [a for a in annotations if 'RL002' in a['message']]
        assert len(warning_annotations) == 1
        assert warning_annotations[0]['annotation_level'] == 'warning'
    
    def test_build_annotations_with_file_path(self, sample_report):
        """Annotations use file path from examples."""
        annotations = build_annotations(sample_report)
        
        # RL002 example has explicit file path
        rl002_annotations = [a for a in annotations if 'RL002' in a['message']]
        assert rl002_annotations[0]['path'] == 'src/app.py'
        assert rl002_annotations[0]['start_line'] == 123
    
    def test_build_annotations_fallback_path(self, sample_report):
        """Annotations fall back to default path when missing."""
        annotations = build_annotations(sample_report)
        
        # First RL001 example has endpoint, should use it
        rl001_first = [a for a in annotations if 'RL001' in a['message']][0]
        assert rl001_first['path'] == '/v1/chat/completions'
    
    def test_build_annotations_skips_zero_count(self):
        """Skip rules with zero violations."""
        report = {
            'rules': {
                'RL_ZERO': {
                    'count': 0,
                    'severity': 'error',
                    'description': 'Never triggered',
                    'examples': []
                }
            }
        }
        
        annotations = build_annotations(report)
        assert len(annotations) == 0
    
    def test_build_annotations_no_examples(self):
        """Create default annotation when no examples."""
        report = {
            'rules': {
                'RL_NO_EXAMPLES': {
                    'count': 1,
                    'severity': 'warning',
                    'description': 'No examples available',
                    'examples': []
                }
            }
        }
        
        annotations = build_annotations(report)
        assert len(annotations) == 1
        assert annotations[0]['path'] == '.crashlens/rules.yaml'
        assert annotations[0]['start_line'] == 1


class TestPostCheckRun:
    """Test posting to GitHub Checks API."""
    
    @patch('post_crashlens_annotations.requests.post')
    def test_post_check_run_success(self, mock_post):
        """Successfully post check-run."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        annotations = [
            {
                'path': 'src/app.py',
                'start_line': 10,
                'end_line': 10,
                'annotation_level': 'warning',
                'message': 'Test violation',
                'title': 'Test Rule'
            }
        ]
        
        success = post_check_run(
            'owner/repo',
            'abc123',
            annotations,
            'fake-token'
        )
        
        assert success is True
        assert mock_post.call_count == 1
        
        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        
        assert payload['name'] == 'CrashLens Guard'
        assert payload['head_sha'] == 'abc123'
        assert payload['status'] == 'completed'
        assert len(payload['output']['annotations']) == 1
    
    @patch('post_crashlens_annotations.requests.post')
    def test_post_check_run_batching(self, mock_post):
        """Batch annotations into chunks of 50."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        # Create 120 annotations (should require 3 batches)
        annotations = [
            {
                'path': f'file_{i}.py',
                'start_line': 1,
                'end_line': 1,
                'annotation_level': 'warning',
                'message': f'Violation {i}',
                'title': f'Rule {i}'
            }
            for i in range(120)
        ]
        
        success = post_check_run(
            'owner/repo',
            'abc123',
            annotations,
            'fake-token'
        )
        
        assert success is True
        assert mock_post.call_count == 3  # 3 batches (50 + 50 + 20)
        
        # Verify batch sizes
        first_call = mock_post.call_args_list[0].kwargs['json']
        assert len(first_call['output']['annotations']) == 50
        
        second_call = mock_post.call_args_list[1].kwargs['json']
        assert len(second_call['output']['annotations']) == 50
        
        third_call = mock_post.call_args_list[2].kwargs['json']
        assert len(third_call['output']['annotations']) == 20
    
    @patch('post_crashlens_annotations.requests.post')
    def test_post_check_run_failure(self, mock_post):
        """Handle HTTP errors gracefully."""
        mock_post.side_effect = Exception("Network error")
        
        annotations = [
            {
                'path': 'src/app.py',
                'start_line': 10,
                'end_line': 10,
                'annotation_level': 'warning',
                'message': 'Test',
                'title': 'Test'
            }
        ]
        
        success = post_check_run(
            'owner/repo',
            'abc123',
            annotations,
            'fake-token'
        )
        
        assert success is False
    
    @patch('post_crashlens_annotations.requests.post')
    def test_post_check_run_conclusion_mapping(self, mock_post):
        """Map annotations to correct conclusion."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        # Test with failure-level annotation
        failure_annotations = [
            {
                'path': 'test.py',
                'start_line': 1,
                'end_line': 1,
                'annotation_level': 'failure',
                'message': 'Error',
                'title': 'Error'
            }
        ]
        
        post_check_run('owner/repo', 'abc123', failure_annotations, 'token')
        
        payload = mock_post.call_args.kwargs['json']
        assert payload['conclusion'] == 'failure'
