from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user_id
from app.detection.audio.dependencies import get_audio_detection_service
from app.detection.audio.service.audio_detection_service import AudioDetectionService
from app.detection.audio.schema import AudioDetectionStatusResponse
from app.detection.audio.schema import AudioDetectionResultResponse

router = APIRouter(prefix="/audio", tags=["detection"])

@router.get("/{audio_id}/status", response_model=AudioDetectionStatusResponse)
async def get_detection_status(
    audio_id: int,
    user_id: int = Depends(get_current_user_id),
    detection_service: AudioDetectionService = Depends(get_audio_detection_service)
):
    """AI 검증 파이프라인의 현재 상태 및 최종 결과를 조회함."""
    status_data = await detection_service.get_detection_status(audio_id, user_id)
    return AudioDetectionStatusResponse(data=status_data)

@router.get("/{audio_id}/result", response_model=AudioDetectionResultResponse)
async def get_detection_result(
    audio_id: int,
    user_id: int = Depends(get_current_user_id),
    detection_service: AudioDetectionService = Depends(get_audio_detection_service)
):
    """AI 검증 파이프라인 분석이 완료된 후 상세 결과를 조회함."""
    result_data = await detection_service.get_detection_result(audio_id, user_id)
    return AudioDetectionResultResponse(data=result_data)
