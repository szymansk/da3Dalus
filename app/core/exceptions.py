"""
Service-layer exceptions for clean separation of concerns.

These exceptions are raised by service functions and automatically
translated to HTTP responses by the global exception handler in main.py.
"""

from typing import Any, Dict, Optional


class ServiceException(Exception):
    """Base exception for all service-layer errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ServiceException):
    """Resource not found. Maps to HTTP 404."""
    pass


class ValidationError(ServiceException):
    """Invalid input data. Maps to HTTP 422."""
    pass


class ConflictError(ServiceException):
    """Resource conflict (e.g., already exists, locked). Maps to HTTP 409."""
    pass


class InternalError(ServiceException):
    """Internal server error. Maps to HTTP 500."""
    pass
