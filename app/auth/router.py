from fastapi import APIRouter, Depends

from app.auth.dependencies import get_auth_service
from app.auth.exception import ProviderNotSupportedError
from app.auth.schema import LoginRequest, RefreshRequest
from app.auth.service import AuthService
from app.common.exception import BadRequestException, UnauthorizedException
from app.common.schema import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SuccessResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    """구글 로그인 (겸 가입)"""

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


@router.post("/refresh", response_model=SuccessResponse)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    """액세스 토큰 재발급 (리프레시 토큰 사용, 토큰 로테이션)"""
    result = await service.refresh(request)
    if not result:
        raise UnauthorizedException("유효하지 않거나 만료된 리프레시 토큰입니다")

    access_token, refresh_token = result
    return SuccessResponse(
        data={
            "accessToken": access_token,
            "refreshToken": refresh_token,
        }
    )
