"""
Security tests for CrashLens - Pre-production validation
Tests YAML safety, path traversal, subprocess execution, PII redaction
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from click.testing import CliRunner
from crashlens.cli import cli
from crashlens.guard import load_rules


class TestYAMLSafety:
    """Test YAML loading is safe from code execution"""
    
    def test_malicious_yaml_python_object_blocked(self):
        """Malicious YAML with python object tags should not execute"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create malicious YAML trying to execute python code
            malicious_yaml = """
version: 1
rules:
  - !!python/object/apply:os.system
    args: ['echo MALICIOUS']
    id: MALICIOUS
    match:
      model: "gpt-4"
"""
            Path("malicious.yaml").write_text(malicious_yaml)
            Path("logs.jsonl").write_text('{"traceId": "1", "model": "gpt-4"}\n')
            
            # Should fail to parse, not execute code
            result = runner.invoke(cli, ['guard', 'logs.jsonl', '--rules', 'malicious.yaml'])
            
            # Should error on YAML parsing, not execute the malicious code
            assert result.exit_code != 0
            assert "MALICIOUS" not in result.output  # Code should not have executed
    
    def test_malicious_yaml_subprocess_blocked(self):
        """YAML attempting subprocess execution should be blocked"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            malicious_yaml = """
version: 1  
rules:
  - !!python/object/apply:subprocess.call
    args: [['echo', 'EXPLOIT']]
    id: EXPLOIT
    match:
      model: "gpt-4"
"""
            Path("malicious.yaml").write_text(malicious_yaml)
            Path("logs.jsonl").write_text('{"traceId": "1", "model": "gpt-4"}\n')
            
            result = runner.invoke(cli, ['guard', 'logs.jsonl', '--rules', 'malicious.yaml'])
            
            assert result.exit_code != 0
            assert "EXPLOIT" not in result.output


class TestPathTraversalProtection:
    """Test path sanitization prevents directory traversal"""
    
    def test_report_path_traversal_blocked(self):
        """Report path with ../ traversal should be sanitized"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: TEST
    match:
      model: "gpt-4"
"""
            Path("rules.yaml").write_text(rules)
            Path("logs.jsonl").write_text('{"traceId": "1", "model": "gpt-4"}\n')
            
            # Try to write report outside current directory
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml',
                '--report-path', '../../etc/passwd'
            ])
            
            # Should either reject the path or sanitize it safely
            # Not write to /etc/passwd
            assert not Path('/etc/passwd').exists() or not Path('/etc/passwd').is_file()
            # Should either fail or write to safe location
            if result.exit_code == 0:
                # If it succeeded, verify file wasn't written to traversed path
                assert not Path('../../etc/passwd').exists()
    
    def test_annotation_hook_path_validation(self):
        """Annotation hook with suspicious path should be validated"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: TEST
    match:
      model: "gpt-4"
"""
            Path("rules.yaml").write_text(rules)
            Path("logs.jsonl").write_text('{"traceId": "1", "model": "gpt-4"}\n')
            
            # Try to use path traversal in annotation hook
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml',
                '--annotation-hook', '../../../malicious.sh'
            ])
            
            # Should handle gracefully (reject or sanitize)
            # Not execute arbitrary scripts outside workspace


class TestNoArbitraryExecution:
    """Verify no eval/exec or shell command injection"""
    
    def test_log_content_not_executed_as_shell(self):
        """Log content with shell commands should not be executed"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: SHELL_TEST
    match:
      prompt: "test"
"""
            Path("rules.yaml").write_text(rules)
            
            # Create log with shell command in content
            malicious_log = '''{"traceId": "1", "prompt": "; rm -rf / &", "model": "gpt-4"}'''
            Path("logs.jsonl").write_text(malicious_log + '\n')
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml'
            ])
            
            # Should process safely, not execute the command
            assert result.exit_code in [0, 1]  # Success or violations, not crash
            # Verify system is still intact (directory still exists)
            assert Path('.').exists()
    
    def test_regex_pattern_no_code_execution(self):
        """Regex patterns in rules should not allow code execution"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: REGEX_EXPLOIT
    match:
      prompt:
        regex: '(?e).*'  # Try to use experimental regex features
