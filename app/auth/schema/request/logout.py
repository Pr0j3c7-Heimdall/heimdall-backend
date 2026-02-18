from pydantic import Field

from app.common.schema import CamelModel


class LogoutRequest(CamelModel):
    refresh_token: str = Field(..., alias="refreshToken", description="리프레시 토큰")
