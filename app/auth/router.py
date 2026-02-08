from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exception import ProviderNotSupportedError
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.common.exception import BadRequestException, UnauthorizedException
from app.auth.schema import LoginRequest
from app.auth.service import AuthService
from app.common.schema import SuccessResponse
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SuccessResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """구글 로그인 (겸 가입)"""
    user_repo = UserRepository(db)
    refresh_repo = RefreshTokenRepository(db)
    service = AuthService(user_repo, refresh_repo)

    try:
        result = await service.login(request)
    except ProviderNotSupportedError as e:
        raise BadRequestException(str(e)) from e

    if not result:
        raise UnauthorizedException("유효하지 않은 ID Token입니다")

    access_token, refresh_token, is_new_user = result
    return SuccessResponse(
        data={
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "isNewUser": is_new_user,
        }
    )
