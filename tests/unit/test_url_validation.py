"""Unit tests for URL normalization, malicious scheme rejection, and anti-SSRF checks."""

import pytest
from unittest.mock import MagicMock
from app.core.exceptions import BadRequestException, SSRFBlockedException
from app.services.url_service import UrlService


@pytest.fixture
def url_service():
    mock_url_repo = MagicMock()
    mock_abuse_repo = MagicMock()
    return UrlService(mock_url_repo, mock_abuse_repo)


def test_normalize_valid_http_urls(url_service):
    u1 = "https://example.com/path?foo=bar#section"
    assert url_service.validate_and_normalize_url(u1) == "https://example.com/path?foo=bar#section"

    # Strips default port 443 on https
    u2 = "https://EXAMPLE.COM:443/docs"
    assert url_service.validate_and_normalize_url(u2) == "https://example.com/docs"

    # Strips default port 80 on http
    u3 = "http://my-blog.org:80/"
    assert url_service.validate_and_normalize_url(u3) == "http://my-blog.org/"


def test_reject_dangerous_schemes(url_service):
    dangerous = [
        "javascript:alert(document.cookie)",
        "file:///etc/passwd",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "ftp://ftp.example.com/resource",
        "gopher://gopher.floodgap.com",
    ]
    for url in dangerous:
        with pytest.raises(BadRequestException):
            url_service.validate_and_normalize_url(url)


def test_reject_ssrf_private_ips(url_service):
    private_targets = [
        "http://127.0.0.1:8000/internal-admin",
        "https://10.0.0.1/secrets",
        "http://192.168.1.1/router-login",
        "http://172.16.0.5/aws-meta",
        "http://169.254.169.254/latest/meta-data/",  # AWS instance metadata
    ]
    for url in private_targets:
        with pytest.raises(SSRFBlockedException):
            url_service.validate_and_normalize_url(url)
