from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""
    
    # Приложение
    app_name: str = "PC Place"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # База данных
    database_url: str = "sqlite+aiosqlite:///./pc_place.db"
    
    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # MinIO/S3
    minio_endpoint: str = "localhost:9000"
    minio_public_url: str = "http://localhost:9000"  # Публичный URL для клиентов (браузеров)
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "pc-place-uploads"
    minio_use_ssl: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    cache_ttl: int = 3600  # Время жизни кеша в секундах (1 час)
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def minio_url(self) -> str:
        """Получить URL MinIO на основе настройки SSL."""
        protocol = "https" if self.minio_use_ssl else "http"
        return f"{protocol}://{self.minio_endpoint}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
