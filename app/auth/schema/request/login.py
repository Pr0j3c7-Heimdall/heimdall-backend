from pydantic import Field

from app.common.schema import CamelModel


class LoginRequest(CamelModel):
    provider: str = Field(..., description="소셜 로그인 제공자 (google)")
    id_token: str = Field(..., alias="idToken", description="구글 ID Token")
