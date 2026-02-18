from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.image.repository.image_repository import ImageRepository
from app.image.service.image_service import ImageService

def get_image_repository(db: AsyncSession = Depends(get_db)) -> ImageRepository:
    return ImageRepository(db)

def get_image_service(
    image_repo: ImageRepository = Depends(get_image_repository)
) -> ImageService:
    return ImageService(image_repo)