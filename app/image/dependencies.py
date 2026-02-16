from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.image.repository.image_repository import ImageRepository
from app.image.service.image_service import ImageService
from app.common.exception.base_exception import UnauthorizedException

from app.config import get_auth_settings
from jose import jwt, JWTError

auth_settings = get_auth_settings()

security = HTTPBearer()

def get_image_repository(db: AsyncSession = Depends(get_db)) -> ImageRepository:
    return ImageRepository(db)

def get_image_service(
    image_repo: ImageRepository = Depends(get_image_repository)
) -> ImageService:
    return ImageService(image_repo)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    token = credentials.credentials  # 여기서 바로 쌩 토큰 문자열을 꺼냅니다.
    
    credentials_exception = UnauthorizedException("인증 정보를 검증할 수 없습니다.")
    try:
        # 아래부터는 기존 코드와 동일
        payload = jwt.decode(token, auth_settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return int(user_id)