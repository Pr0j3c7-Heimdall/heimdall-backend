from typing import Optional

from pydantic import Field

from app.common.schema import CamelModel


class LogoutRequest(CamelModel):
    refresh_token: str = Field(..., alias="refreshToken", description="리프레시 토큰")
    access_token: Optional[str] = Field(None, alias="accessToken", description="액세스 토큰 (블랙리스트용, 선택)")
