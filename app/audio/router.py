from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks, File

from app.audio.dependencies import get_audio_service
from app.auth.dependencies import get_current_user_id
from app.audio.service.audio_service import AudioService
from app.audio.schema.response.upload import AudioUploadResponse, AudioUploadData

router = APIRouter(prefix="/audios", tags=["audios"])

@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    audio_service: AudioService = Depends(get_audio_service),
):
    """
    오디오 파일을 업로드하고 AI 검증을 비동기로 시작함.
    음성/가창 트랙은 더 이상 클라이언트가 지정하지 않으며, 백그라운드 파이프라인이
    YAMNet으로 자동 판별한다 (완료 전까지 응답의 track은 null).
    """
    uploaded_audio = await audio_service.upload_audio(file, user_id, background_tasks)
    return AudioUploadResponse(
        data=AudioUploadData(
            audio_id=uploaded_audio.id,
            audio_url=uploaded_audio.audio_url,
            track=uploaded_audio.track,
            result="업로드 성공 및 AI 검증 시작"
        )
    )
