"""애플리케이션 설정 (역할별 분리, fail-fast)"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Auth 관련 설정. 시작 시점에 검증하여 누락 시 즉시 실패"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    JWT_SECRET_KEY: str = Field(..., min_length=1, description="JWT 서명용 시크릿 키")
    GOOGLE_CLIENT_ID: str = Field(..., min_length=1, description="구글 OAuth 2.0 클라이언트 ID")


class CorsSettings(BaseSettings):
    """CORS 관련 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="허용할 origin 목록 (쉼표 구분)",
    )


class DatabaseSettings(BaseSettings):
    """DB 관련 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="mysql+aiomysql://user:password@localhost:3306/heimdall",
        description="MySQL 연결 URL",
    )


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Auth 설정 조회 (캐싱)"""
    return AuthSettings()


@lru_cache
def get_cors_settings() -> CorsSettings:
    """CORS 설정 조회 (캐싱)"""
    return CorsSettings()


@lru_cache
def get_db_settings() -> DatabaseSettings:
    """DB 설정 조회 (캐싱)"""
    return DatabaseSettings()
