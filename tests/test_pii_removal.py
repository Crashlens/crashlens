"""
Tests for PII Removal Feature
"""

import json
import pytest
import tempfile
from pathlib import Path
from crashlens.pii.remover import PIIRemover
from crashlens.pii.patterns import validate_email, validate_phone, validate_ssn
from crashlens.pii.sanitizer import PIISanitizer, FileSanitizer


class TestPIIPatterns:
    """Test PII pattern detection."""
    
    def test_email_detection(self):
        """Test email pattern detection."""
        assert validate_email("Contact: user@example.com")
        assert validate_email("Email: john.doe+test@company.co.uk")
        assert not validate_email("Not an email: user@")
        assert not validate_email("No email here")
    
    def test_phone_detection(self):
        """Test phone number detection."""
        assert validate_phone("Call: (123) 456-7890")
        assert validate_phone("Phone: 123-456-7890")
        assert validate_phone("Mobile: 1234567890")
        assert not validate_phone("Not a phone: 123")
    
    def test_ssn_detection(self):
        """Test SSN detection."""
        assert validate_ssn("SSN: 123-45-6789")
        assert not validate_ssn("Not SSN: 123456789")
        assert not validate_ssn("No SSN here")


class TestPIIRemover:
    """Test PII removal logic."""
    
    def test_remove_email(self):
        """Test email removal."""
        remover = PIIRemover(['email'])
        text = "Contact me at john@example.com for info"
        result = remover.remove_pii_from_text(text)
        
        assert "[EMAIL_REDACTED]" in result
        assert "john@example.com" not in result
        assert remover.get_stats()['email'] == 1
    
    def test_remove_multiple_pii_types(self):
        """Test removal of multiple PII types."""
        remover = PIIRemover(['email', 'phone_us'])
        text = "Email: john@test.com Phone: 123-456-7890"
        result = remover.remove_pii_from_text(text)
        
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "john@test.com" not in result
        assert "123-456-7890" not in result
    
    def test_remove_pii_from_dict(self):
        """Test PII removal from dictionary."""
        remover = PIIRemover()
        data = {
            "user": "john@example.com",
            "phone": "123-456-7890",
            "message": "Contact at john@example.com"
        }
        
        result = remover.remove_pii_from_dict(data)
        
        assert "[EMAIL_REDACTED]" in result['user']
        assert "[PHONE_REDACTED]" in result['phone']
        assert result['message'].count("[EMAIL_REDACTED]") == 1
    
    def test_nested_dict_pii_removal(self):
        """Test PII removal from nested dictionaries."""
        remover = PIIRemover(['email'])
        data = {
            "level1": {
                "level2": {
                    "email": "nested@example.com"
                }
            }
        }
        
        result = remover.remove_pii_from_dict(data)
        assert "[EMAIL_REDACTED]" in result['level1']['level2']['email']
    
    def test_dry_run_mode(self):
        """Test dry run mode (count only, don't remove)."""
        remover = PIIRemover(['email'])
        text = "Email: test@example.com"
        
        result = remover.remove_pii_from_text(text, dry_run=True)
        
        # Original text should be unchanged
        assert result == text
        # But stats should be updated
        assert remover.get_stats()['email'] == 1
    
    def test_stats_reset(self):
        """Test statistics reset."""
        remover = PIIRemover(['email'])
        remover.remove_pii_from_text("test@example.com")
        
        assert remover.get_stats()['email'] == 1
        
        remover.reset_stats()
        assert remover.get_stats()['email'] == 0
    
    def test_preserve_non_string_values(self):
        """Test that non-string values are preserved."""
        remover = PIIRemover()
        data = {
            "count": 42,
            "active": True,
            "value": None,
            "items": [1, 2, 3]
        }
        
        result = remover.remove_pii_from_dict(data)
        
        assert result['count'] == 42
        assert result['active'] is True
        assert result['value'] is None
        assert result['items'] == [1, 2, 3]


