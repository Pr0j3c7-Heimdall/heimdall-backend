from pydantic import Field

from app.common.schema import CamelModel


class RefreshResponse(CamelModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
