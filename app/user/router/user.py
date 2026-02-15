from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user_credentials
from app.common.exception import UnauthorizedException
from app.common.schema import SuccessResponse
from app.user.dependencies import get_user_service
from app.user.schema import MeResponse
from app.user.service import UserService

router = APIRouter(prefix="/users", tags=["user"])


@router.get("/me", response_model=SuccessResponse)
async def get_me(
    credentials: tuple[int, str] = Depends(get_current_user_credentials),
    service: UserService = Depends(get_user_service),
):
    """마이페이지 회원정보 조회"""
    user_id, _ = credentials
    user = await service.get_me(user_id)
    if not user:
        raise UnauthorizedException("사용자를 찾을 수 없습니다")
    return SuccessResponse(
        data=MeResponse(
            name=user.name,
            email=user.email,
            created_at=user.created_at.strftime("%Y-%m-%d") if user.created_at else "",
        ).model_dump(by_alias=True)
    )
