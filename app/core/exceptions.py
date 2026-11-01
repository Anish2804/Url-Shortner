"""Domain exceptions with standard HTTP status codes and detail messages."""

from typing import Any, Dict, Optional
from fastapi import status


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, code="RESOURCE_NOT_FOUND", details=details)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, code="BAD_REQUEST", details=details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED", details=details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN", details=details)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists or conflict occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, code="CONFLICT", details=details)


class RateLimitExceededException(AppException):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", retry_after: int = 60):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after},
        )


class LinkExpiredException(AppException):
    def __init__(self, message: str = "This short link has expired"):
        super().__init__(message=message, status_code=status.HTTP_410_GONE, code="LINK_EXPIRED")


class LinkInactiveException(AppException):
    def __init__(self, message: str = "This short link is currently inactive"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="LINK_INACTIVE")


class LinkPasswordRequiredException(AppException):
    def __init__(self, message: str = "Password is required to access this link"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, code="PASSWORD_REQUIRED")


class InvalidLinkPasswordException(AppException):
    def __init__(self, message: str = "Incorrect password for this link"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="INVALID_LINK_PASSWORD")


class LinkAlreadyConsumedException(AppException):
    def __init__(self, message: str = "This one-time link has already been used"):
        super().__init__(message=message, status_code=status.HTTP_410_GONE, code="LINK_ALREADY_CONSUMED")


class SSRFBlockedException(AppException):
    def __init__(self, message: str = "Destination URL resolves to a forbidden private or local network"):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, code="SSRF_FORBIDDEN_DESTINATION")


class MaliciousDomainException(AppException):
    def __init__(self, message: str = "Destination domain is blocked due to security or abuse policies"):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, code="MALICIOUS_DOMAIN_BLOCKED")


class ServiceUnavailableException(AppException):
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, code="SERVICE_UNAVAILABLE")