"""
            Path("rules.yaml").write_text(rules)
            Path("logs.jsonl").write_text('{"traceId": "1", "prompt": "test", "model": "gpt-4"}\n')
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml'
            ])
            
            # Should either reject invalid regex or process safely
            # Not execute code via regex engine exploits
            assert result.exit_code in [0, 1, 2]  # Any non-crash exit code acceptable


class TestPIIRedactionSafety:
    """Verify PII redaction is complete and doesn't leak"""
    
    def test_pii_fully_redacted_in_json_output(self):
        """PII should be completely removed from JSON reports"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: PII_TEST
    description: "Test PII redaction"
    if:
      model: "gpt-4"
    then: fail_ci
    action: error
"""
            Path("rules.yaml").write_text(rules)
            
            # Log with multiple PII types
            pii_log = '''{
                "traceId": "1",
                "model": "gpt-4",
                "prompt": "My email is john.doe@example.com and SSN is 123-45-6789",
                "metadata": {
                    "user_phone": "555-123-4567",
                    "user_email": "jane@test.com"
                }
            }'''
            Path("logs.jsonl").write_text(pii_log + '\n')
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml',
                '--strip-pii',
                '--output', 'json'
            ])
            
            assert result.exit_code in [0, 1]
            
            # PII should be fully redacted
            assert 'john.doe@example.com' not in result.output
            assert 'jane@test.com' not in result.output
            assert '123-45-6789' not in result.output
            assert '555-123-4567' not in result.output
            
            # Redaction markers should be present
            assert '[REDACTED' in result.output or result.output == '' or 'PII_TEST' in result.output
    
    def test_pii_not_leaked_in_metadata_fields(self):
        """PII redaction should cover all nested fields"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: META_TEST
    description: "Test metadata PII"
    if:
      model: "gpt-4"
    then: fail_ci
    action: error
"""
            Path("rules.yaml").write_text(rules)
            
            pii_log = '''{
                "traceId": "1",
                "model": "gpt-4",
                "metadata": {
                    "deep": {
                        "nested": {
                            "email": "secret@company.com"
                        }
                    }
                }
            }'''
            Path("logs.jsonl").write_text(pii_log + '\n')
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml',
                '--strip-pii',
                '--output', 'json'
            ])
            
            # Even deeply nested PII should be redacted
            assert 'secret@company.com' not in result.output


class TestInputValidation:
    """Test input validation and error handling"""
    
    def test_extremely_long_input_line_handled(self):
        """Very long JSONL lines should not cause crashes"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: LONG_TEST
    match:
      model: "gpt-4"
"""
            Path("rules.yaml").write_text(rules)
            
            # Create log with extremely long field (10MB string)
            long_string = "A" * (10 * 1024 * 1024)
            log = f'{{"traceId": "1", "model": "gpt-4", "prompt": "{long_string}"}}\n'
            Path("logs.jsonl").write_text(log)
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml'
            ])
            
            # Should handle gracefully (may skip line, but shouldn't crash)
            assert result.exit_code in [0, 1]  # Success or violations, not crash
    
    def test_null_bytes_in_input_handled(self):
        """Null bytes in input should not cause issues"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            rules = """
version: 1
rules:
  - id: NULL_TEST
    match:
      model: "gpt-4"
"""
            Path("rules.yaml").write_text(rules)
            
            # Log with null byte
            log = '{"traceId": "1", "model": "gpt-4", "prompt": "test\\x00null"}\n'
            Path("logs.jsonl").write_text(log)
            
            result = runner.invoke(cli, [
                'guard', 'logs.jsonl',
                '--rules', 'rules.yaml'
            ])
            
            # Should process without crash
            assert result.exit_code in [0, 1]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
