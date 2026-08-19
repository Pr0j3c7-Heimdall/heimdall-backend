from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class AudioDetectionStatusData(BaseModel):
    audio_id: int = Field(..., description="ID of the audio")
    analysis_status: str = Field(..., description="Current status of the analysis pipeline")

class AudioDetectionStatusResponse(SuccessResponse):
    data: AudioDetectionStatusData
