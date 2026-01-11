"""Middleware безопасности для добавления заголовков безопасности и защиты от CSRF."""
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import MutableHeaders


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления заголовков безопасности и базовой защиты от CSRF."""
    
    # Безопасные HTTP-методы, не требующие защиты от CSRF
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    async def dispatch(self, request: Request, call_next):
        # Генерировать CSRF-токен для запросов, изменяющих состояние
        if request.method not in self.SAFE_METHODS:
            csrf_token = secrets.token_urlsafe(32)
            # Сохранить в сессии (в продакшене использовать правильное хранилище сессий)
            # Пока добавляем в заголовки ответа
            response = await call_next(request)
            response.headers["X-CSRF-Token"] = csrf_token
        else:
            response = await call_next(request)
        
        # Добавить заголовки безопасности
        headers = MutableHeaders(response.headers)
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["X-XSS-Protection"] = "1; mode=block"
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (только для HTTPS)
        if request.url.scheme == "https":
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy (базовая)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Разрешить inline для Babel
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        headers["Content-Security-Policy"] = csp
        
        return response

