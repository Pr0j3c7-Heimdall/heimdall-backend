from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.detection.image.repository import DetectionRepository
from app.detection.image.service.image_detection_service import DetectionService

def get_detection_repository(db: AsyncSession = Depends(get_db)) -> DetectionRepository:
    return DetectionRepository(db)

def get_detection_service(
    detection_repo: DetectionRepository = Depends(get_detection_repository)
) -> DetectionService:
    return DetectionService(detection_repo)
