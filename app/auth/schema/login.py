from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    provider: str = Field(..., description="소셜 로그인 제공자 (google)")
    id_token: str = Field(..., alias="idToken", description="구글 ID Token")


class LoginResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    is_new_user: bool = Field(..., alias="isNewUser")

    model_config = {"populate_by_name": True}
