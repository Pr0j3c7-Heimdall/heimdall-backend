from pydantic import BaseModel, Field
from typing import Optional
from app.common.schema.response import SuccessResponse

class AudioUploadData(BaseModel):
    audio_id: int = Field(..., description="Unique ID of the uploaded audio")
    audio_url: str = Field(..., description="Full URL to access the uploaded audio")
    track: str = Field(..., description="Analysis track (speech or singing)")
    result: Optional[str] = Field(None, description="Result message from AI validation (if any)")

class AudioUploadResponse(SuccessResponse):
    data: AudioUploadData
