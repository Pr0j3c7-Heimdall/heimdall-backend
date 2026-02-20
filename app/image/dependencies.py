from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.image.repository.image_repository import ImageRepository
from app.detection.repository.detection_repository import DetectionRepository
from app.detection.service.detection_service import DetectionService
from app.detection.dependencies import get_detection_service
from app.image.service.image_service import ImageService

def get_image_repository(db: AsyncSession = Depends(get_db)) -> ImageRepository:
    return ImageRepository(db)

def get_detection_repository(db: AsyncSession = Depends(get_db)) -> DetectionRepository:
    return DetectionRepository(db)

def get_image_service(
    image_repo: ImageRepository = Depends(get_image_repository),
    detection_repo: DetectionRepository = Depends(get_detection_repository),
    detection_service: DetectionService = Depends(get_detection_service)
) -> ImageService:
    return ImageService(image_repo, detection_repo, detection_service)