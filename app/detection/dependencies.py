from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.detection.repository.detection_repository import DetectionRepository
from app.image.repository.image_repository import ImageRepository
from app.detection.service.detection_service import DetectionService

def get_detection_repository(db: AsyncSession = Depends(get_db)) -> DetectionRepository:
    return DetectionRepository(db)

def get_image_repository(db: AsyncSession = Depends(get_db)) -> ImageRepository:
    return ImageRepository(db)

def get_detection_service(
    detection_repo: DetectionRepository = Depends(get_detection_repository),
    image_repo: ImageRepository = Depends(get_image_repository)
) -> DetectionService:
    return DetectionService(detection_repo, image_repo)
