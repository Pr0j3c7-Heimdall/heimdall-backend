from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class ModelResultSchema(BaseModel):
    model_result_id: int = Field(..., description="Model detection result ID")
    detection_method: str = Field(..., description="Model used for this detection (e.g. SSL-AASIST, RawNet3)")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this detection")
    result_json: Optional[Any] = Field(None, description="상세 결과 JSON")

    class Config:
        from_attributes = True

class AudioDetectionResultData(BaseModel):
    audio_id: int = Field(..., description="Audio ID")
    audio_url: str = Field(..., description="Original audio URL")
    track: str = Field(..., description="Analysis track (speech or singing)")
    final_is_ai: Optional[bool] = Field(None, description="Final determination if the audio is AI-generated")
    final_ai_probability: Optional[float] = Field(None, description="Final probability that the audio is AI-generated")
    completed_at: Optional[datetime] = Field(None, description="Time when the analysis was completed")
    models: List[ModelResultSchema] = Field(default_factory=list, description="List of per-model detection results")

class AudioDetectionResultResponse(SuccessResponse):
    data: AudioDetectionResultData
