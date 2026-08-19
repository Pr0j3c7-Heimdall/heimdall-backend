from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.detection.audio.repository import AudioDetectionRepository
from app.detection.audio.service.audio_detection_service import AudioDetectionService

def get_audio_detection_repository(db: AsyncSession = Depends(get_db)) -> AudioDetectionRepository:
    return AudioDetectionRepository(db)

def get_audio_detection_service(
    detection_repo: AudioDetectionRepository = Depends(get_audio_detection_repository)
) -> AudioDetectionService:
    return AudioDetectionService(detection_repo)
