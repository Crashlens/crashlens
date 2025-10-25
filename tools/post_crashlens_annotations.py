#!/usr/bin/env python3
"""
Post CrashLens guard violations as GitHub Checks API annotations.

Usage:
    python post_crashlens_annotations.py <report_path> <commit_sha>

Environment Variables:
    GITHUB_REPOSITORY - Repository name (owner/repo)
    GITHUB_TOKEN - GitHub API token with checks:write scope

Example:
    export GITHUB_REPOSITORY="myorg/crashlens"
    export GITHUB_TOKEN="ghp_xxxxx"
    python post_crashlens_annotations.py crashlens-report.json abc123def456
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


def load_report(report_path: Path) -> Dict[str, Any]:
    """
    Load guard report from JSON file.
    
    Args:
        report_path: Path to report JSON file
        
    Returns:
        Parsed report dictionary
        
    Raises:
        FileNotFoundError: If report file doesn't exist
        json.JSONDecodeError: If report is invalid JSON
    """
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_annotations(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert guard report to GitHub Checks API annotations.
    
    Args:
        report: Parsed guard report dictionary
        
    Returns:
        List of annotation dictionaries for GitHub API
    """
    annotations = []
    
    rules = report.get('rules', {})
    
    for rule_id, rule_data in rules.items():
        # Skip rules with no violations
        if rule_data.get('count', 0) == 0:
            continue
        
        severity = rule_data.get('severity', 'warning')
        description = rule_data.get('description', 'Policy violation')
        examples = rule_data.get('examples', [])
        
        # Map severity to annotation level
        # GitHub supports: notice, warning, failure
        if severity in ['error', 'fatal', 'critical']:
            annotation_level = 'failure'
        else:
            annotation_level = 'warning'
        
        # Create annotation for each example (limit to 10 per rule to avoid spam)
        for example in examples[:10]:
            # Extract file path
            file_path = None
            line_number = None
            
            # Try different field names for file path
            if 'file' in example:
                file_path = example['file']
            elif 'path' in example:
                file_path = example['path']
            elif 'endpoint' in example:
                file_path = example['endpoint']
            
            # Try different field names for line number
            if 'line_number' in example:
                line_number = example['line_number']
            elif 'line' in example:
                line_number = example['line']
            
            # Fallback defaults
            if not file_path:
                file_path = '.crashlens/rules.yaml'
            if not line_number:
                line_number = 1
            
            # Build annotation message
            message_parts = [
                f"**Rule:** {rule_id}",
                f"**Severity:** {severity}",
                f"**Description:** {description}",
                ""
            ]
            
            # Add example details
            if 'model' in example:
                message_parts.append(f"**Model:** {example['model']}")
            if 'tokens' in example:
                message_parts.append(f"**Tokens:** {example['tokens']:,}")
            if 'timestamp' in example:
                message_parts.append(f"**Timestamp:** {example['timestamp']}")
            if 'cost' in example:
                message_parts.append(f"**Cost:** ${example['cost']:.4f}")
            
            message = "\n".join(message_parts)
            
            annotations.append({
                'path': file_path,
                'start_line': line_number,
                'end_line': line_number,
                'annotation_level': annotation_level,
                'message': message,
                'title': f"Rule {rule_id} violated"
            })
        
        # If no examples but count > 0, create a default annotation
        if not examples and rule_data.get('count', 0) > 0:
            annotations.append({
                'path': '.crashlens/rules.yaml',
                'start_line': 1,
                'end_line': 1,
                'annotation_level': annotation_level,
                'message': f"**Rule:** {rule_id}\n**Severity:** {severity}\n**Description:** {description}\n\nViolations: {rule_data['count']}",
                'title': f"Rule {rule_id} violated ({rule_data['count']} times)"
            })
    
    return annotations


def post_check_run(
    repo: str,
    commit_sha: str,
    annotations: List[Dict[str, Any]],
    token: str
) -> bool:
    """
    Post check-run with annotations to GitHub Checks API.
    
    Args:
        repo: Repository name (owner/repo)
        commit_sha: Git commit SHA
        annotations: List of annotation dictionaries
        token: GitHub API token
        
    Returns:
        True if successful, False otherwise
    """
    url = f"https://api.github.com/repos/{repo}/check-runs"
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    # Determine conclusion based on annotation levels
    has_failure = any(a['annotation_level'] == 'failure' for a in annotations)
    conclusion = 'failure' if has_failure else 'success'
    
    # GitHub API limits annotations to 50 per request
    # We'll batch them if needed
    batch_size = 50
    
    for i in range(0, len(annotations), batch_size):
        batch = annotations[i:i + batch_size]
        
        payload = {
            'name': 'CrashLens Guard',
            'head_sha': commit_sha,
            'status': 'completed',
            'conclusion': conclusion,
            'output': {
                'title': 'CrashLens Policy Violations',
                'summary': f"Found {len(annotations)} policy violations across {len(batch)} annotations in this batch.",
                'annotations': batch
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code not in [200, 201]:
                print(f"❌ Failed to post check-run: {response.status_code}", file=sys.stderr)
                print(response.text, file=sys.stderr)
                return False
            
            print(f"✅ Posted batch {i // batch_size + 1} ({len(batch)} annotations)")
        
        except Exception as e:
            print(f"❌ Error posting check-run: {e}", file=sys.stderr)
            return False
    
    return True


def main() -> int:
    """
    Main entry point for CLI.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if len(sys.argv) != 3:
        print("Usage: python post_crashlens_annotations.py <report_path> <commit_sha>", file=sys.stderr)
        return 1
    
    report_path = Path(sys.argv[1])
    commit_sha = sys.argv[2]
    
    # Get environment variables
    repo = os.getenv('GITHUB_REPOSITORY')
    token = os.getenv('GITHUB_TOKEN')
    
    if not repo:
        print("❌ GITHUB_REPOSITORY environment variable not set", file=sys.stderr)
        return 1
    
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set", file=sys.stderr)
        return 1
    
    # Load report
    try:
        report = load_report(report_path)
    except FileNotFoundError:
        print(f"❌ Report file not found: {report_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in report: {e}", file=sys.stderr)
        return 1
    
    # Build annotations
    annotations = build_annotations(report)
    
    if not annotations:
        print("✅ No violations to report")
        return 0
    
    print(f"📋 Posting {len(annotations)} annotations for commit {commit_sha[:8]}...")
    
    # Post to GitHub
    success = post_check_run(repo, commit_sha, annotations, token)
    
    if success:
        print(f"✅ Successfully posted annotations to {repo}")
        return 0
    else:
        print("❌ Failed to post annotations", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
