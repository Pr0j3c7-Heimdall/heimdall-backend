from pydantic import BaseModel, Field
from typing import Optional
from app.common.schema.response import SuccessResponse

class AudioUploadData(BaseModel):
    audio_id: int = Field(..., description="Unique ID of the uploaded audio")
    audio_url: str = Field(..., description="Full URL to access the uploaded audio")
    track: Optional[str] = Field(None, description="분석 트랙 (speech 또는 singing). YAMNet 판별 완료 전에는 null")
    result: Optional[str] = Field(None, description="Result message from AI validation (if any)")

class AudioUploadResponse(SuccessResponse):
    data: AudioUploadData
