from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks, File, Form

from app.audio.dependencies import get_audio_service
from app.auth.dependencies import get_current_user_id
from app.audio.service.audio_service import AudioService
from app.audio.schema.response.upload import AudioUploadResponse, AudioUploadData

router = APIRouter(prefix="/audios", tags=["audios"])

@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    track: str = Form(..., description="분석 트랙 (speech 또는 singing)"),
    user_id: int = Depends(get_current_user_id),
    audio_service: AudioService = Depends(get_audio_service),
):
    """
    오디오 파일을 업로드하고 AI 검증을 비동기로 시작함.
    """
    uploaded_audio = await audio_service.upload_audio(file, track, user_id, background_tasks)
    return AudioUploadResponse(
        data=AudioUploadData(
            audio_id=uploaded_audio.id,
            audio_url=uploaded_audio.audio_url,
            track=uploaded_audio.track,
            result="업로드 성공 및 AI 검증 시작"
        )
    )
