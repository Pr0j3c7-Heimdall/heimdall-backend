from pydantic import Field

from app.common.schema import CamelModel


class MeResponse(CamelModel):
    """마이페이지 회원정보 조회 응답"""

    name: str = Field(..., description="이름")
    email: str = Field(..., description="이메일")
    created_at: str = Field(..., alias="createdAt", description="가입일 (YYYY-MM-DD)")
