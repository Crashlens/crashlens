"""
Test: URL Validation SSRF Protection
Purpose: Ensure PUSHGATEWAY_URL validation rejects SSRF attack vectors.

Acceptance Criteria:
- Reject file://, ftp://, and other dangerous schemes
- Reject private IP addresses (127.0.0.1, 192.168.x.x, 10.x.x.x, 172.16-31.x.x)
- Reject localhost and private hostname variations
- Allow HTTP/HTTPS to public IPs only (or with explicit allowlist)
- No network calls during validation

This prevents Server-Side Request Forgery (SSRF) attacks via malicious pushgateway URLs.
"""

import pytest
from urllib.parse import urlparse
import ipaddress
from typing import Optional


def is_private_ip(hostname: str) -> bool:
    """
    Check if hostname resolves to a private IP address.
    
    Returns True for:
    - 127.0.0.0/8 (localhost)
    - 10.0.0.0/8 (private)
    - 172.16.0.0/12 (private)
    - 192.168.0.0/16 (private)
    - 169.254.0.0/16 (link-local)
    - ::1 (IPv6 localhost)
    """
    try:
        # Try to parse as IP address
        ip = ipaddress.ip_address(hostname)
        # Only check for truly private IPs, not documentation ranges
        return (
            ip.is_private or 
            ip.is_loopback or 
            ip.is_link_local or
            ip.is_reserved
        )
    except ValueError:
        # Not an IP address - check for common private hostnames
        private_hostnames = [
            'localhost',
            'localhost.localdomain',
            'ip6-localhost',
            'ip6-loopback',
        ]
        return hostname.lower() in private_hostnames


def validate_pushgateway_url(url: str, allow_private: bool = False) -> tuple[bool, Optional[str]]:
    """
    Validate pushgateway URL for SSRF protection.
    
    Args:
        url: The URL to validate
        allow_private: Whether to allow private IPs (for testing/dev)
    
    Returns:
        (is_valid, error_message)
    """
    if not url:
        return False, "URL is empty"
    
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        return False, f"Invalid scheme '{parsed.scheme}'. Only http and https allowed."
    
    # Check hostname exists
    if not parsed.hostname:
        return False, "URL must have a hostname"
    
    # Check for private IPs unless explicitly allowed
    if not allow_private:
        if is_private_ip(parsed.hostname):
            return False, (
                f"Private IP or localhost '{parsed.hostname}' not allowed. "
                "Set CRASHLENS_ALLOW_PRIVATE_PUSHGATEWAY=1 to override."
            )
    
    return True, None


@pytest.mark.unit
def test_reject_file_scheme():
    """
    ACCEPTANCE: file:// URLs must be rejected.
    """
    dangerous_urls = [
        "file:///etc/passwd",
        "file:///C:/Windows/System32/config/sam",
        "file://localhost/etc/hosts",
    ]
    
    for url in dangerous_urls:
        is_valid, error = validate_pushgateway_url(url)
        assert not is_valid, f"FAIL: file:// URL was not rejected: {url}"
        assert error and "scheme" in error.lower(), f"Error message should mention scheme: {error}"
    
    print("✓ PASS: file:// URLs rejected")


@pytest.mark.unit
def test_reject_ftp_scheme():
    """
    ACCEPTANCE: ftp:// URLs must be rejected.
    """
    ftp_urls = [
        "ftp://example.com",
        "ftp://ftp.example.com/data",
        "ftps://secure.example.com",
    ]
    
    for url in ftp_urls:
        is_valid, error = validate_pushgateway_url(url)
        assert not is_valid, f"FAIL: FTP URL was not rejected: {url}"
        assert error and "scheme" in error.lower(), f"Error message should mention scheme: {error}"
    
    print("✓ PASS: ftp:// URLs rejected")


@pytest.mark.unit
def test_reject_localhost():
    """
    ACCEPTANCE: localhost URLs must be rejected by default.
    """
    localhost_urls = [
        "http://localhost:9091",
        "http://127.0.0.1:9091",
        "http://127.0.0.5:9091",
        "http://127.1.2.3:9091",
        "http://[::1]:9091",  # IPv6 localhost
        "http://localhost.localdomain:9091",
    ]
    
    for url in localhost_urls:
        is_valid, error = validate_pushgateway_url(url, allow_private=False)
        assert not is_valid, f"FAIL: Localhost URL was not rejected: {url}"
        assert error and ("private" in error.lower() or "localhost" in error.lower()), (
            f"Error message should mention private/localhost: {error}"
        )
    
    print("✓ PASS: localhost URLs rejected")


