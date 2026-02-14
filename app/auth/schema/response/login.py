from pydantic import Field

from app.common.schema import CamelModel


class LoginResponse(CamelModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    is_new_user: bool = Field(..., alias="isNewUser")
