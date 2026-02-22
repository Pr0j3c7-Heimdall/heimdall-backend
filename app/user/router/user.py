from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.auth.dependencies import get_current_user_credentials
from app.common.schema import SuccessResponse
from app.user.model import User
from app.user.schema import MeResponse
from app.user.service import UserService
from app.user.dependencies import get_user_service

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


@router.get("/me/history/image", response_model=SuccessResponse)
async def get_my_image_history(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    result_type: Optional[str] = Query(None),
    credentials: tuple[User, str] = Depends(get_current_user_credentials),
    service: UserService = Depends(get_user_service),
):
    """마이페이지 이미지 검증 내역 조회"""
    user, _ = credentials
    
    if file_type and file_type != "image":
        return SuccessResponse(data={
            "total_count": 0,
            "total_pages": 0,
            "current_page": page,
            "histories": []
        })

    history_data = await service.get_image_history(
        user_id=user.id,
        page=page,
        size=size,
        keyword=keyword,
        result_type=result_type
    )
    
    return SuccessResponse(data=history_data.model_dump(by_alias=True))