@pytest.mark.unit
def test_reject_private_ips():
    """
    ACCEPTANCE: Private IP ranges must be rejected by default.
    """
    private_ips = [
        "http://192.168.0.1:9091",     # Class C private
        "http://192.168.1.100:9091",
        "http://10.0.0.1:9091",        # Class A private
        "http://10.42.0.5:9091",
        "http://172.16.0.1:9091",      # Class B private
        "http://172.31.255.255:9091",
        "http://169.254.1.1:9091",     # Link-local
    ]
    
    for url in private_ips:
        is_valid, error = validate_pushgateway_url(url, allow_private=False)
        assert not is_valid, f"FAIL: Private IP was not rejected: {url}"
        assert error and "private" in error.lower(), f"Error message should mention private: {error}"
    
    print("✓ PASS: Private IP addresses rejected")


@pytest.mark.unit
def test_allow_public_ips():
    """
    ACCEPTANCE: Public IP addresses with http/https should be allowed.
    """
    public_urls = [
        "http://8.8.8.8:9091",              # Google DNS
        "http://1.1.1.1:9091",              # Cloudflare DNS
        "https://prometheus.io:9091",       # Public domain
        "https://pushgateway.example.com",  # Public domain
        "https://metrics.company.com:9091", # Public domain
    ]
    
    for url in public_urls:
        is_valid, error = validate_pushgateway_url(url, allow_private=False)
        assert is_valid, f"FAIL: Public URL was rejected: {url}. Error: {error}"
    
    print("✓ PASS: Public IP/domain URLs allowed")


@pytest.mark.unit
def test_allow_private_with_override():
    """
    ACCEPTANCE: Private IPs allowed when allow_private=True (explicit override).
    """
    private_urls = [
        "http://localhost:9091",
        "http://127.0.0.1:9091",
        "http://192.168.1.100:9091",
        "http://10.0.0.5:9091",
    ]
    
    for url in private_urls:
        is_valid, error = validate_pushgateway_url(url, allow_private=True)
        assert is_valid, (
            f"FAIL: Private URL rejected even with allow_private=True: {url}. "
            f"Error: {error}"
        )
    
    print("✓ PASS: Private IPs allowed with explicit override")


@pytest.mark.unit
def test_reject_other_dangerous_schemes():
    """
    ACCEPTANCE: Other dangerous schemes must be rejected.
    """
    dangerous_schemes = [
        "gopher://example.com",
        "dict://localhost:2628/d:word",
        "ldap://ldap.example.com",
        "ssh://user@host",
        "telnet://example.com:23",
        "data:text/html,<script>alert(1)</script>",
    ]
    
    for url in dangerous_schemes:
        is_valid, error = validate_pushgateway_url(url)
        assert not is_valid, f"FAIL: Dangerous scheme was not rejected: {url}"
    
    print("✓ PASS: Other dangerous schemes rejected")


@pytest.mark.unit
def test_empty_or_invalid_urls():
    """
    ACCEPTANCE: Empty or malformed URLs must be rejected gracefully.
    """
    invalid_urls = [
        "",
        "   ",
        "not-a-url",
        "://missing-scheme",
        "http://",  # No hostname
    ]
    
    for url in invalid_urls:
        is_valid, error = validate_pushgateway_url(url)
        assert not is_valid, f"FAIL: Invalid URL was not rejected: '{url}'"
        assert error is not None, "Error message should be provided"
    
    print("✓ PASS: Empty/invalid URLs rejected")


@pytest.mark.unit
def test_no_network_calls_during_validation():
    """
    ACCEPTANCE: URL validation must not make network calls.
    
    This test ensures validation is fast and safe.
    """
    # These URLs would require DNS lookups if validation made network calls
    test_urls = [
        "http://this-domain-definitely-does-not-exist-12345.com:9091",
        "http://invalid-tld-99999.invalid:9091",
        "http://192.0.2.1:9091",  # TEST-NET-1 (should not be routable)
    ]
    
    import time
    start = time.time()
    
    for url in test_urls:
        # Validation should be instant (no DNS lookup)
        validate_pushgateway_url(url)
    
    elapsed = time.time() - start
    
    # If validation made network calls, it would take >>100ms per URL
    # We allow 1 second total for all 3 URLs (very generous)
    assert elapsed < 1.0, (
        f"FAIL: Validation took {elapsed:.3f}s for 3 URLs. "
        "Likely making network calls (DNS lookups)."
    )
    
    print(f"✓ PASS: No network calls (validation took {elapsed*1000:.1f}ms for 3 URLs)")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("URL VALIDATION SSRF PROTECTION TEST SUITE")
    print("=" * 70)
    print()
    
    try:
        test_reject_file_scheme()
        test_reject_ftp_scheme()
        test_reject_localhost()
        test_reject_private_ips()
        test_allow_public_ips()
        test_allow_private_with_override()
        test_reject_other_dangerous_schemes()
        test_empty_or_invalid_urls()
        test_no_network_calls_during_validation()
        
        print()
        print("=" * 70)
        print("ALL URL VALIDATION SSRF TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
