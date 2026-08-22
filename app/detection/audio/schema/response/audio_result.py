from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.schema.response import SuccessResponse

class C2PAResultSchema(BaseModel):
    """C2PA 검증 결과.

    필드 구성은 이미지 응답의 C2PAResultSchema와 동일하다. 프론트엔드가 이미지/오디오
    결과를 같은 컴포넌트로 렌더링할 수 있도록 의도적으로 맞춘 것이므로,
    한쪽만 바꾸지 말 것.
    """

    c2pa_id: int = Field(..., description="C2PA verification result ID")
    is_c2pa_compliant: bool = Field(..., description="서명·바인딩·신뢰 검증을 통과하고 AI 생성이 선언된 경우에만 true")

    created_model: Optional[str] = Field(None, description="생성 모델명 1")
    converted_model: Optional[str] = Field(None, description="생성 모델명 2")
    created_description: Optional[str] = Field(None, description="생성 모델명 3")
    claim_generator: Optional[str] = Field(None, description="서명한 주체 1")
    claim_generator_info_name: Optional[str] = Field(None, description="서명한 주체 2")
    synth_id: Optional[str] = Field(None, description="Google SynthID Watermark")
    visible_watermark: Optional[str] = Field(None, description="Google Visible Watermark")
    total_digital_source_type: Optional[str] = Field(None, description="디지털 콘텐츠 제작 방식 라벨")
    synth_id_digital_source_type: Optional[str] = Field(None, description="synthID 생성 방식 라벨")
    visible_watermark_digital_source_type: Optional[str] = Field(None, description="visible watermark 생성 방식 라벨")

    class Config:
        from_attributes = True

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
    c2pa: Optional[C2PAResultSchema] = Field(None, description="C2PA verification result")
    models: List[ModelResultSchema] = Field(default_factory=list, description="List of per-model detection results")

class AudioDetectionResultResponse(SuccessResponse):
    data: AudioDetectionResultData