class TestPIISanitizer:
    """Test sanitizer file operations."""
    
    def test_generate_output_path(self):
        """Test output path generation."""
        sanitizer = PIISanitizer()
        input_path = Path("logs/test.jsonl")
        output_path = sanitizer._generate_output_path(input_path)
        
        assert output_path == Path("logs/test_sanitized.jsonl")
    
    def test_sanitize_file_dry_run(self, tmp_path):
        """Test file sanitization in dry run mode."""
        # Create test input file
        input_file = tmp_path / "test.jsonl"
        with open(input_file, 'w') as f:
            f.write(json.dumps({"email": "test@example.com"}) + '\n')
            f.write(json.dumps({"phone": "123-456-7890"}) + '\n')
        
        sanitizer = PIISanitizer()
        result = sanitizer.sanitize_file(input_file, dry_run=True)
        
        assert result['records_processed'] == 2
        assert result['total_pii_found'] >= 2  # At least email and phone
        assert result['dry_run'] is True
        assert result['output_path'] is None
    
    def test_sanitize_file_with_output(self, tmp_path):
        """Test file sanitization with output file."""
        # Create test input file
        input_file = tmp_path / "test.jsonl"
        output_file = tmp_path / "output.jsonl"
        
        with open(input_file, 'w') as f:
            f.write(json.dumps({"user": "john@example.com", "id": 123}) + '\n')
        
        sanitizer = PIISanitizer(['email'])
        result = sanitizer.sanitize_file(input_file, output_file)
        
        assert result['records_processed'] == 1
        assert output_file.exists()
        
        # Verify output content
        with open(output_file, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            assert "[EMAIL_REDACTED]" in data['user']
            assert data['id'] == 123
    
    def test_invalid_json_handling(self, tmp_path):
        """Test handling of invalid JSON lines."""
        input_file = tmp_path / "invalid.jsonl"
        
        with open(input_file, 'w') as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
        
        sanitizer = PIISanitizer()
        result = sanitizer.sanitize_file(input_file, dry_run=True)
        
        # Should process only valid lines
        assert result['records_processed'] == 2


class TestFileSanitizer:
    """Test JSONL file sanitization with FileSanitizer."""
    
    def test_sanitize_jsonl_file(self):
        """Test sanitizing a JSONL file."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write('{"prompt": "Email me at test@example.com", "model": "gpt-4"}\n')
            f.write('{"prompt": "Call 555-1234", "model": "gpt-3.5-turbo"}\n')
            input_file = f.name
        
        try:
            # Sanitize file
            sanitizer = FileSanitizer()
            result = sanitizer.sanitize_jsonl_file(input_file)
            
            # Check output file was created
            assert Path(result['output_file']).exists()
            
            # Verify content
            with open(result['output_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 2
                
                # Check first record
                record1 = json.loads(lines[0])
                assert "test@example.com" not in record1['prompt']
                assert "[EMAIL_REDACTED]" in record1['prompt']
            
            # Check stats
            assert result['records_processed'] == 2
            assert result['total_pii_removed'] > 0
            
        finally:
            # Cleanup
            Path(input_file).unlink()
            if result.get('output_file'):
                Path(result['output_file']).unlink(missing_ok=True)
    
    def test_dry_run_mode(self):
        """Test dry run mode doesn't create output file."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write('{"prompt": "test@example.com"}\n')
            input_file = f.name
        
        try:
            sanitizer = FileSanitizer()
            result = sanitizer.sanitize_jsonl_file(input_file, dry_run=True)
            
            # Output file should not exist
            assert result['output_file'] is None
            
            # But stats should be present
            assert result['total_pii_removed'] > 0
            
        finally:
            Path(input_file).unlink()
    
    def test_custom_output_path(self):
        """Test custom output file path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write('{"prompt": "test@example.com"}\n')
            input_file = f.name
        
        custom_output = str(Path(input_file).parent / "custom_output.jsonl")
        
        try:
            sanitizer = FileSanitizer()
            result = sanitizer.sanitize_jsonl_file(input_file, output_file=custom_output)
            
            assert result['output_file'] == custom_output
            assert Path(custom_output).exists()
            
        finally:
            Path(input_file).unlink()
            Path(custom_output).unlink(missing_ok=True)


class TestPIIDictRemoval:
    """Test PII removal from dictionary structures."""
    
    def test_simple_dict(self):
        """Test PII removal from simple dictionary."""
        remover = PIIRemover()
        
        data = {
            "user": "john@example.com",
            "message": "Call me at 555-123-4567",
            "count": 42
        }
        
        result = remover.remove_pii_from_dict(data)
        
        assert "john@example.com" not in result["user"]
        assert "[EMAIL_REDACTED]" in result["user"]
        assert "555-123-4567" not in result["message"]
        assert "[PHONE_REDACTED]" in result["message"]
        assert result["count"] == 42  # Non-PII unchanged
    
    def test_nested_dict(self):
        """Test PII removal from nested dictionary."""
        remover = PIIRemover()
        
        data = {
            "metadata": {
                "user_email": "test@test.com",
                "user_phone": "555-9999"
            },
            "prompt": "Safe content"
        }
        
        result = remover.remove_pii_from_dict(data)
        
        assert "test@test.com" not in result["metadata"]["user_email"]
        assert "Safe content" in result["prompt"]


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_file(self):
        """Test handling empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            input_file = f.name  # Empty file
        
        try:
            sanitizer = FileSanitizer()
            result = sanitizer.sanitize_jsonl_file(input_file)
            
            assert result['records_processed'] == 0
            
        finally:
            Path(input_file).unlink()
            if result.get('output_file'):
                Path(result['output_file']).unlink(missing_ok=True)
    
    def test_invalid_json_line(self):
        """Test handling invalid JSON line."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
            input_file = f.name
        
        try:
            sanitizer = FileSanitizer()
            result = sanitizer.sanitize_jsonl_file(input_file)
            
            # Should process 2 valid records, skip 1 invalid
            assert result['records_processed'] == 2
            
        finally:
            Path(input_file).unlink()
            if result.get('output_file'):
                Path(result['output_file']).unlink(missing_ok=True)
    
    def test_nonexistent_file(self):
        """Test error when input file doesn't exist."""
        sanitizer = FileSanitizer()
        
        with pytest.raises(FileNotFoundError):
            sanitizer.sanitize_jsonl_file("nonexistent_file.jsonl")
    
    def test_phone_removal(self):
        """Test phone number removal."""
        remover = PIIRemover(pii_types=['phone_us'])
        
        text = "Call me at (555) 123-4567 or 555-987-6543"
        result = remover.remove_pii_from_text(text)
        
        assert "(555) 123-4567" not in result
        assert "555-987-6543" not in result
        assert "[PHONE_REDACTED]" in result
        assert remover.get_stats()['phone_us'] >= 1
    
    def test_ssn_removal(self):
        """Test SSN removal."""
        remover = PIIRemover(pii_types=['ssn'])
        
        text = "My SSN is 123-45-6789"
        result = remover.remove_pii_from_text(text)
        
        assert "123-45-6789" not in result
        assert "[SSN_REDACTED]" in result
    
    def test_credit_card_removal(self):
        """Test credit card removal."""
        remover = PIIRemover(pii_types=['credit_card'])
        
        text = "Card number: 1234-5678-9012-3456"
        result = remover.remove_pii_from_text(text)
        
        assert "1234-5678-9012-3456" not in result
        assert "[CREDIT_CARD_REDACTED]" in result
