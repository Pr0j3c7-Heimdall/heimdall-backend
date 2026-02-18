from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user_credentials
from app.common.schema import SuccessResponse
from app.user.model import User
from app.user.schema import MeResponse

router = APIRouter(prefix="/users", tags=["user"])


@router.get("/me", response_model=SuccessResponse)
async def get_me(
    credentials: tuple[User, str] = Depends(get_current_user_credentials),
):
    """마이페이지 회원정보 조회"""
    user, _ = credentials
    return SuccessResponse(
        data=MeResponse(
            name=user.name,
            email=user.email,
            created_at=user.created_at.strftime("%Y-%m-%d"),
        ).model_dump(by_alias=True)
    )
