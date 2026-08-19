from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.audio.repository.audio_repository import AudioRepository
from app.detection.audio.repository.audio_detection_repository import AudioDetectionRepository
from app.detection.audio.service.audio_detection_service import AudioDetectionService
from app.detection.audio.dependencies import get_audio_detection_service
from app.audio.service.audio_service import AudioService

def get_audio_repository(db: AsyncSession = Depends(get_db)) -> AudioRepository:
    return AudioRepository(db)

def get_audio_detection_repository(db: AsyncSession = Depends(get_db)) -> AudioDetectionRepository:
    return AudioDetectionRepository(db)

def get_audio_service(
    audio_repo: AudioRepository = Depends(get_audio_repository),
    detection_repo: AudioDetectionRepository = Depends(get_audio_detection_repository),
    detection_service: AudioDetectionService = Depends(get_audio_detection_service)
) -> AudioService:
    return AudioService(audio_repo, detection_repo, detection_service)
