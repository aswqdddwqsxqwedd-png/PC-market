from fastapi import HTTPException, status
from typing import Any, Optional, Dict


class AppException(HTTPException):
    """Base application exception."""
    
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {}
                }
            }
        )


class NotFoundError(AppException):
    """Resource not found error."""
    
    def __init__(self, resource: str, resource_id: Any = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} not found",
            details={"id": resource_id} if resource_id else None
        )


class AuthenticationError(AppException):
    """Authentication error."""
    
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_FAILED",
            message=message
        )


class AuthorizationError(AppException):
    """Authorization error."""
    
    def __init__(self, message: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message
        )


class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details
        )


class ConflictError(AppException):
    """Conflict error (e.g., duplicate resource)."""
    
    def __init__(self, resource: str, message: str = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code=f"{resource.upper()}_ALREADY_EXISTS",
            message=message or f"{resource} already exists"
        )
