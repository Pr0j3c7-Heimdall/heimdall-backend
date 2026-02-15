from fastapi import APIRouter, Depends

from app.auth.dependencies import get_auth_service, get_current_user_credentials
from app.auth.exception import AccountDeletedError, ProviderNotSupportedError
from app.auth.schema import LoginRequest, LogoutRequest, RefreshRequest, RefreshResponse
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
    except (ProviderNotSupportedError, AccountDeletedError) as e:
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


@router.delete("/me", response_model=SuccessResponse)
async def withdraw(
    credentials: tuple[int, str] = Depends(get_current_user_credentials),
    service: AuthService = Depends(get_auth_service),
):
    """회원 탈퇴 (status=DELETED, deleted_at 기록)"""
    user_id, access_token = credentials
    await service.withdraw(user_id, access_token)
    return SuccessResponse(data=None)


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: LogoutRequest,
    credentials: tuple[int, str] = Depends(get_current_user_credentials),
    service: AuthService = Depends(get_auth_service),
):
    """로그아웃 (인증 필요, refresh token 삭제, access token 블랙리스트 등록)"""
    _, access_token = credentials
    await service.logout(request, access_token)
    return SuccessResponse(data=None)


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
        data=RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(by_alias=True)
    )
